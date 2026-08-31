# 🔒 SecureVault for Mac

![Screenshot van SecureVault](screenshot.png)

[![CI](https://github.com/parvenuprompting/secure-vault-v2/actions/workflows/ci.yml/badge.svg)](https://github.com/parvenuprompting/secure-vault-v2/actions/workflows/ci.yml)

**SecureVault** is een moderne, minimalistische desktopapplicatie voor macOS waarmee je eenvoudig gevoelige mappen kunt beveiligen in geëncrypteerde kluizen (`.dmg` disk images en `.sparsebundle` meegroeiende pakketten).

De applicatie is geschreven in **Python 3** met **PySide6 (Qt)** en maakt gebruik van native macOS-beveiligingstools (`hdiutil`) met **APFS** en **AES‑256 encryptie**. Geen externe encryptielibraries, geen cloud opvaardigen, geen vendor lock‑in — alles blijft 100% lokaal op je Mac.

[![Version](https://img.shields.io/badge/Version-v2.1.0-blue.svg)](https://github.com/parvenuprompting/secure-vault-v2)
[![Platform](https://img.shields.io/badge/Platform-macOS%20Only-lightgrey?logo=apple&logoColor=white)](https://github.com/parvenuprompting/secure-vault-v2)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Qt](https://img.shields.io/badge/Qt-PySide6-41CD52?logo=qt&logoColor=white)](https://www.qt.io/)
[![Tests](https://img.shields.io/badge/Tests-49%20passed-brightgreen?logo=pytest&logoColor=white)](https://github.com/parvenuprompting/secure-vault-v2)
[![Coverage](https://img.shields.io/badge/Coverage-91%25-brightgreen?logo=pytest&logoColor=white)](https://github.com/parvenuprompting/secure-vault-v2)
[![Encryption](https://img.shields.io/badge/Encryption-AES--256-red?logo=apple-pay&logoColor=white)](https://github.com/parvenuprompting/secure-vault-v2)
[![Keychain](https://img.shields.io/badge/Keychain-macOS%20Keychain-success?logo=apple&logoColor=white)](https://github.com/parvenuprompting/secure-vault-v2)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> [!IMPORTANT]
> **macOS Exclusief**: Deze applicatie is specifiek gebouwd voor macOS en maakt gebruik van het ingebouwde command-line hulpprogramma `hdiutil` en de macOS `Keychain`.

---

## ✨ Kenmerken

* **🔐 AES‑256 Encryptie & APFS**
  Gebruikt de industriestandaard voor encryptie via macOS `hdiutil` op het moderne APFS bestandssysteem.

* **◼ Monochrome Editorial UI**
  Een rustige zwart-wit interface met papierachtergrond, inktkleur, veel witruimte, dunne lijnen en één terughoudend oranje accent. De functionaliteit blijft ongewijzigd; alleen de presentatie is aangepast.

* **📂 3 Kluisindelingen (Read-Only, Read-Write & SparseBundle)**
  - 📦 **Gecomprimeerd (`UDZO`)**: Vaste omvang, gecomprimeerd en alleen-lezen (ideaal voor veilige archivering).
  - 📝 **Lees / Schrijf (`UDRW`)**: Bestanden toevoegen of verwijderen direct vanuit macOS Finder.
  - 🚀 **Meegroeiend (`UDSB` / Sparse Bundle)**: Neemt alleen de daadwerkelijk gebruikte schijfruimte in en groeit automatisch mee wanneer je bestanden toevoegt!

* **🗝️ macOS Keychain Integratie**
  Sla kluiswachtwoorden veilig op in macOS Sleutelhangertoegang (Keychain) voor 1-klik ontgrendelen zonder telkens je wachtwoord opnieuw in te voeren.

* **🎲 Wachtwoord Generator & Sterktemeter**
  Genereer cryptografisch sterke, willekeurige wachtwoorden met 1-klik automatische kopie naar je klembord en real-time visuele sterktemeting.

* **⏱️ Auto-Lock Timer**
  Automatische beveiligingsvergrendeling na een in te stellen periode van inactiviteit (bijv. 5, 15 of 30 minuten) om geopende kluizen te beschermen.

* **🔓 Kluis Manager & Context Menu**
  - Ontgrendel bestaande `.dmg` of `.sparsebundle` kluizen met je wachtwoord of vanuit Keychain.
  - Open geopende kluizen direct in macOS Finder met **"🔓 ONTGRENDELEN IN FINDER"**.
  - Bekijk actieve geopende kluizen en recente kluizen via een handig rechtermuisklik contextmenu.
  - Vergrendel geopende kluizen veilig met één klik (**"🔒 VEILIG VERGRENDELEN"**).

* **💬 Nederlandstalige Fouthandeling & Notificaties**
  Duidelijke, vriendelijke foutmeldingen (bijv. verkeerd wachtwoord, in gebruik door Finder) en native macOS notificaties bij acties.

* **🛡️ Zero-Trust Security & Opschoning**
  Geen cloud, geen telemetry of externe servers. Gevoelige gegevens in het geheugen worden na gebruik overschreven (`bytearray` zeroing).

---

## 📁 Projectstructuur

```
Secure-Vault/
├── main.py              # Hoofd-entrypoint (start de PySide6 applicatie)
├── src/
│   ├── ui.py            # GUI-componenten (CreateVaultTab, ManageVaultTab, Auto-Lock, Keychain, Dialogs)
│   └── vault_engine.py  # Kernlogica voor hdiutil, APFS, UDZO/UDRW/UDSB, Keychain, mount & unmount
├── assets/              # Afbeeldingen, iconen en installer-achtergrond
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

Voer de geautomatiseerde pytest suite uit met coverage rapportage:

```bash
QT_QPA_PLATFORM=offscreen pytest --cov=src --cov-report=term-missing
```

De tests kunnen ook op Linux in offscreen-modus draaien. De echte `hdiutil`, Finder- en Keychain-integratie moet op macOS worden gecontroleerd.

---

## 🔨 App & Installer Bouwen

Om een op zichzelf staande macOS `.app` en een `.dmg` installer te bouwen:

```bash
pip install dmgbuild pyinstaller
python3 bouw_alles.py
```

---

## 📄 Licentie

Gepubliceerd onder de [MIT Licentie](LICENSE).
