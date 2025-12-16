# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],  # <-- AANGEPAST: Dit is je nieuwe startpunt
    pathex=[],
    binaries=[],
    datas=[
        ('assets/logo.png', 'assets'), # <-- AANGEPAST: Neem logo mee naar map 'assets' in de app
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SecureVault',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Zet op True als je foutmeldingen wilt zien tijdens testen
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.icns', # <-- AANGEPAST: Zorg dat je .icns ook in assets staat of pas pad aan
)

app = BUNDLE(
    exe,
    name='SecureVault.app',
    icon='assets/logo.icns',
    bundle_identifier='com.jouwnaam.securevault',
)