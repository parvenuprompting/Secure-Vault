import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTextEdit, QFileDialog, 
                               QMessageBox, QProgressBar, QToolButton)
from PySide6.QtCore import QThread, Signal, Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter # <--- QPainter toegevoegd

from src.vault_engine import VaultEngine

# --- WORKER THREAD ---
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

# --- HELPER WIDGET ---
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
        if is_password: 
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
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


# --- HOOFD APPLICATIE ---
class KluisApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SecureVault Pro")
        self.resize(500, 650)
        self.setObjectName("MainWindow")

        # 1. Paden bepalen
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        
        self.path_logo = os.path.join(project_root, 'assets', 'logo.png')
        self.path_bg = os.path.join(project_root, 'assets', 'background.png')

        # Debug check (zie je in de terminal)
        if os.path.exists(self.path_bg):
            print(f"✅ Achtergrond gevonden: {self.path_bg}")
        else:
            print(f"❌ Achtergrond NIET gevonden op: {self.path_bg}")

        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)

        # HEADER
        header_layout = QHBoxLayout()
        logo_label = QLabel()
        if os.path.exists(self.path_logo):
            pixmap = QPixmap(self.path_logo)
            scaled_pixmap = pixmap.scaled(QSize(40, 40), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        
        title = QLabel("SecureVault")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        btn_help = QToolButton()
        btn_help.setText("?")
        btn_help.setCursor(Qt.PointingHandCursor)
        btn_help.setObjectName("helpBtn")
        btn_help.clicked.connect(self.show_help)

        title_center_layout = QHBoxLayout()
        title_center_layout.addWidget(logo_label)
        title_center_layout.addSpacing(10)
        title_center_layout.addWidget(title)
        
        header_layout.addLayout(title_center_layout)
        header_layout.addStretch()
        header_layout.addWidget(btn_help)

        layout.addLayout(header_layout)
        layout.addSpacing(20)

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

        # Actie
        layout.addSpacing(20)
        self.btn_start = QPushButton("START BEVEILIGING")
        self.btn_start.setObjectName("actionBtn")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_process)
        layout.addWidget(self.btn_start)

        # Progress & Log
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Status log verschijnt hier...")
        layout.addWidget(self.log_view)

        self.setLayout(layout)

    def apply_styles(self):
        # We hebben hier GEEN background image meer nodig in de CSS
        # Dat doet de paintEvent functie nu.
        self.setStyleSheet("""
            QWidget { color: #EEE; font-family: ".AppleSystemUIFont"; }
            
            QLabel#title { font-size: 24px; font-weight: bold; color: #FFF; }
            QLabel#inputLabel { color: #CCC; font-size: 11px; font-weight: bold; letter-spacing: 0.5px; }
            
            /* Inputs (Transparant) */
            QLineEdit { 
                background: rgba(30, 30, 30, 0.7); 
                border: 1px solid #555; 
                padding: 10px; 
                border-radius: 6px; 
                color: #FFF; 
                font-size: 13px; 
            }
            QLineEdit:focus { border: 1px solid #4CAF50; background: rgba(30, 30, 30, 0.9); }
            
            /* Knoppen */
            QPushButton { background: rgba(68, 68, 68, 0.85); border: none; padding: 8px; border-radius: 6px; }
            
            QPushButton#actionBtn { 
                background: rgba(76, 175, 80, 0.9); 
                color: #FFF; 
                font-weight: bold; 
                padding: 12px; 
                font-size: 14px; 
                border-radius: 8px; 
            }
            QPushButton#actionBtn:hover { background: rgba(69, 160, 73, 1.0); }
            
            QToolButton#helpBtn { 
                background: rgba(51, 51, 51, 0.8); 
                color: #AAA; 
                border-radius: 12px; 
                font-weight: bold; 
                width: 24px; 
                height: 24px; 
                border: 1px solid #555; 
            }
            QToolButton#helpBtn:hover { background: rgba(85, 85, 85, 1.0); color: #FFF; border-color: #777; }

            QTextEdit { 
                background: rgba(10, 10, 10, 0.7); 
                border: 1px solid #333; 
                color: #0F0; 
                font-family: "Menlo"; 
                font-size: 11px; 
                border-radius: 6px; 
                margin-top: 10px; 
            }
            
            QProgressBar { background: rgba(34, 34, 34, 0.8); border-radius: 4px; height: 6px; margin-top: 10px; }
            QProgressBar::chunk { background: #4CAF50; border-radius: 4px; }
        """)

    # --- HIER GEBEURT DE MAGIE (Aangepast) ---
    def paintEvent(self, event):
        """Tekent de achtergrond 'fixed' (Aspect Fill / Cover)"""
        # Eerst de standaard dingen tekenen (belangrijk!)
        super().paintEvent(event)
        
        if os.path.exists(self.path_bg):
            painter = QPainter(self)
            pixmap = QPixmap(self.path_bg)
            
            # 1. Hoe groot is het venster nu?
            target_size = self.size()
            
            # 2. Schaal het plaatje zodat het het HELE venster bedekt,
            # maar wel zijn verhoudingen behoudt (niet uitrekken).
            # 'Qt.KeepAspectRatioByExpanding' is de sleutel hier.
            scaled_pixmap = pixmap.scaled(
                target_size, 
                Qt.KeepAspectRatioByExpanding, 
                Qt.SmoothTransformation
            )
            
            # 3. Bereken het midden. Omdat het geschaalde plaatje nu misschien
            # groter is dan het venster (breder of hoger), moeten we uitrekenen
            # waar we moeten beginnen met tekenen om het te centreren.
            x = (target_size.width() - scaled_pixmap.width()) // 2
            y = (target_size.height() - scaled_pixmap.height()) // 2
            
            # 4. Teken het geschaalde, gecentreerde plaatje
            painter.drawPixmap(x, y, scaled_pixmap)

    def show_help(self):
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
