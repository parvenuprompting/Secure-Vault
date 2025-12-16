import os
import subprocess
import shutil
import re
import sys # <--- Nieuwe import

# --- CONFIGURATIE ---
SCRIPT_NAAM = "main.py"
APP_NAAM = "SecureVault"
ASSETS_DIR = "assets"
ICON_FILE = f"{ASSETS_DIR}/logo.icns"
BG_FILE = f"{ASSETS_DIR}/installer_bg.png"

def haal_versie_op():
    """Leest de VERSION variabele uit main.py"""
    with open(SCRIPT_NAAM, 'r') as f:
        content = f.read()
        match = re.search(r'VERSION\s*=\s*"([^"]+)"', content)
        if match:
            return match.group(1)
    return "0.0.0"

def bouw_app():
    print("🔨 Stap 1: App bouwen met PyInstaller...")
    
    # Assets map meenemen
    add_data_arg = f"{ASSETS_DIR}:{ASSETS_DIR}"

    subprocess.run([
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--clean",
        f"--icon={ICON_FILE}",
        f"--name={APP_NAAM}",
        f"--add-data={add_data_arg}",
        SCRIPT_NAAM
    ], check=True)

def maak_luxe_dmg(versie):
    print("💿 Stap 2: Luxe DMG maken met dmgbuild...")
    
    dmg_naam = f"{APP_NAAM}_v{versie}.dmg"
    app_pad = os.path.join("dist", f"{APP_NAAM}.app")
    
    if os.path.exists(dmg_naam):
        os.remove(dmg_naam)

    settings = {
        'files': [app_pad],
        'symlinks': { 'Applications': '/Applications' },
        'icon': ICON_FILE,
        'icon_locations': {
            f'{APP_NAAM}.app': (140, 120),
            'Applications':   (460, 120)
        },
        'window_rect': ((600, 400), (600, 400)),
    }

    if os.path.exists(BG_FILE):
        settings['background'] = BG_FILE
        print(f"   -> Achtergrond '{BG_FILE}' gevonden.")
    else:
        print(f"   -> Geen installer achtergrond gevonden (is optioneel).")

    # Settings file genereren
    with open("temp_settings.py", "w") as f:
        f.write(f"files = {settings['files']}\n")
        f.write(f"symlinks = {settings['symlinks']}\n")
        f.write(f"icon = '{settings['icon']}'\n")
        f.write(f"icon_locations = {settings['icon_locations']}\n")
        if 'background' in settings:
            f.write(f"background = '{settings['background']}'\n")
        f.write("window_rect = ((100, 100), (600, 400))\n")
        f.write("icon_size = 100\n")

    try:
        # HIER IS DE FIX: We roepen dmgbuild aan via Python zelf
        subprocess.run([
            sys.executable, "-m", "dmgbuild",
            "-s", "temp_settings.py",
            f"{APP_NAAM} Installer",
            dmg_naam
        ], check=True)
        print(f"\n✅ KLAAR! Je installer staat hier: {dmg_naam}")
    except Exception as e:
        print(f"⚠️ DMG maken mislukt: {e}")
    finally:
        if os.path.exists("temp_settings.py"):
            os.remove("temp_settings.py")

if __name__ == "__main__":
    v = haal_versie_op()
    print(f"🚀 Start proces voor {APP_NAAM} versie {v}")
    
    # Oude dist map opruimen
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    
    try:
        bouw_app()
        maak_luxe_dmg(v)
    except Exception as e:
        print(f"\n❌ Er ging iets mis: {e}")