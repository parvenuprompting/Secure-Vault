# 🔒 SecureVault for Mac

> Lokale beveiligingskluis voor macOS. De encryptie wordt uitgevoerd door Apple `hdiutil`; SecureVault is een gebruiksinterface en geen zelfstandig cryptografisch protocol.

> **Security note:** SecureVault helpt lokale macOS-gegevens te beschermen met Apple's versleutelde disk images. De beveiliging hangt ook af van macOS, je accountbeveiliging, FileVault, Keychain-instellingen, fysieke toegang en de gekozen wachtwoordsterkte. Gebruik de app niet als vervanging voor een onafhankelijke security-audit of back-upstrategie.

[![CI](https://github.com/parvenuprompting/secure-vault-v2/actions/workflows/ci.yml/badge.svg)](https://github.com/parvenuprompting/secure-vault-v2/actions/workflows/ci.yml)

**SecureVault** is een moderne, minimalistische desktopapplicatie voor macOS waarmee je eenvoudig gevoelige mappen kunt beveiligen in geëncrypteerde kluizen (`.dmg` disk images en `.sparsebundle` meegroeiende pakketten).

De applicatie is geschreven in **Python 3** met **PySide6 (Qt)** en maakt gebruik van native macOS-beveiligingstools (`hdiutil`) met **APFS** en **AES‑256 encryptie**. Geen externe encryptielibraries, geen cloud opslag, geen vendor lock‑in — alles blijft 100% lokaal op je Mac.

[![Version](https://img.shields.io/badge/Version-v2.1.0-blue.svg)](https://github.com/parvenuprompting/secure-vault-v2)
[![Platform](https://img.shields.io/badge/Platform-macOS%20Only-lightgrey?logo=apple&logoColor=white)](https://github.com/parvenuprompting/secure-vault-v2)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Qt](https://img.shields.io/badge/Qt-PySide6-41CD52?logo=qt&logoColor=white)](https://www.qt.io/)
[![Tests](https://img.shields.io/badge/Tests-53%20passed-brightgreen?logo=pytest&logoColor=white)](https://github.com/parvenuprompting/secure-vault-v2)
[![Encryption](https://img.shields.io/badge/Encryption-AES--256-red?logo=apple-pay&logoColor=white)](https://github.com/parvenuprompting/secure-vault-v2)
[![Keychain](https://img.shields.io/badge/Keychain-macOS%20Keychain-success?logo=apple&logoColor=white)](https://github.com/parvenuprompting/secure-vault-v2)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> [!IMPORTANT]
> **macOS Exclusief**: Deze applicatie is specifiek gebouwd voor macOS en maakt gebruik van het ingebouwde command-line hulpprogramma `hdiutil` en de macOS `Keychain`.

---

## ✨ Kenmerken

* **🔐 AES‑256 Encryptie & APFS**
  Gebruikt de industriestandaard voor encryptie via macOS `hdiutil` op het moderne APFS bestandssysteem.

* **◼ Monochroom Zwart-Wit UI**
  Een strak, contrastrijk zwart-wit thema zonder achtergrondafbeelding. Scherpe typografie, dunne randen en een donkere terminal-logbox. De interface is volledig responsief: de inhoud schaalt mee bij elk vensterformaat — van gesplitst split-view tot volledig scherm.

* **🪟 Altijd Gemaximaliseerd Opstarten**
  De applicatie opent automatisch gemaximaliseerd, zodat alle formuliervelden direct volledig zichtbaar zijn zonder handmatig vergroten.

* **🎨 Nieuw Native macOS App-Icoon**
  Minimalistische titanium vault-dial op een matzwart macOS-squircle. Het icoon is als multi-resolutie `.icns` gecompileerd en verschijnt correct in het Dock, Finder, Spotlight en alle andere macOS-contexten.

* **📂 3 Kluisindelingen (Read-Only, Read-Write & SparseBundle)**
  - 📦 **Gecomprimeerd (`UDZO`)**: Vaste omvang, gecomprimeerd en alleen-lezen (ideaal voor veilige archivering).
  - 📝 **Lees / Schrijf (`UDRW`)**: Bestanden toevoegen of verwijderen direct vanuit macOS Finder.
  - 🚀 **Meegroeiend (`UDSB` / Sparse Bundle)**: Neemt alleen de daadwerkelijk gebruikte schijfruimte in en groeit automatisch mee wanneer je bestanden toevoegt.

* **🗝️ macOS Keychain Integratie**
  Sla kluiswachtwoorden veilig op in macOS Sleutelhangertoegang (Keychain) voor 1-klik ontgrendelen zonder telkens je wachtwoord opnieuw in te voeren.

* **🎲 Wachtwoord Generator & Sterktemeter**
  Genereer cryptografisch sterke, willekeurige wachtwoorden met 1-klik automatische kopie naar je klembord en real-time visuele sterktemeting.

* **⏱️ Auto-Lock Timer**
  Automatische beveiligingsvergrendeling na een in te stellen periode van inactiviteit (15, 30 of 60 minuten) om geopende kluizen te beschermen.

* **🔓 Kluis Manager & Context Menu**
  - Ontgrendel bestaande `.dmg` of `.sparsebundle` kluizen met je wachtwoord of vanuit Keychain.
  - Open geopende kluizen direct in macOS Finder met **"🔓 ONTGRENDELEN IN FINDER"**.
  - Bekijk actieve geopende kluizen en recente kluizen via een handig rechtermuisklik contextmenu.
  - Vergrendel geopende kluizen veilig met één klik (**"🔒 Geselecteerde Vergrendelen"**).

* **💬 Nederlandstalige Fouthandeling & Notificaties**
  Duidelijke, vriendelijke foutmeldingen (bijv. verkeerd wachtwoord, in gebruik door Finder) en native macOS notificaties bij acties.

* **🛡️ Lokale beveiliging en veilige defaults**
  Geen cloud, telemetry of externe servers. Bestaande kluizen worden standaard niet overschreven, clipboard-wachtwoorden worden na 60 seconden gewist als ze nog ongewijzigd zijn en bekende byte-buffers worden opgeruimd. Volledige zeroization van Python/Qt-geheugen kan niet worden gegarandeerd.

---

## 📁 Projectstructuur

```
Secure-Vault/
├── main.py              # Hoofd-entrypoint (start de PySide6 applicatie, gemaximaliseerd)
├── src/
│   ├── ui.py            # GUI-componenten (CreateVaultTab, ManageVaultTab, Auto-Lock, Keychain, Dialogs)
│   ├── theme.py         # Monochroom zwart-wit stylesheet
│   └── vault_engine.py  # Kernlogica voor hdiutil, APFS, UDZO/UDRW/UDSB, Keychain, mount & unmount
├── assets/              # App-icoon (logo.png, logo.icns) en installer-achtergrond
├── conftest.py          # Pytest fixtures & headless Qt configuratie
├── tests/               # Unit- & Pytest-Qt GUI testsuite
│   ├── test_vault_engine.py
│   └── test_ui.py
├── .github/workflows/ci.yml # Linux + macOS import/test-controle
├── bouw_alles.py        # Script voor het bouwen van .app & installer .dmg
├── requirements.txt     # Python afhankelijkheden
└── README.md            # Documentatie
```

---

## 🚀 Installatie & Starten

### Via de .dmg installer (aanbevolen)

Download de nieuwste `SecureVault_v2.1.0.dmg`, open het bestand en sleep `SecureVault.app` naar je `Applications` map.

### Vanuit de broncode

```bash
# Virtuele omgeving aanmaken & afhankelijkheden installeren
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Applicatie starten
python3 main.py
```

---

## 🧪 Tests & Coverage

Voer de geautomatiseerde pytest suite uit (53 tests):

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest -v
```

Met coverage rapportage:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest --cov=src --cov-report=term-missing
```

De tests kunnen ook op Linux in offscreen-modus draaien. De echte `hdiutil`, Finder- en Keychain-integratie moet op macOS worden gecontroleerd.

---

## 🔨 App & Installer Bouwen

Om een op zichzelf staande macOS `.app` en een `.dmg` installer te bouwen:

```bash
PATH=".venv/bin:$PATH" .venv/bin/python3 bouw_alles.py
```

Het buildscript:
1. Bouwt de `.app` bundle met PyInstaller (inclusief het native `logo.icns` app-icoon)
2. Plaatst een `.metadata_never_index` bestand in de build-mappen zodat Spotlight de builduitvoer niet indexeert
3. Maakt een installer `.dmg` aan met `dmgbuild`

> [!TIP]
> Na het bouwen kun je de nieuwste versie installeren met:
> ```bash
> rsync -av --delete "dist/SecureVault.app/" "/Applications/SecureVault.app/"
> ```

---

## 📄 Licentie

Gepubliceerd onder de [MIT Licentie](LICENSE).
