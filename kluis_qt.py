import sys
import os
import subprocess
import time
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QTextEdit, 
                               QFileDialog, QMessageBox, QFormLayout, QProgressBar)
from PySide6.QtCore import QThread, Signal, Qt

class EncryptionWorker(QThread):
    """
    Deze worker voert het zware werk uit op een aparte achtergrond-thread.
    Hierdoor blijft de interface reageren terwijl de bestanden worden gekopieerd.
    """
    log_signal = Signal(str)      # Stuurt tekstberichten naar de GUI
    finish_signal = Signal(bool, str) # Stuurt signaal als klaar (Succes/Fout, Bericht)

    def __init__(self, bron_pad, doel_pad, naam, wachtwoord):
        super().__init__()
        self.bron = bron_pad
        self.doel = doel_pad
        self.naam = naam
        self.ww = wachtwoord

    def log(self, text):
        self.log_signal.emit(text)

    def bereken_map_grootte(self, start_pad):
        """Berekent de totale grootte van een map in bytes."""
        totaal_grootte = 0
        for dirpath, dirnames, filenames in os.walk(start_pad):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # Sla symbolische links over om dubbeltelling te voorkomen
                if not os.path.islink(fp):
                    totaal_grootte += os.path.getsize(fp)
        return totaal_grootte

    def run(self):
        try:
            # Paden samenstellen
            dmg_final = os.path.join(self.doel, f"{self.naam}.dmg")
            dmg_temp = os.path.join(self.doel, f"temp_{self.naam}.dmg")
            vol_naam = "BeveiligdVolume"
            mount_point = f"/Volumes/{vol_naam}"

            self.log(f"--- Start proces voor: {self.naam} ---")

            # 0. Voorbereiding: Grootte berekenen
            self.log("Stap 0/4: Grootte berekenen...")
            grootte_bytes = self.bereken_map_grootte(self.bron)
            
            # Zet om naar Megabytes
            grootte_mb = int(grootte_bytes / (1024 * 1024))
            
            # Voeg 10% buffer toe + 50MB overhead voor het bestandssysteem zelf
            benodigde_mb = int(grootte_mb * 1.1) + 50
            grootte_arg = f"{benodigde_mb}m"
            
            self.log(f"Bron is {grootte_mb} MB. We maken een kluis van {grootte_arg}.")

            # Opruimen oude resten
            if os.path.exists(dmg_temp):
                os.remove(dmg_temp)
            subprocess.run(['hdiutil', 'detach', mount_point, '-quiet', '-force'], capture_output=True)

            # 1. Tijdelijke (onbeveiligde) schijf maken met DYNAMISCHE GROOTTE
            self.log("Stap 1/4: Tijdelijke werkschijf aanmaken...")
            cmd_create = [
                'hdiutil', 'create', '-size', grootte_arg, '-fs', 'HFS+J', 
                '-volname', vol_naam, '-type', 'UDIF', '-o', dmg_temp
            ]
            subprocess.run(cmd_create, check=True, capture_output=True)

            # 2. Koppelen
            self.log("Stap 2/4: Schijf koppelen...")
            cmd_attach = [
                'hdiutil', 'attach', dmg_temp, '-mountpoint', mount_point, 
                '-quiet', '-noverify'
            ]
            subprocess.run(cmd_attach, check=True, capture_output=True)

            # 3. Kopiëren
            self.log("Stap 3/4: Bestanden kopiëren (rsync)...")
            cmd_copy = ['rsync', '-av', f'{self.bron}/', mount_point]
            process_copy = subprocess.run(cmd_copy, capture_output=True, text=True)
            
            if process_copy.returncode != 0:
                raise Exception(f"Fout bij kopiëren: {process_copy.stderr}")
            
            self.log("Kopiëren voltooid.")

            # 4. Converteren naar Encryptie
            self.log("Stap 4/4: Versleutelen en opslaan...")
            
            subprocess.run(['hdiutil', 'detach', mount_point, '-quiet', '-force'], check=True, capture_output=True)

            cmd_convert = [
                'hdiutil', 'convert', dmg_temp, '-format', 'UDZO', 
                '-o', dmg_final, '-encryption', 'AES-256', '-stdinpass'
            ]

            process = subprocess.Popen(
                cmd_convert, 
                stdin=subprocess.PIPE, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            
            # We sturen het wachtwoord ZONDER de \n, zoals eerder gefixt
            stdout, stderr = process.communicate(input=self.ww) 

            if process.returncode != 0:
                raise Exception(f"Encryptie mislukt: {stderr}")

            if os.path.exists(dmg_temp):
                os.remove(dmg_temp)

            self.finish_signal.emit(True, f"Kluis succesvol aangemaakt in:\n{dmg_final}")

        except Exception as e:
            try:
                subprocess.run(['hdiutil', 'detach', mount_point, '-quiet', '-force'], capture_output=True)
                if os.path.exists(dmg_temp): os.remove(dmg_temp)
            except:
                pass
            self.finish_signal.emit(False, str(e))

class KluisApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MacBook Kluis Maker (PySide6)")
        self.resize(600, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # --- Titel ---
        lbl_titel = QLabel("Maak een Beveiligde Kluis (.dmg)")
        lbl_titel.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        lbl_titel.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_titel)
        layout.addSpacing(20)

        # --- Formulier ---
        form_layout = QFormLayout()

        # 1. Bronmap
        self.path_bron = QLineEdit()
        self.btn_bron = QPushButton("Kies Map...")
        self.btn_bron.clicked.connect(self.kies_bron)
        layout_bron = QHBoxLayout()
        layout_bron.addWidget(self.path_bron)
        layout_bron.addWidget(self.btn_bron)
        form_layout.addRow("Te beveiligen map:", layout_bron)

        # 2. Doelmap
        self.path_doel = QLineEdit()
        self.path_doel.setText(os.path.join(os.path.expanduser('~'), "Desktop"))
        self.btn_doel = QPushButton("Kies Map...")
        self.btn_doel.clicked.connect(self.kies_doel)
        layout_doel = QHBoxLayout()
        layout_doel.addWidget(self.path_doel)
        layout_doel.addWidget(self.btn_doel)
        form_layout.addRow("Waar opslaan:", layout_doel)

        # 3. Naam
        self.input_naam = QLineEdit("MijnPriveDocumenten")
        form_layout.addRow("Naam van kluis:", self.input_naam)

        # 4. Wachtwoord
        self.input_ww = QLineEdit()
        self.input_ww.setEchoMode(QLineEdit.EchoMode.Password) # Sterretjes
        form_layout.addRow("Wachtwoord:", self.input_ww)

        layout.addLayout(form_layout)
        layout.addSpacing(20)

        # --- Knoppen en Progress ---
        self.btn_start = QPushButton("START VERSLEUTELING")
        self.btn_start.setMinimumHeight(50)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71; 
                color: white; 
                font-size: 14px; 
                font-weight: bold; 
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #27ae60; }
            QPushButton:disabled { background-color: #95a5a6; }
        """)
        self.btn_start.clicked.connect(self.start_proces)
        layout.addWidget(self.btn_start)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Indeterminate
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # --- Log Venster ---
        lbl_log = QLabel("Status Log:")
        layout.addWidget(lbl_log)
        
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("background-color: #f0f0f0; font-family: Courier;")
        layout.addWidget(self.txt_log)

        self.setLayout(layout)

    # --- Interactie Functies ---

    def kies_bron(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecteer Bronmap")
        if folder:
            self.path_bron.setText(folder)

    def kies_doel(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecteer Opslaglocatie")
        if folder:
            self.path_doel.setText(folder)

    def log_message(self, text):
        self.txt_log.append(text)
        sb = self.txt_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def start_proces(self):
        bron = self.path_bron.text()
        doel = self.path_doel.text()
        naam = self.input_naam.text()
        ww = self.input_ww.text()

        # Validatie
        if not bron or not os.path.exists(bron):
            QMessageBox.warning(self, "Fout", "Selecteer een geldige bronmap.")
            return
        if not doel or not os.path.exists(doel):
            QMessageBox.warning(self, "Fout", "Selecteer een geldige doelmap.")
            return
        if not naam:
            QMessageBox.warning(self, "Fout", "Geef de kluis een naam.")
            return
        if not ww:
            QMessageBox.warning(self, "Fout", "Vul een wachtwoord in.")
            return

        # UI voorbereiden
        self.btn_start.setEnabled(False)
        self.btn_start.setText("BEZIG MET VERSLEUTELEN...")
        self.path_bron.setEnabled(False)
        self.path_doel.setEnabled(False)
        self.input_ww.setEnabled(False)
        self.progress_bar.show()
        self.txt_log.clear()

        # Start de Worker Thread
        self.worker = EncryptionWorker(bron, doel, naam, ww)
        self.worker.log_signal.connect(self.log_message)
        self.worker.finish_signal.connect(self.proces_klaar)
        self.worker.start()

    def proces_klaar(self, succes, bericht):
        self.progress_bar.hide()
        self.btn_start.setEnabled(True)
        self.btn_start.setText("START VERSLEUTELING")
        self.path_bron.setEnabled(True)
        self.path_doel.setEnabled(True)
        self.input_ww.setEnabled(True)

        if succes:
            self.log_message("✅ KLAAR!")
            QMessageBox.information(self, "Succes", bericht)
        else:
            self.log_message("❌ FOUT!")
            QMessageBox.critical(self, "Fout", f"Er ging iets mis:\n{bericht}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = KluisApp()
    window.show()
    sys.exit(app.exec())