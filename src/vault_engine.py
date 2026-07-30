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
    Padvalidatie, grootte berekenen, geëncrypteerde DMG/SparseBundle aanmaken,
    ontgrendelen/mounten en veilig vergrendelen/uitwerpen.
    Volledig ontkoppeld van de UI.
    """

    FORMAT_DESCRIPTIONS = {
        "UDZO": "Gecomprimeerd (Alleen-Lezen .dmg)",
        "UDRW": "Lees / Schrijf (Aanpasbaar .dmg)",
        "UDSB": "Meegroeiend (Sparse Bundle .sparsebundle)",
    }

    _active_mounts: Dict[str, str] = {}  # {mount_point: vault_path}

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

            if os.path.exists(dmg_final):
                log("⚠️ Bestaande kluis met dezelfde naam wordt overschreven...")
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
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    self.cleanup(dmg_final)
                    return False, "Proces geannuleerd door gebruiker."
                threading.Event().wait(0.2)

            stdout, stderr = process.communicate()

            if process.returncode != 0:
                self.cleanup(dmg_final)
                error_msg = stderr.strip() if stderr else "Onbekende hdiutil fout."
                log(f"❌ Encryptiefout: {error_msg}")
                return False, f"hdiutil fout ({process.returncode}): {error_msg}"

            log(f"🎉 Succes! Kluis is aangemaakt op:\n{dmg_final}")
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
        Retourneert: (success, message, mount_point)
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
                err_msg = stderr.strip() if stderr else "Wachtwoord onjuist of bestand beschadigd."
                logger.error("Failed to attach vault %s: %s", vault_path, err_msg)
                return False, f"Kon kluis niet ontgrendelen: {err_msg}", ""

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

        err_msg = res.stderr.strip()
        logger.warning("Unmount failed for %s: %s", mount_point, err_msg)
        return (
            False,
            f"Kon kluis niet uitwerpen ({err_msg}).\n\n"
            "Mogelijk staan er bestanden of een Finder-venster open op deze kluis. "
            "Sluit geopende bestanden en probeer het opnieuw.",
        )

    def get_active_mounts(self) -> Dict[str, str]:
        """Retourneert een kopie van het woordenboek met actieve mounts {mount_point: vault_path}."""
        # Opschonen van mounts die inmiddels extern ontkoppeld zijn
        inactive = [m for m in self._active_mounts if not os.path.exists(m)]
        for m in inactive:
            del self._active_mounts[m]
        return dict(self._active_mounts)