import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTextEdit, QFileDialog, 
                               QMessageBox, QProgressBar, QToolButton) # QToolButton toegevoegd
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QIcon, QFont

from src.vault_engine import VaultEngine

# ... (WorkerThread klasse blijft ongewijzigd) ...
class WorkerThread(QThread):
    log_signal = Signal(str)
    finish_signal = Signal(bool, str)

    def __init__(self, source, dest, name, password):
        super().__init__()
        self.source = source
        self.dest = dest
        self.name = name
        self.password = password
        self.engine = VaultEngine()

    def run(self):
        success, msg = self.engine.create_vault(
            self.source, self.dest, self.name, self.password, 
            progress_callback=lambda m: self.log_signal.emit(m)
        )
        self.finish_signal.emit(success, msg)

# ... (ModernInput klasse blijft ongewijzigd) ...
class ModernInput(QWidget):
    def __init__(self, label_text, browse_func=None, is_password=False):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,10)
        self.lbl = QLabel(label_text)
        self.lbl.setObjectName("inputLabel")
        layout.addWidget(self.lbl)
        
        row = QHBoxLayout()
        self.input = QLineEdit()
        if is_password: self.input.setEchoMode(QLineEdit.EchoMode.Password)
        row.addWidget(self.input)
        
        if browse_func:
            btn = QPushButton("...")
            btn.setFixedWidth(40)
            btn.clicked.connect(browse_func)
            row.addWidget(btn)
        
        layout.addLayout(row)
        self.setLayout(layout)

    def text(self): return self.input.text()
    def setText(self, t): self.input.setText(t)
    def setEnabled(self, v): self.input.setEnabled(v)


class KluisApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SecureVault Pro")
        self.resize(500, 650) # Iets langer gemaakt voor comfort
        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)

        # --- HEADER (Titel + Help Knop) ---
        header_layout = QHBoxLayout()
        
        # Titel
        title = QLabel("SecureVault")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        
        # Help Knop
        btn_help = QToolButton()
        btn_help.setText("?")
        btn_help.setCursor(Qt.PointingHandCursor)
        btn_help.setObjectName("helpBtn")
        btn_help.setToolTip("Bekijk handleiding")
        btn_help.clicked.connect(self.show_help)

        # We gebruiken stretches om de titel in het midden te houden
        header_layout.addWidget(btn_help) # Een dummy knop links voor balans (optioneel, nu weggelaten)
        header_layout.addStretch()
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(btn_help) # De echte knop rechts

        layout.addLayout(header_layout)
        layout.addSpacing(10)
        # ----------------------------------

        # Inputs
        self.inp_source = ModernInput("WELKE MAP?", self.browse_source)
        layout.addWidget(self.inp_source)
        
        self.inp_dest = ModernInput("WAAR OPSLAAN?", self.browse_dest)
        self.inp_dest.setText(os.path.expanduser("~/Desktop"))
        layout.addWidget(self.inp_dest)

        self.inp_name = ModernInput("NAAM KLUIS")
        self.inp_name.setText("MijnKluis")
        layout.addWidget(self.inp_name)

        self.inp_pass = ModernInput("WACHTWOORD", is_password=True)
        layout.addWidget(self.inp_pass)

        # Action
        layout.addSpacing(20)
        self.btn_start = QPushButton("START BEVEILIGING")
        self.btn_start.setObjectName("actionBtn")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_process)
        layout.addWidget(self.btn_start)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        # Log
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Status log verschijnt hier...")
        layout.addWidget(self.log_view)

        self.setLayout(layout)

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget { background: #1E1E1E; color: #EEE; font-family: ".AppleSystemUIFont"; }
            
            QLabel#title { font-size: 24px; font-weight: bold; margin-bottom: 5px; color: #FFF; }
            QLabel#inputLabel { color: #AAA; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; }
            
            QLineEdit { background: #2D2D2D; border: 1px solid #444; padding: 10px; border-radius: 6px; color: #FFF; font-size: 13px; }
            QLineEdit:focus { border: 1px solid #4CAF50; }
            
            QPushButton { background: #444; border: none; padding: 8px; border-radius: 6px; }
            
            /* De groene actie knop */
            QPushButton#actionBtn { background: #4CAF50; color: #FFF; font-weight: bold; padding: 12px; font-size: 14px; border-radius: 8px; }
            QPushButton#actionBtn:hover { background: #45a049; }
            QPushButton#actionBtn:pressed { background: #3e8e41; }
            
            /* Het Help knopje */
            QToolButton#helpBtn { background: #333; color: #AAA; border-radius: 12px; font-weight: bold; width: 24px; height: 24px; border: 1px solid #444; }
            QToolButton#helpBtn:hover { background: #555; color: #FFF; border-color: #666; }

            QTextEdit { background: #111; border: 1px solid #333; color: #0F0; font-family: "Menlo"; font-size: 11px; border-radius: 6px; margin-top: 10px; }
            
            QProgressBar { background: #222; border-radius: 4px; height: 6px; margin-top: 10px; }
            QProgressBar::chunk { background: #4CAF50; border-radius: 4px; }
        """)

    def show_help(self):
        """Toont de handleiding in een pop-up"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Handleiding")
        msg.setText("<b>Hoe werkt SecureVault?</b>")
        msg.setInformativeText(
            "<br>"
            "1. <b>Kies Map:</b> Selecteer de map die je wilt beveiligen.<br>"
            "2. <b>Locatie:</b> Kies waar de kluis (.dmg) moet komen.<br>"
            "3. <b>Beveilig:</b> Verzin een naam en een sterk wachtwoord.<br>"
            "4. <b>Start:</b> De app maakt een versleutelde kluis aan.<br><br>"
            "<i style='color:#FF6B6B'>⚠️ Let op: Je originele map wordt niet automatisch verwijderd. "
            "Controleer eerst of de kluis werkt en verwijder daarna zelf het origineel.</i>"
        )
        msg.setIcon(QMessageBox.Information)
        msg.exec()

    def browse_source(self):
        d = QFileDialog.getExistingDirectory(self, "Kies map")
        if d: self.inp_source.setText(d)

    def browse_dest(self):
        d = QFileDialog.getExistingDirectory(self, "Kies map")
        if d: self.inp_dest.setText(d)

    def log(self, msg):
        self.log_view.append(msg)
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def start_process(self):
        source = self.inp_source.text()
        dest = self.inp_dest.text()
        name = self.inp_name.text()
        pw = self.inp_pass.text()

        if not all([source, dest, name, pw]):
            QMessageBox.warning(self, "Let op", "Vul alle velden in.")
            return

        self.toggle_ui(False)
        self.log_view.clear()
        
        self.worker = WorkerThread(source, dest, name, pw)
        self.worker.log_signal.connect(self.log)
        self.worker.finish_signal.connect(self.on_finish)
        self.worker.start()

    def on_finish(self, success, msg):
        self.toggle_ui(True)
        if success:
            QMessageBox.information(self, "Gelukt", msg)
        else:
            QMessageBox.critical(self, "Fout", msg)

    def toggle_ui(self, enable):
        self.btn_start.setEnabled(enable)
        self.inp_source.setEnabled(enable)
        self.inp_dest.setEnabled(enable)
        self.inp_name.setEnabled(enable)
        self.inp_pass.setEnabled(enable)
        self.progress.setVisible(not enable)