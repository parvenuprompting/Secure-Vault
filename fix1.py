import os
import shutil

def setup_project_structure():
    print("🚀 Start herstructurering van project...")

    # Huidige map
    base_dir = os.getcwd()

    # 1. Mappen aanmaken
    dirs_to_create = ['src', 'assets']
    for d in dirs_to_create:
        path = os.path.join(base_dir, d)
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"✅ Map aangemaakt: {d}/")
        else:
            print(f"ℹ️  Map bestaat al: {d}/")

    # 2. Bestanden verplaatsen naar 'assets'
    files_to_move = ['logo.png', 'installer_bg.png', 'logo.icns']
    
    for filename in files_to_move:
        src_path = os.path.join(base_dir, filename)
        dst_path = os.path.join(base_dir, 'assets', filename)
        
        if os.path.exists(src_path):
            # Check of doel al bestaat, zo ja verwijderen we die eerst (overschrijven)
            if os.path.exists(dst_path):
                os.remove(dst_path)
            shutil.move(src_path, dst_path)
            print(f"📦 Verplaatst: {filename} -> assets/")
        else:
            print(f"⚠️  Niet gevonden (overgeslagen): {filename}")

    # 3. Lege __init__.py aanmaken in src
    init_path = os.path.join(base_dir, 'src', '__init__.py')
    if not os.path.exists(init_path):
        with open(init_path, 'w') as f:
            pass # Leeg bestand
        print("📄 Aangemaakt: src/__init__.py")

    # 4. requirements.txt aanmaken
    req_path = os.path.join(base_dir, 'requirements.txt')
    requirements = "PySide6\ndmgbuild\nPillow"
    with open(req_path, 'w') as f:
        f.write(requirements)
    print("📝 Aangemaakt: requirements.txt")

    # 5. Oude rommel opruimen
    files_to_delete = ['encrypt.py']
    for filename in files_to_delete:
        path = os.path.join(base_dir, filename)
        if os.path.exists(path):
            os.remove(path)
            print(f"🗑️  Verwijderd: {filename} (was dubbele code)")

    print("\n✨ Structuur update voltooid!")
    print("Je mapstructuur is nu klaar voor de nieuwe 'Engine' en 'UI' code.")

if __name__ == "__main__":
    setup_project_structure()