from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys

# --- CONFIGURATIE ---
SCRIPT_NAAM = "main.py"
APP_NAAM = "SecureVault"
ASSETS_DIR = "assets"
ICON_FILE = f"{ASSETS_DIR}/logo.icns"
BG_FILE = f"{ASSETS_DIR}/installer_bg.png"


def controleer_vereisten() -> None:
    """Controleert of benodigde tools en assets aanwezig zijn vóór het bouwen."""
    print("🔍 Controleer afhankelijkheden en assets...")

    if platform.system() != "Darwin":
        print(
            "❌ FOUT: SecureVault-builds kunnen alleen op macOS worden gemaakt. "
            "PyInstaller en dmgbuild kunnen hier niet betrouwbaar een macOS-app bouwen."
        )
        sys.exit(1)

    # Check dmgbuild module
    try:
        import dmgbuild  # noqa: F401
    except ImportError:
        print(
            "❌ FOUT: 'dmgbuild' is niet geïnstalleerd.\n"
            "   Voer het volgende commando uit om het te installeren:\n"
            "   pip3 install dmgbuild\n"
        )
        sys.exit(1)

    # Check pyinstaller CLI
    if not shutil.which("pyinstaller") and not shutil.which("pyinstaller.exe"):
        print(
            "❌ FOUT: 'pyinstaller' is niet gevonden in je PATH.\n"
            "   Voer het volgende commando uit om het te installeren:\n"
            "   pip3 install pyinstaller\n"
        )
        sys.exit(1)

    # Check assets
    if not os.path.exists(ASSETS_DIR):
        print(f"⚠️ WAARSCHUWING: Map '{ASSETS_DIR}' niet gevonden.")

    if not os.path.exists(ICON_FILE):
        print(f"⚠️ WAARSCHUWING: Icoon '{ICON_FILE}' niet gevonden. Standaardicoon wordt gebruikt.")


def haal_versie_op() -> str:
    """Leest de VERSION variabele uit main.py"""
    with open(SCRIPT_NAAM, "r", encoding="utf-8") as f:
        content = f.read()
        match = re.search(r'VERSION\s*=\s*"([^"]+)"', content)
        if match:
            return match.group(1)
    return "0.0.0"


def bouw_app() -> None:
    print("🔨 Stap 1: App bouwen met PyInstaller...")

    add_data_arg = f"{ASSETS_DIR}:{ASSETS_DIR}"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--clean",
        f"--name={APP_NAAM}",
        f"--add-data={add_data_arg}",
    ]

    if os.path.exists(ICON_FILE):
        cmd.append(f"--icon={ICON_FILE}")

    cmd.append(SCRIPT_NAAM)

    subprocess.run(cmd, check=True)


def maak_luxe_dmg(versie: str) -> None:
    print("💿 Stap 2: Luxe DMG maken met dmgbuild...")

    dmg_naam = f"{APP_NAAM}_v{versie}.dmg"
    app_pad = os.path.join("dist", f"{APP_NAAM}.app")

    if os.path.exists(dmg_naam):
        os.remove(dmg_naam)

    settings_content = f"""# Dynamisch gegenereerde dmgbuild settings
files = ['{app_pad}']
symlinks = {{ 'Applications': '/Applications' }}
icon_locations = {{
    '{APP_NAAM}.app': (140, 120),
    'Applications': (460, 120)
}}
window_rect = ((100, 100), (600, 400))
icon_size = 100
"""

    if os.path.exists(ICON_FILE):
        settings_content += f"icon = '{ICON_FILE}'\n"

    if os.path.exists(BG_FILE):
        settings_content += f"background = '{BG_FILE}'\n"
        print(f"   -> Achtergrond '{BG_FILE}' gevonden.")

    settings_file = "temp_settings.py"
    with open(settings_file, "w", encoding="utf-8") as f:
        f.write(settings_content)

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "dmgbuild",
                "-s",
                settings_file,
                f"{APP_NAAM} Installer",
                dmg_naam,
            ],
            check=True,
        )
        print(f"\n✅ KLAAR! Je installer staat hier: {dmg_naam}")
        print_notarisatie_instructies(dmg_naam)
    except Exception as e:
        print(f"⚠️ DMG maken mislukt: {e}")
    finally:
        if os.path.exists(settings_file):
            os.remove(settings_file)


def print_notarisatie_instructies(dmg_naam: str) -> None:
    """Print nuttige instructies voor macOS Code-Signing en Notarization voor externe distributie."""
    print(
        "\n--- 📝 MACOS CODE-SIGNING & NOTARIZATION ONTHOUDER ---"
        "\nAls je deze .dmg ooit wilt distribueren aan andere Mac-gebruikers zonder macOS Gatekeeper waarschuwingen:"
        "\n1. Code-sign de app bundle:"
        f"\n   codesign --deep --force --verify --verbose --sign 'Developer ID Application: jouw-naam' dist/{APP_NAAM}.app"
        "\n2. Notariseer het DMG bestand bij Apple:"
        f"\n   xcrun notarytool submit {dmg_naam} --keychain-profile 'jouw-profile' --wait"
        "\n3. Staple het notarisatieticket aan de DMG:"
        f"\n   xcrun stapler staple {dmg_naam}"
        "\n----------------------------------------------------\n"
    )


if __name__ == "__main__":
    controleer_vereisten()
    v = haal_versie_op()
    print(f"🚀 Start bouwproces voor {APP_NAAM} versie {v}")

    # Oude dist map opruimen
    if os.path.exists("dist"):
        shutil.rmtree("dist")

    try:
        bouw_app()
        maak_luxe_dmg(v)
    except Exception as e:
        print(f"\n❌ Er ging iets mis tijdens de build: {e}")
        sys.exit(1)