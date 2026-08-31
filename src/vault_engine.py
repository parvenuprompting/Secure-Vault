from __future__ import annotations

import os
import gc
import uuid
import logging
import subprocess
import threading
from typing import Callable, Dict, Optional, Tuple

logger = logging.getLogger("VaultEngine")


class VaultEngine:
    """
    Verantwoordelijk voor alle systeem-operaties:
    Padvalidatie, grootte berekening, AES-256 geëncrypteerde kluis-aanmaak (UDZO, UDRW, UDSB/SparseBundle),
    macOS Keychain integratie, fouthandeling, notificaties, ontgrendelen en veilig vergrendelen.
    Volledig ontkoppeld van de UI.
    """

    FORMAT_DESCRIPTIONS = {
        "UDZO": "Gecomprimeerd (Alleen-Lezen .dmg)",
        "UDRW": "Lees / Schrijf (Aanpasbaar .dmg)",
        "UDSB": "Meegroeiend (Sparse Bundle .sparsebundle)",
    }

    _active_mounts: Dict[str, str] = {}  # {mount_point: vault_path}

    @staticmethod
    def parse_hdiutil_error(stderr: str) -> str:
        """
        Converteert ruwe hdiutil stderr output naar duidelijke Nederlandstalige meldingen.
        """
        if not stderr:
            return "Onbekende hdiutil fout."

        err_lower = stderr.lower()
        if "checksum incorrect" in err_lower or "authentication failed" in err_lower or "invalid argument" in err_lower:
            return "❌ Wachtwoord is onjuist of het kluisbestand is beschadigd."
        elif "no mountable file systems" in err_lower:
            return "❌ Kan bestandssysteem niet koppelen. Het kluisbestand is mogelijk niet van een ondersteund type."
        elif "resource busy" in err_lower or "busy" in err_lower:
            return "⚠️ Kluis is nog in gebruik door Finder of een ander programma. Sluit geopende bestanden en probeer opnieuw."
        elif "permission denied" in err_lower or "operation not permitted" in err_lower:
            return "❌ Geen toegang. Controleer lees- en schrijfrechten op dit bestand."
        elif "file exists" in err_lower:
            return "⚠️ Een kluis met deze naam bestaat al op de doelbestemming."

        return f"hdiutil fout: {stderr.strip()}"

    @staticmethod
    def send_macos_notification(title: str, message: str) -> None:
        """
        Verstuurt een native macOS notificatie via osascript. Faalt stil als notificaties uit staan.
        """
        try:
            cmd = ["osascript", "-e", f'display notification "{message}" with title "{title}"']
            subprocess.run(cmd, capture_output=True, timeout=3)
        except Exception as e:
            logger.debug("Could not send macOS notification: %s", e)

    @staticmethod
    def save_keychain_password(vault_path: str, password: str) -> bool:
        """
        Slaat een wachtwoord veilig op in macOS Sleutelhangertoegang (Keychain) voor deze kluis.
        """
        if not vault_path or not password:
            return False
        try:
            abs_path = os.path.abspath(vault_path)
            cmd = [
                "security",
                "add-generic-password",
                "-a",
                abs_path,
                "-s",
                "SecureVault",
                "-w",
                password,
                "-U",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return res.returncode == 0
        except Exception as e:
            logger.warning("Keychain save failed: %s", e)
            return False

    @staticmethod
    def get_keychain_password(vault_path: str) -> Optional[str]:
        """
        Haalt een opgeslagen wachtwoord op uit macOS Keychain voor deze kluis.
        """
        if not vault_path:
            return None
        try:
            abs_path = os.path.abspath(vault_path)
            cmd = [
                "security",
                "find-generic-password",
                "-a",
                abs_path,
                "-s",
                "SecureVault",
                "-w",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout:
                return res.stdout.strip()
            return None
        except Exception as e:
            logger.warning("Keychain fetch failed: %s", e)
            return None

    @staticmethod
    def delete_keychain_password(vault_path: str) -> bool:
        """
        Verwijdert een bewaard wachtwoord uit macOS Keychain voor deze kluis.
        """
        if not vault_path:
            return False
        try:
            abs_path = os.path.abspath(vault_path)
            cmd = [
                "security",
                "delete-generic-password",
                "-a",
                abs_path,
                "-s",
                "SecureVault",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return res.returncode == 0
        except Exception as e:
            logger.warning("Keychain delete failed: %s", e)
            return False

    def get_vault_disk_size(self, vault_path: str) -> str:
        """
        Berekent de daadwerkelijke omvang op schijf van een .dmg of .sparsebundle.
        """
        if not os.path.exists(vault_path):
            return "0 MB"
        try:
            total_bytes = 0
            if os.path.isdir(vault_path):
                for dirpath, _, filenames in os.walk(vault_path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        try:
                            if not os.path.islink(fp):
                                total_bytes += os.path.getsize(fp)
                        except OSError:
                            continue
            else:
                total_bytes = os.path.getsize(vault_path)

            size_mb = total_bytes / (1024 * 1024)
            if size_mb >= 1024:
                return f"{size_mb / 1024:.1f} GB"
            return f"{int(size_mb)} MB"
        except Exception:
            return "Onbekend"

    def validate_paths(self, source: str, dest_folder: str) -> None:
        """
        Valideert of de bronmap en doelmap bestaan en of er schrijfrechten zijn.
        """
        if not source or not os.path.exists(source):
            raise ValueError(f"Bronmap bestaat niet: '{source}'")
        if not os.path.isdir(source):
            raise ValueError(f"Gekozen bron is geen map: '{source}'")

        if not dest_folder or not os.path.exists(dest_folder):
            raise ValueError(f"Doelmap bestaat niet: '{dest_folder}'")
        if not os.path.isdir(dest_folder):
            raise ValueError(f"Gekozen doel is geen map: '{dest_folder}'")

        if not os.access(dest_folder, os.W_OK):
            raise PermissionError(f"Geen schrijfrechten in doelmap: '{dest_folder}'")

    def calculate_size_mb(self, source_path: str) -> int:
        """
        Berekent de grootte van de bronmap in MB, inclusief 15% buffer en 100MB minimum overhead.
        """
        total_size = 0
        for dirpath, _, filenames in os.walk(source_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
                except OSError:
                    continue

        size_mb = total_size / (1024 * 1024)
        return max(int(size_mb * 1.15) + 100, 100)

    @staticmethod
    def check_password_strength(password: str) -> Tuple[bool, str, int]:
        """
        Controleert de sterkte van een wachtwoord.
        Retourneert: (is_geldig, feedback_bericht, score_0_100)
        """
        if not password:
            return False, "Wachtwoord is leeg.", 0

        score = 0
        length = len(password)

        if length < 8:
            return False, "Wachtwoord moet minimaal 8 tekens lang zijn.", min(length * 5, 35)

        score += min(length * 4, 40)

        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)

        if has_lower:
            score += 15
        if has_upper:
            score += 15
        if has_digit:
            score += 15
        if has_special:
            score += 15

        score = min(score, 100)

        if score < 50:
            msg = "Zwak wachtwoord: voeg meer variatie in tekens toe."
        elif score < 75:
            msg = "Matig wachtwoord: voeg cijfers of speciale tekens toe."
        else:
            msg = "Sterk wachtwoord!"

        return True, msg, score

    @staticmethod
    def generate_secure_password(length: int = 16) -> str:
        """
        Genereert een cryptografisch sterk, willekeurig wachtwoord met Python's secrets module.
        """
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-="
        while True:
            password = "".join(secrets.choice(alphabet) for _ in range(length))
            if (
                any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(not c.isalnum() for c in password)
            ):
                return password

    def cleanup(self, path: str) -> None:
        """Veilige verwijdering van een bestand of map als het bestaat."""
        if os.path.exists(path):
            try:
                if os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                logger.info("Opgeruimd: %s", path)
            except OSError as e:
                logger.warning("Kon %s niet opruimen: %s", path, e)

    def create_vault(
        self,
        source: str,
        dest_folder: str,
        name: str,
        password: str,
        format_type: str = "UDZO",
        progress_callback: Optional[Callable[[str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
        allow_overwrite: bool = False,
    ) -> Tuple[bool, str]:
        """
        Maakt een geëncrypteerde AES-256 kluis aan (UDZO, UDRW of UDSB/SparseBundle) via hdiutil.
        """
        def log(msg: str) -> None:
            logger.info(msg)
            if progress_callback:
                progress_callback(msg)

        pw_bytes = bytearray(password.encode("utf-8"))

        ext = ".sparsebundle" if format_type == "UDSB" else ".dmg"
        dmg_final = os.path.join(dest_folder, f"{name}{ext}")
        vol_name = f"{name}-{uuid.uuid4().hex[:8]}"

        try:
            if cancel_event and cancel_event.is_set():
                return False, "Proces geannuleerd door gebruiker."

            log("🔍 Stap 1: Paden en rechten valideren...")
            self.validate_paths(source, dest_folder)

            log("📏 Stap 2: Grootte van bronmap berekenen...")
            size_mb = self.calculate_size_mb(source)
            log(f"   -> Geschatte grootte: {size_mb} MB (inclusief reserve)")

            if cancel_event and cancel_event.is_set():
                return False, "Proces geannuleerd door gebruiker."

            if os.path.lexists(dmg_final):
                if not allow_overwrite:
                    log("⚠️ Er bestaat al een kluis met deze naam. De bestaande kluis blijft behouden.")
                    return False, f"Bestaat al: '{dmg_final}'. Kies een andere naam of bevestig overschrijven."
                log("⚠️ Overschrijven is expliciet bevestigd; bestaande kluis wordt verwijderd.")
                self.cleanup(dmg_final)

            log(f"🔨 Stap 3: Kluis aanmaken ({self.FORMAT_DESCRIPTIONS.get(format_type, format_type)})...")
            safe_source = source.rstrip("/")

            cmd = [
                "hdiutil",
                "create",
                "-srcfolder",
                safe_source,
                "-format",
                format_type,
                "-fs",
                "APFS",
                "-encryption",
                "AES-256",
                "-volname",
                vol_name,
                "-stdinpass",
                dmg_final,
            ]

            cmd_log = " ".join(cmd[:-2] + ["<MASKED_PASS>", cmd[-1]])
            logger.debug("Uitvoeren commando: %s", cmd_log)

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if process.stdin:
                process.stdin.write(password)
                process.stdin.flush()
                process.stdin.close()

            while process.poll() is None:
                if cancel_event and cancel_event.is_set():
                    log("⚠️ Annuleren ontvangen... Bezig met stopzetten van processen...")
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    self.cleanup(dmg_final)
                    return False, "Proces geannuleerd door gebruiker."
                threading.Event().wait(0.2)

            stdout, stderr = process.communicate()

            if process.returncode != 0:
                self.cleanup(dmg_final)
                parsed_err = self.parse_hdiutil_error(stderr)
                log(f"❌ Encryptiefout: {parsed_err}")
                return False, parsed_err

            log(f"🎉 Succes! Kluis is aangemaakt op:\n{dmg_final}")
            self.send_macos_notification("SecureVault", f"Kluis '{name}' is succesvol aangemaakt!")
            return True, dmg_final

        except Exception as e:
            self.cleanup(dmg_final)
            log(f"❌ Fout opgetreden: {str(e)}")
            return False, str(e)

        finally:
            for i in range(len(pw_bytes)):
                pw_bytes[i] = 0
            del pw_bytes
            del password
            gc.collect()

    def mount_vault(self, vault_path: str, password: str) -> Tuple[bool, str, str]:
        """
        Ontgrendelt en koppelt een bestaande kluis (.dmg of .sparsebundle) via hdiutil attach -stdinpass.
        """
        if not vault_path or not os.path.exists(vault_path):
            return False, f"Kluisbestand niet gevonden: '{vault_path}'", ""

        pw_bytes = bytearray(password.encode("utf-8"))
        vol_id = f"BeveiligdVolume-{uuid.uuid4().hex[:8]}"
        mount_point = f"/Volumes/{vol_id}"

        try:
            cmd = [
                "hdiutil",
                "attach",
                vault_path,
                "-mountpoint",
                mount_point,
                "-stdinpass",
                "-nobrowse",
            ]

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if process.stdin:
                process.stdin.write(password)
                process.stdin.flush()
                process.stdin.close()

            stdout, stderr = process.communicate()

            if process.returncode != 0:
                parsed_err = self.parse_hdiutil_error(stderr)
                logger.error("Failed to attach vault %s: %s", vault_path, parsed_err)
                return False, parsed_err, ""

            self._active_mounts[mount_point] = vault_path
            logger.info("Vault %s mounted at %s", vault_path, mount_point)
            return True, "Kluis succesvol ontgrendeld!", mount_point

        except Exception as e:
            logger.error("Exception during mount: %s", e)
            return False, f"Fout bij koppelen: {str(e)}", ""

        finally:
            for i in range(len(pw_bytes)):
                pw_bytes[i] = 0
            del pw_bytes
            del password
            gc.collect()

    def unmount_vault(self, mount_point: str, force: bool = False) -> Tuple[bool, str]:
        """
        Werpt een gekoppelde kluis veilig uit via hdiutil detach.
        """
        if not os.path.exists(mount_point):
            if mount_point in self._active_mounts:
                del self._active_mounts[mount_point]
            return True, "Kluis was al ontkoppeld."

        cmd = ["hdiutil", "detach", mount_point]
        if force:
            cmd.append("-force")

        res = subprocess.run(cmd, capture_output=True, text=True)

        if res.returncode == 0:
            if mount_point in self._active_mounts:
                del self._active_mounts[mount_point]
            logger.info("Vault unmounted at %s", mount_point)
            return True, "Kluis is veilig vergrendeld en afgesloten."

        parsed_err = self.parse_hdiutil_error(res.stderr)
        logger.warning("Unmount failed for %s: %s", mount_point, parsed_err)
        return False, parsed_err

    def unmount_all_vaults(self) -> int:
        """
        Werpt alle actieve geopende kluizen uit (bijv. bij Auto-Lock).
        Retourneert het aantal succesvol ontkoppelde kluizen.
        """
        unmounted_count = 0
        mounts = list(self._active_mounts.keys())
        for mnt in mounts:
            success, _ = self.unmount_vault(mnt)
            if success:
                unmounted_count += 1
        if unmounted_count > 0:
            self.send_macos_notification(
                "SecureVault Auto-Lock",
                f"{unmounted_count} kluis(en) automatisch vergrendeld wegens inactiviteit.",
            )
        return unmounted_count

    def get_active_mounts(self) -> Dict[str, str]:
        """Retourneert een kopie van het woordenboek met actieve mounts {mount_point: vault_path}."""
        inactive = [m for m in self._active_mounts if not os.path.exists(m)]
        for m in inactive:
            del self._active_mounts[m]
        return dict(self._active_mounts)