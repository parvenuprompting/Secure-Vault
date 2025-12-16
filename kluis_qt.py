import sys
import os
import subprocess
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QTextEdit, 
                               QFileDialog, QMessageBox, QProgressBar, QFrame)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QFont, QIcon

# --- DE WORKER (DE MOTOR) ---
# Deze code is functioneel hetzelfde als voorheen, met de fix voor grootte-berekening en het wachtwoord.

class EncryptionWorker(QThread):
    log_signal = Signal(str)
    finish_signal = Signal(bool, str)

    def __init__(self, bron_pad, doel_pad, naam, wachtwoord):
        super().__init__()
        self.bron = bron_pad
        self.doel = doel_pad
        self.naam = naam
        self.ww = wachtwoord

    def log(self, text):
        self.log_signal.emit(text)

    def bereken_map_grootte(self, start_pad):
        totaal_grootte = 0
        for dirpath, dirnames, filenames in os.walk(start_pad):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    totaal_grootte += os.path.getsize(fp)
        return totaal_grootte

    def run(self):
        try:
            dmg_final = os.path.join(self.doel, f"{self.naam}.dmg")
            dmg_temp = os.path.join(self.doel, f"temp_{self.naam}.dmg")
            vol_naam = "BeveiligdVolume"
            mount_point = f"/Volumes/{vol_naam}"

            self.log(f"🚀 Start proces voor: {self.naam}")

            # Stap 0: Grootte
            self.log("📏 Bezig met berekenen van grootte...")
            grootte_bytes = self.bereken_map_grootte(self.bron)
            grootte_mb = int(grootte_bytes / (1024 * 1024))
            benodigde_mb = int(grootte_mb * 1.1) + 50
            grootte_arg = f"{benodigde_mb}m"
            self.log(f"   Bron: {grootte_mb} MB. Kluis wordt: {grootte_arg}.")

            if os.path.exists(dmg_temp): os.remove(dmg_temp)
            subprocess.run(['hdiutil', 'detach', mount_point, '-quiet', '-force'], capture_output=True)

            # Stap 1: Create
            self.log("🔨 Tijdelijke werkschijf aanmaken...")
            cmd_create = ['hdiutil', 'create', '-size', grootte_arg, '-fs', 'HFS+J', '-volname', vol_naam, '-type', 'UDIF', '-o', dmg_temp]
            subprocess.run(cmd_create, check=True, capture_output=True)

            # Stap 2: Attach
            self.log("🔌 Schijf koppelen...")
            subprocess.run(['hdiutil', 'attach', dmg_temp, '-mountpoint', mount_point, '-quiet', '-noverify'], check=True, capture_output=True)

            # Stap 3: Copy
            self.log("📂 Bestanden kopiëren...")
            process_copy = subprocess.run(['rsync', '-av', f'{self.bron}/', mount_point], capture_output=True, text=True)
            if process_copy.returncode != 0: raise Exception(f"Fout bij kopiëren: {process_copy.stderr}")

            # Stap 4: Convert
            self.log("🔒 Versleutelen...")
            subprocess.run(['hdiutil', 'detach', mount_point, '-quiet', '-force'], check=True, capture_output=True)

            cmd_convert = ['hdiutil', 'convert', dmg_temp, '-format', 'UDZO', '-o', dmg_final, '-encryption', 'AES-256', '-stdinpass']
            process = subprocess.Popen(cmd_convert, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Wachtwoord sturen ZONDER extra enter
            stdout, stderr = process.communicate(input=self.ww)

            if process.returncode != 0: raise Exception(f"Encryptie mislukt: {stderr}")
            if os.path.exists(dmg_temp): os.remove(dmg_temp)

            self.finish_signal.emit(True, f"Kluis succesvol aangemaakt:\n{dmg_final}")

        except Exception as e:
            try:
                subprocess.run(['hdiutil', 'detach', mount_point, '-quiet', '-force'], capture_output=True)
                if os.path.exists(dmg_temp): os.remove(dmg_temp)
            except: pass
            self.finish_signal.emit(False, str(e))


# --- DE MODERN UI ---

class ModernInput(QWidget):
    """ Een helper class voor mooie input velden met een label erboven """
    def __init__(self, label_text, placeholder="", is_password=False, browse_func=None):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,15) # Ruimte onder elk blok
        layout.setSpacing(5)

        # Label
        self.lbl = QLabel(label_text)
        self.lbl.setObjectName("inputLabel") # Voor CSS styling
        layout.addWidget(self.lbl)

        # Container voor input + knop
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0,0,0,0)
        row.setSpacing(10)

        # Input veld
        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        if is_password:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
        row.addWidget(self.input)

        # Browse knop (optioneel)
        if browse_func:
            self.btn = QPushButton("Kies...")
            self.btn.setCursor(Qt.PointingHandCursor)
            self.btn.setObjectName("browseBtn")
            self.btn.setFixedWidth(80)
            self.btn.clicked.connect(browse_func)
            row.addWidget(self.btn)

        layout.addWidget(container)
        self.setLayout(layout)

    def text(self):
        return self.input.text()
    
    def setText(self, text):
        self.input.setText(text)
    
    def setEnabled(self, val):
        self.input.setEnabled(val)
        if hasattr(self, 'btn'): self.btn.setEnabled(val)


class KluisApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SecureVault for Mac")
        self.resize(500, 650)
        
        # --- STYLING (CSS) ---
        # Hier definiëren we de moderne look
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                color: #FFFFFF;
                font-family: -apple-system, "Helvetica Neue", sans-serif;
            }
            QLabel#title {
                font-size: 22px;
                font-weight: bold;
                color: #FFFFFF;
                margin-bottom: 20px;
            }
            QLabel#inputLabel {
                font-size: 13px;
                color: #AAAAAA;
                font-weight: 500;
            }
            QLineEdit {
                background-color: #2D2D2D;
                border: 1px solid #3E3E3E;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                color: white;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
            }
            QPushButton#browseBtn {
                background-color: #333333;
                border: none;
                border-radius: 8px;
                padding: 10px;
                color: #DDDDDD;
            }
            QPushButton#browseBtn:hover {
                background-color: #444444;
            }
            QPushButton#actionBtn {
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
                padding: 15px;
                border: none;
            }
            QPushButton#actionBtn:hover {
                background-color: #45a049;
            }
            QPushButton#actionBtn:disabled {
                background-color: #2e5c31;
                color: #888888;
            }
            QTextEdit {
                background-color: #121212;
                border: 1px solid #333;
                border-radius: 8px;
                color: #00FF00;
                font-family: "Menlo", "Courier New", monospace;
                font-size: 11px;
                padding: 10px;
            }
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #333;
                height: 6px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 40, 30, 40)
        main_layout.setSpacing(5)

        # 1. Header
        header = QLabel("Beveiligde Kluis Maken")
        header.setObjectName("title")
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        # 2. Input Velden (Via onze ModernInput helper)
        self.field_bron = ModernInput("WELKE MAP BEVEILIGEN?", "Selecteer map...", browse_func=self.kies_bron)
        main_layout.addWidget(self.field_bron)

        self.field_doel = ModernInput("WAAR OPSLAAN?", "Selecteer locatie...", browse_func=self.kies_doel)
        self.field_doel.setText(os.path.join(os.path.expanduser('~'), "Desktop"))
        main_layout.addWidget(self.field_doel)

        self.field_naam = ModernInput("NAAM VAN DE KLUIS", "Bijv: PriveDocumenten")
        self.field_naam.setText("MijnPriveKluis")
        main_layout.addWidget(self.field_naam)

        self.field_ww = ModernInput("KIES WACHTWOORD", "Geheim wachtwoord", is_password=True)
        main_layout.addWidget(self.field_ww)

        main_layout.addSpacing(20)

        # 3. Actie Knop
        self.btn_start = QPushButton("START BEVEILIGING")
        self.btn_start.setObjectName("actionBtn")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_proces)
        main_layout.addWidget(self.btn_start)

        # 4. Progress Bar (Indeterminate)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0) # Animatie modus
        self.progress.hide()
        main_layout.addWidget(self.progress)

        main_layout.addSpacing(10)

        # 5. Terminal Log
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setPlaceholderText("Status log verschijnt hier...")
        self.txt_log.setFixedHeight(120)
        main_layout.addWidget(self.txt_log)

        self.setLayout(main_layout)

    # --- LOGICA ---

    def kies_bron(self):
        d = QFileDialog.getExistingDirectory(self, "Kies map")
        if d: self.field_bron.setText(d)

    def kies_doel(self):
        d = QFileDialog.getExistingDirectory(self, "Kies map")
        if d: self.field_doel.setText(d)

    def log_msg(self, text):
        self.txt_log.append(text)
        # Auto scroll
        sb = self.txt_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def start_proces(self):
        bron = self.field_bron.text()
        doel = self.field_doel.text()
        naam = self.field_naam.text()
        ww = self.field_ww.text()

        if not bron or not doel or not naam or not ww:
            QMessageBox.warning(self, "Oeps", "Vul alle velden in aub.")
            return

        # UI Updates
        self.btn_start.setText("BEZIG MET VERSLEUTELEN...")
        self.btn_start.setEnabled(False)
        self.field_bron.setEnabled(False)
        self.field_doel.setEnabled(False)
        self.field_naam.setEnabled(False)
        self.field_ww.setEnabled(False)
        self.progress.show()
        self.txt_log.clear()

        # Start Worker
        self.worker = EncryptionWorker(bron, doel, naam, ww)
        self.worker.log_signal.connect(self.log_msg)
        self.worker.finish_signal.connect(self.klaar)
        self.worker.start()

    def klaar(self, succes, msg):
        self.progress.hide()
        self.btn_start.setText("START BEVEILIGING")
        self.btn_start.setEnabled(True)
        self.field_bron.setEnabled(True)
        self.field_doel.setEnabled(True)
        self.field_naam.setEnabled(True)
        self.field_ww.setEnabled(True)

        if succes:
            self.log_msg("✅ KLAAR!")
            QMessageBox.information(self, "Gelukt", msg)
        else:
            self.log_msg("❌ FOUT!")
            QMessageBox.critical(self, "Fout", msg)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # --- NEW: Icoon instellen ---
    # We zoeken het pad naar logo.png in dezelfde map als het script
    icon_path = os.path.join(os.path.dirname(__file__), 'logo.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    # ---------------------------
    window = KluisApp()
    window.show()
    sys.exit(app.exec())