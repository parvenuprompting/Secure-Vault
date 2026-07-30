# 🔒 SecureVault for Mac

![Screenshot van de applicatie](screenshot.png)

**SecureVault** is een moderne, minimalistische desktopapplicatie voor macOS waarmee je eenvoudig mappen kunt beveiligen in versleutelde kluizen (`.dmg` disk images en `.sparsebundle` meegroeiende pakketten).

De applicatie is geschreven in **Python 3** met **PySide6 (Qt)** en maakt gebruik van native macOS-beveiligingstools (`hdiutil`) met **APFS** en **AES‑256 encryptie**. Geen externe encryptielibraries, geen cloud, geen vendor lock‑in — alles blijft lokaal op je Mac.

![Status](https://img.shields.io/badge/Status-Stable-green)
![Platform](https://img.shields.io/badge/Platform-macOS%20Only-lightgrey)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)

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
├── tests/               # Unit- & integratietests
├── bouw_alles.py        # Script voor het bouwen van .app & installer .dmg
├── requirements.txt     # Python afhankelijkheden
└── README.md            # Documentatie
```

---

## 🚀 Installatie & Starten

```bash
pip3 install -r requirements.txt
python3 main.py
```

---

## 🔨 App & Installer Bouwen

Om een op zichzelf staande macOS `.app` en een `.dmg` installer te bouwen:

```bash
pip3 install dmgbuild pyinstaller
python3 bouw_alles.py
```
