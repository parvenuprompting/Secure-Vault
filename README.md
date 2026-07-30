# 🔒 SecureVault for Mac

![Screenshot van de applicatie](screenshot.png)

**SecureVault** is een moderne, minimalistische desktopapplicatie voor macOS waarmee je eenvoudig mappen kunt beveiligen in versleutelde kluizen (`.dmg` disk images en `.sparsebundle` meegroeiende pakketten).

De applicatie is geschreven in **Python 3** met **PySide6 (Qt)** en maakt gebruik van native macOS-beveiligingstools (`hdiutil`) met **APFS** en **AES‑256 encryptie**. Geen externe encryptielibraries, geen cloud, geen vendor lock‑in — alles blijft lokaal op je Mac.

[![Version](https://img.shields.io/badge/Version-v2.0.0-blue.svg)](https://github.com/parvenuprompting/secure-vault-v2)
[![Platform](https://img.shields.io/badge/Platform-macOS%20Only-lightgrey?logo=apple&logoColor=white)](https://github.com/parvenuprompting/secure-vault-v2)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Qt](https://img.shields.io/badge/Qt-PySide6%206.6%2B-41CD52?logo=qt&logoColor=white)](https://www.qt.io/)
[![Coverage](https://img.shields.io/badge/Coverage-93%25-brightgreen?logo=pytest&logoColor=white)](https://github.com/parvenuprompting/secure-vault-v2)
[![Encryption](https://img.shields.io/badge/Encryption-AES--256-red?logo=pre-commit&logoColor=white)](https://github.com/parvenuprompting/secure-vault-v2)
[![FileSystem](https://img.shields.io/badge/FileSystem-APFS-000000?logo=apple&logoColor=white)](https://github.com/parvenuprompting/secure-vault-v2)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> [!IMPORTANT]
> **macOS Exclusief**: Deze applicatie is specifiek gebouwd voor macOS en vereist het ingebouwde command-line hulpprogramma `hdiutil`.

---

## ✨ Kenmerken

* **🔐 AES‑256 Encryptie & APFS**
  Gebruikt de industriestandaard voor encryptie via macOS `hdiutil` op het moderne APFS bestandssysteem.

* **📂 3 Kluisindelingen (Read-Only & Read-Write)**
  - 📦 **Gecomprimeerd (`UDZO`)**: Vaste omvang, gecomprimeerd en alleen-lezen (ideaal voor archivering).
  - 📝 **Lees / Schrijf (`UDRW`)**: Bestanden toevoegen of verwijderen direct vanuit macOS Finder.
  - 🚀 **Meegroeiend (`UDSB` / Sparse Bundle)**: Neemt alleen de daadwerkelijk gebruikte schijfruimte in en groeit automatisch mee wanneer je bestanden toevoegt in Finder!

* **🔓 Kluis Manager & Finder-integratie**
  - Ontgrendel bestaande `.dmg` of `.sparsebundle` kluizen met je wachtwoord.
  - Open met één klik in macOS Finder (**"🔓 ONTGRENDELEN IN FINDER"**).
  - Bekijk actieve geopende kluizen en vergrendel ze veilig (**"🔒 VEILIG VERGRENDELEN"**).

* **🛡️ Wachtwoordveiligheid & Bevestiging**
  Real-time wachtwoordsterkte-check, visuele vergelijking tussen wachtwoorden, show/hide toggle en veilige geheugen-opschoning (`bytearray` zeroing).

* **⛔ Annuleer-mechanisme**
  Processen kunnen op elk moment veilig geannuleerd worden met automatische opruiming van tijdelijke schijven.

---

## 📁 Projectstructuur

```
Secure-Vault/
├── main.py              # Hoofd-entrypoint (start de PySide6 applicatie)
├── src/
│   ├── ui.py            # GUI-componenten (QTabWidget, CreateVaultTab, ManageVaultTab)
│   └── vault_engine.py  # Kernlogica voor hdiutil, APFS, UDZO/UDRW/UDSB, mount & unmount
├── assets/              # Afbeeldingen, iconen en installer-achtergrond
├── conftest.py          # Pytest fixtures & headless Qt configuratie
├── tests/               # Unit- & Pytest-Qt GUI testsuite (93% coverage)
│   ├── test_vault_engine.py
│   └── test_ui.py
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
pytest --cov=src --cov-report=term-missing
```

---

## 🔨 App & Installer Bouwen

Om een op zichzelf staande macOS `.app` en een `.dmg` installer te bouwen:

```bash
pip install dmgbuild pyinstaller
python3 bouw_alles.py
```

---

## 📄 Licentie

Gepubliceerd onder de MIT Licentie.
