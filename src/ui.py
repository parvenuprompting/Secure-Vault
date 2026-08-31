from __future__ import annotations

import os
import subprocess
import threading
from typing import Optional, List

from PySide6.QtCore import QSize, Qt, QThread, Signal, QSettings, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPainter, QPixmap, QGuiApplication, QAction, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.vault_engine import VaultEngine
from src.theme import stylesheet


# --- QSETTINGS HELPER FUNCTIES ---
def get_recent_vaults() -> List[str]:
    """Haalt de lijst van maximaal 8 bestaande recente kluispaden op uit QSettings."""
    settings = QSettings("SecureVault", "SecureVaultPro")
    raw_list = settings.value("RecentVaults", [])
    if isinstance(raw_list, str):
        raw_list = [raw_list]
    valid_paths = [p for p in raw_list if os.path.exists(p)]
    return valid_paths[:8]


def add_recent_vault(vault_path: str) -> None:
    """Voegt een kluispad toe aan de recente geschiedenis in QSettings."""
    if not vault_path or not os.path.exists(vault_path):
        return
    abs_path = os.path.abspath(vault_path)
    current = get_recent_vaults()
    if abs_path in current:
        current.remove(abs_path)
    current.insert(0, abs_path)
    settings = QSettings("SecureVault", "SecureVaultPro")
    settings.setValue("RecentVaults", current[:8])


# --- WORKER THREAD VOOR AANMAKEN ---
class WorkerThread(QThread):
    log_signal = Signal(str)
    finish_signal = Signal(bool, str)

    def __init__(
        self,
        source: str,
        dest: str,
        name: str,
        password: str,
        format_type: str = "UDZO",
        allow_overwrite: bool = False,
    ):
        super().__init__()
        self.source = source
        self.dest = dest
        self.name = name
        self.password = password
        self.format_type = format_type
        self.allow_overwrite = allow_overwrite
        self.cancel_event = threading.Event()
        self.engine = VaultEngine()

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        success, msg = self.engine.create_vault(
            self.source,
            self.dest,
            self.name,
            self.password,
            format_type=self.format_type,
            progress_callback=lambda m: self.log_signal.emit(m),
            cancel_event=self.cancel_event,
            allow_overwrite=self.allow_overwrite,
        )
        self.finish_signal.emit(success, msg)


# --- HELPER WIDGET FOR INPUTS ---
class ModernInput(QWidget):
    text_changed_signal = Signal(str)

    def __init__(
        self,
        label_text: str,
        browse_func: Optional[object] = None,
        is_password: bool = False,
        tooltip: str = "",
    ):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)

        self.lbl = QLabel(label_text)
        self.lbl.setObjectName("inputLabel")
        if tooltip:
            self.lbl.setToolTip(tooltip)
        layout.addWidget(self.lbl)

        row = QHBoxLayout()
        row.setSpacing(6)

        self.input = QLineEdit()
        if tooltip:
            self.input.setToolTip(tooltip)

        if is_password:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)

        self.input.textChanged.connect(lambda t: self.text_changed_signal.emit(t))
        row.addWidget(self.input)

        if is_password:
            self.btn_toggle = QToolButton()
            self.btn_toggle.setText("👁")
            self.btn_toggle.setToolTip("Wachtwoord tonen / verbergen")
            self.btn_toggle.setCursor(Qt.PointingHandCursor)
            self.btn_toggle.setObjectName("togglePwBtn")
            self.btn_toggle.clicked.connect(self.toggle_password_visibility)
            row.addWidget(self.btn_toggle)

        if browse_func:
            btn_browse = QPushButton("Bladeren...")
            btn_browse.setToolTip("Selecteer via de bestandskiezer")
            btn_browse.setCursor(Qt.PointingHandCursor)
            btn_browse.setObjectName("browseBtn")
            btn_browse.clicked.connect(browse_func)
            row.addWidget(btn_browse)

        layout.addLayout(row)
        self.setLayout(layout)

    def toggle_password_visibility(self) -> None:
        if self.input.echoMode() == QLineEdit.EchoMode.Password:
            self.input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle.setText("🙈")
        else:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle.setText("👁")

    def text(self) -> str:
        return self.input.text()

    def setText(self, t: str) -> None:
        self.input.setText(t)

    def setEnabled(self, v: bool) -> None:
        self.input.setEnabled(v)

    def set_border_status(self, status: Optional[str]) -> None:
        if status == "valid":
            self.input.setStyleSheet(
                "border: 1px solid #4CAF50; background: rgba(30, 45, 30, 0.8);"
            )
        elif status == "invalid":
            self.input.setStyleSheet(
                "border: 1px solid #FF5252; background: rgba(45, 30, 30, 0.8);"
            )
        else:
            self.input.setStyleSheet("")


# --- WIDGET TAB 1: KLUIS AANMAKEN ---
class CreateVaultTab(QWidget):
    def __init__(self, parent_app: KluisApp):
        super().__init__()
        self.app = parent_app
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        self.inp_source = ModernInput(
            "WELKE MAP?",
            self.browse_source,
            tooltip="Selecteer de map die je wilt versleutelen (of sleep een map naar het venster)",
        )
        layout.addWidget(self.inp_source)

        self.inp_dest = ModernInput(
            "WAAR OPSLAAN?",
            self.browse_dest,
            tooltip="Locatie waar het kluisbestand wordt opgeslagen",
        )
        self.inp_dest.setText(os.path.expanduser("~/Desktop"))
        self.allow_overwrite = QCheckBox("Bestaande kluis overschrijven (maakt geen automatische backup)")
        self.allow_overwrite.setObjectName("overwriteChk")
        self.allow_overwrite.setChecked(False)
        self.allow_overwrite.setToolTip("Laat dit uitgeschakeld om bestaande kluizen altijd te beschermen")
        layout.addWidget(self.allow_overwrite)
        layout.addWidget(self.inp_dest)

        self.inp_name = ModernInput(
            "NAAM KLUIS", tooltip="Bestandsnaam van de kluis"
        )
        self.inp_name.setText("MijnKluis")
        layout.addWidget(self.inp_name)

        # FORMAT SELECTION (UDZO / UDRW / UDSB)
        lbl_format = QLabel("KLUIS TYPE (INDELING)")
        lbl_format.setObjectName("inputLabel")
        layout.addWidget(lbl_format)

        self.combo_format = QComboBox()
        self.combo_format.setObjectName("formatCombo")
        self.combo_format.addItem(
            "📦 Gecomprimeerd (Alleen-Lezen .dmg) - Kleinste omvang", "UDZO"
        )
        self.combo_format.addItem(
            "📝 Lees / Schrijf (Aanpasbaar .dmg) - Direct bewerkbaar", "UDRW"
        )
        self.combo_format.addItem(
            "🚀 Meegroeiend (Sparse Bundle .sparsebundle) - Groeit automatisch mee",
            "UDSB",
        )
        self.combo_format.setToolTip(
            "Kies 'Meegroeiend' of 'Lees/Schrijf' als je achteraf in Finder bestanden wilt toevoegen of verwijderen."
        )
        layout.addWidget(self.combo_format)
        layout.addSpacing(6)

        # Wachtwoord inputs & Generator knop
        pw_header_row = QHBoxLayout()
        lbl_pw_title = QLabel("WACHTWOORD")
        lbl_pw_title.setObjectName("inputLabel")
        pw_header_row.addWidget(lbl_pw_title)
        pw_header_row.addStretch()

        self.btn_gen_pass = QPushButton("🎲 Genereer Sterk Wachtwoord")
        self.btn_gen_pass.setObjectName("browseBtn")
        self.btn_gen_pass.setToolTip("Genereer automatisch een cryptografisch sterk wachtwoord en kopieer naar klembord")
        self.btn_gen_pass.setCursor(Qt.PointingHandCursor)
        self.btn_gen_pass.clicked.connect(self.generate_and_copy_password)
        pw_header_row.addWidget(self.btn_gen_pass)

        layout.addLayout(pw_header_row)

        self.inp_pass = ModernInput(
            "",
            is_password=True,
            tooltip="Minimaal 8 tekens. Gebruik cijfers en speciale tekens voor extra veiligheid.",
        )
        self.inp_pass.text_changed_signal.connect(self.validate_passwords)
        layout.addWidget(self.inp_pass)

        # Wachtwoordsterkte indicator
        self.strength_bar = QProgressBar()
        self.strength_bar.setRange(0, 100)
        self.strength_bar.setValue(0)
        self.strength_bar.setFixedHeight(5)
        self.strength_bar.setTextVisible(False)
        self.strength_bar.setObjectName("strengthBar")
        layout.addWidget(self.strength_bar)

        self.lbl_strength = QLabel("")
        self.lbl_strength.setObjectName("strengthLabel")
        layout.addWidget(self.lbl_strength)

        self.inp_pass_confirm = ModernInput(
            "BEVESTIG WACHTWOORD",
            is_password=True,
            tooltip="Herhaal het wachtwoord ter controle",
        )
        self.inp_pass_confirm.text_changed_signal.connect(self.validate_passwords)
        layout.addWidget(self.inp_pass_confirm)

        self.lbl_match = QLabel("")
        self.lbl_match.setObjectName("matchLabel")
        layout.addWidget(self.lbl_match)

        # BUTTONS
        layout.addSpacing(6)
        btn_row = QHBoxLayout()

        self.btn_start = QPushButton("🔒 START BEVEILIGING")
        self.btn_start.setObjectName("actionBtn")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_process)
        btn_row.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("❌ ANNULEREN")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.hide()
        self.btn_cancel.clicked.connect(self.cancel_process)
        btn_row.addWidget(self.btn_cancel)

        layout.addLayout(btn_row)

        # PROGRESS & LOG
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText(
            "Status log verschijnt hier... (of sleep een map naar de app)"
        )
        layout.addWidget(self.log_view)

        self.setLayout(layout)

    def browse_source(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Kies bronmap")
        if d:
            self.inp_source.setText(d)

    def browse_dest(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Kies doelmap")
        if d:
            self.inp_dest.setText(d)

    def generate_and_copy_password(self) -> None:
        self.app.reset_auto_lock_timer()
        new_pw = VaultEngine.generate_secure_password(16)
        self.inp_pass.setText(new_pw)
        self.inp_pass_confirm.setText(new_pw)

        # Automatisch kopiëren naar klembord
        QGuiApplication.clipboard().setText(new_pw)
        if hasattr(self, "clipboard_clear_timer"):
            self.clipboard_clear_timer.stop()
        self.clipboard_clear_timer = QTimer(self)
        self.clipboard_clear_timer.setSingleShot(True)
        self.clipboard_clear_timer.timeout.connect(lambda: self.clear_generated_clipboard(new_pw))
        self.clipboard_clear_timer.start(60_000)

        # Waarschuwing / Informatiewens over het bewaren en noteren van het wachtwoord
        box = QMessageBox(self)
        box.setWindowTitle("Wachtwoord Gegenereerd & Gekopieerd")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText("🎲 <b>Sterk Wachtwoord Gegenereerd & Gekopieerd</b>")
        box.setInformativeText(
            "Het gegenereerde wachtwoord is automatisch ingevuld én <b>gekopieerd naar je klembord</b>!<br><br>"
            "⚠️ <b>BELANGRIJK BERICHT:</b><br>"
            "Noteer of bewaar dit wachtwoord direct op een veilige plek (zoals een wachtwoordmanager of kluis).<br><br>"
            "<i>Als je dit wachtwoord vergeet, is het technisch <u>onmogelijk</u> om de bestanden in de kluis te herstellen!</i>"
        )
        box.exec()

    def clear_generated_clipboard(self, generated_password: str) -> None:
        """Wis het gegenereerde wachtwoord alleen als het nog op het clipboard staat."""
        clipboard = QGuiApplication.clipboard()
        if clipboard.text() == generated_password:
            clipboard.clear()

    def validate_passwords(self) -> None:
        pw = self.inp_pass.text()
        pw_confirm = self.inp_pass_confirm.text()

        if not pw:
            self.strength_bar.setValue(0)
            self.lbl_strength.setText("")
            self.inp_pass.set_border_status(None)
            self.inp_pass_confirm.set_border_status(None)
            self.lbl_match.setText("")
            return

        is_valid, msg, score = VaultEngine.check_password_strength(pw)
        self.strength_bar.setValue(score)

        if score < 50:
            self.strength_bar.setStyleSheet(
                "QProgressBar#strengthBar::chunk { background: #FF5252; }"
            )
            self.lbl_strength.setText(f"Sterkte: {msg}")
            self.lbl_strength.setStyleSheet("color: #FF5252;")
        elif score < 75:
            self.strength_bar.setStyleSheet(
                "QProgressBar#strengthBar::chunk { background: #FFC107; }"
            )
            self.lbl_strength.setText(f"Sterkte: {msg}")
            self.lbl_strength.setStyleSheet("color: #FFC107;")
        else:
            self.strength_bar.setStyleSheet(
                "QProgressBar#strengthBar::chunk { background: #4CAF50; }"
            )
            self.lbl_strength.setText(f"Sterkte: {msg}")
            self.lbl_strength.setStyleSheet("color: #4CAF50;")

        if is_valid:
            self.inp_pass.set_border_status("valid")
        else:
            self.inp_pass.set_border_status("invalid")

        if pw_confirm:
            if pw == pw_confirm:
                self.inp_pass_confirm.set_border_status("valid")
                self.lbl_match.setText("✅ Wachtwoorden komen overeen")
                self.lbl_match.setStyleSheet("color: #4CAF50;")
            else:
                self.inp_pass_confirm.set_border_status("invalid")
                self.lbl_match.setText("❌ Wachtwoorden komen niet overeen")
                self.lbl_match.setStyleSheet("color: #FF5252;")
        else:
            self.inp_pass_confirm.set_border_status(None)
            self.lbl_match.setText("")

    def log(self, msg: str) -> None:
        self.log_view.append(msg)
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def start_process(self) -> None:
        self.app.reset_auto_lock_timer()
        source = self.inp_source.text().strip()
        dest = self.inp_dest.text().strip()
        name = self.inp_name.text().strip()
        pw = self.inp_pass.text()
        pw_confirm = self.inp_pass_confirm.text()
        format_type = self.combo_format.currentData()

        if not all([source, dest, name, pw, pw_confirm]):
            QMessageBox.warning(
                self, "Invoer incompleet", "Vul alle velden in om door te gaan."
            )
            return

        if pw != pw_confirm:
            QMessageBox.warning(
                self,
                "Wachtwoord Mismatch",
                "Het ingestelde wachtwoord en de bevestiging komen niet overeen.",
            )
            return

        is_valid_pw, pw_msg, _ = VaultEngine.check_password_strength(pw)
        if not is_valid_pw:
            QMessageBox.warning(self, "Zwak Wachtwoord", pw_msg)
            return

        try:
            VaultEngine().validate_paths(source, dest)
        except Exception as e:
            QMessageBox.critical(self, "Pad Fout", str(e))
            return

        self.toggle_ui(False)
        self.log_view.clear()
        self.btn_cancel.setText("❌ ANNULEREN")
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.show()

        self.worker = WorkerThread(source, dest, name, pw, format_type=format_type, allow_overwrite=self.allow_overwrite.isChecked())
        self.worker.log_signal.connect(self.log)
        self.worker.finish_signal.connect(self.on_finish)
        self.worker.start()

        # Wis de UI-kopieën zodra stdin aan de worker is doorgegeven.
        self.inp_pass.setText("")
        self.inp_pass_confirm.setText("")

    def cancel_process(self) -> None:
        if self.worker and self.worker.isRunning():
            self.log("⚠️ Annulering aangevraagd... Bezig met netjes opruimen...")
            self.btn_cancel.setText("⌛ Bezig met opruimen...")
            self.btn_cancel.setEnabled(False)
            self.worker.cancel()

    def on_finish(self, success: bool, msg: str) -> None:
        self.btn_cancel.hide()
        self.toggle_ui(True)

        if success:
            add_recent_vault(msg)
            self.app.tab_manage.populate_recents()

            box = QMessageBox(self)
            box.setWindowTitle("Voltooid")
            box.setText("🎉 Kluis Succesvol Aangemaakt")
            box.setInformativeText(f"De kluis is succesvol aangemaakt!\n\nLocatie:\n{msg}")
            box.setIcon(QMessageBox.Information)

            btn_finder = box.addButton("Toon in Finder", QMessageBox.ActionRole)
            box.addButton("Sluiten", QMessageBox.RejectRole)

            box.exec()

            if box.clickedButton() == btn_finder:
                if os.path.exists(msg):
                    subprocess.run(["open", "-R", msg])
        else:
            QMessageBox.critical(
                self, "Proces Afgebroken of Fout", f"Details:\n{msg}"
            )

    def toggle_ui(self, enable: bool) -> None:
        self.btn_start.setEnabled(enable)
        self.inp_source.setEnabled(enable)
        self.inp_dest.setEnabled(enable)
        self.inp_name.setEnabled(enable)
        self.inp_pass.setEnabled(enable)
        self.inp_pass_confirm.setEnabled(enable)
        self.combo_format.setEnabled(enable)
        self.progress.setVisible(not enable)


# --- WIDGET TAB 2: KLUIS OPENEN & BEHEREN ---
class ManageVaultTab(QWidget):
    def __init__(self, parent_app: KluisApp):
        super().__init__()
        self.app = parent_app
        self.engine = VaultEngine()
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # RECENT VAULTS DROPDOWN
        lbl_recents = QLabel("🕒 RECENT GEOPENDE KLUIZEN")
        lbl_recents.setObjectName("inputLabel")
        layout.addWidget(lbl_recents)

        rec_row = QHBoxLayout()
        self.combo_recents = QComboBox()
        self.combo_recents.setObjectName("recentsCombo")
        self.combo_recents.setToolTip("Selecteer een recent gebruikte kluis uit het overzicht")
        self.combo_recents.currentIndexChanged.connect(self.on_recent_selected)
        rec_row.addWidget(self.combo_recents)

        self.btn_open_last = QPushButton("⚡ OPEN LAATSTE")
        self.btn_open_last.setObjectName("browseBtn")
        self.btn_open_last.setToolTip("Selecteer direct de laatst gebruikte kluis")
        self.btn_open_last.setCursor(Qt.PointingHandCursor)
        self.btn_open_last.clicked.connect(self.select_last_vault)
        rec_row.addWidget(self.btn_open_last)

        layout.addLayout(rec_row)
        layout.addSpacing(6)

        # UNLOCK SECTION
        lbl_section = QLabel("🔓 BESTAANDE KLUIS ONTGRENDELEN")
        lbl_section.setObjectName("sectionTitle")
        layout.addWidget(lbl_section)

        self.inp_vault_file = ModernInput(
            "SELECTEER KLUIS (.dmg of .sparsebundle)",
            self.browse_vault_file,
            tooltip="Kies het bestand of pakket dat je wilt ontgrendelen",
        )
        self.inp_vault_file.text_changed_signal.connect(self.check_keychain_autofill)
        layout.addWidget(self.inp_vault_file)

        self.inp_vault_pass = ModernInput(
            "WACHTWOORD",
            is_password=True,
            tooltip="Voer het wachtwoord van deze kluis in",
        )
        layout.addWidget(self.inp_vault_pass)

        # KEYCHAIN CHECKBOX
        self.chk_keychain = QCheckBox("🔑 Wachtwoord bewaren in macOS Sleutelhangertoegang (Keychain)")
        self.chk_keychain.setObjectName("keychainChk")
        self.chk_keychain.setToolTip(
            "Slaat het wachtwoord versleuteld op in de macOS Keychain. "
            "Bij uitvinken wordt het bewaarde wachtwoord direct uit Keychain verwijderd."
        )
        layout.addWidget(self.chk_keychain)
        layout.addSpacing(6)

        self.btn_unlock = QPushButton("🔓 ONTGRENDELEN IN FINDER")
        self.btn_unlock.setObjectName("actionBtn")
        self.btn_unlock.setCursor(Qt.PointingHandCursor)
        self.btn_unlock.clicked.connect(self.unlock_vault)
        layout.addWidget(self.btn_unlock)

        layout.addSpacing(15)

        # ACTIVE MOUNTS SECTION
        lbl_mounts = QLabel("📌 ACTIEVE GEOPENDE KLUISEN")
        lbl_mounts.setObjectName("sectionTitle")
        layout.addWidget(lbl_mounts)

        self.mounts_list = QListWidget()
        self.mounts_list.setObjectName("mountsList")
        self.mounts_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.mounts_list.customContextMenuRequested.connect(self.show_mounts_context_menu)
        self.mounts_list.itemDoubleClicked.connect(self.on_mount_item_double_clicked)
        layout.addWidget(self.mounts_list)

        btn_row = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 Vernieuwen")
        self.btn_refresh.setObjectName("browseBtn")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_mounts)
        btn_row.addWidget(self.btn_refresh)

        self.btn_lock_selected = QPushButton("🔒 Geselecteerde Vergrendelen (Uitwerpen)")
        self.btn_lock_selected.setObjectName("cancelBtn")
        self.btn_lock_selected.setCursor(Qt.PointingHandCursor)
        self.btn_lock_selected.clicked.connect(self.lock_selected_vault)
        btn_row.addWidget(self.btn_lock_selected)

        layout.addLayout(btn_row)
        self.setLayout(layout)

        self.populate_recents()
        self.refresh_mounts()

    def populate_recents(self) -> None:
        self.combo_recents.blockSignals(True)
        self.combo_recents.clear()
        recents = get_recent_vaults()

        if not recents:
            self.combo_recents.addItem("Geen recente kluizen gevonden.", "")
            self.combo_recents.setEnabled(False)
            self.btn_open_last.setEnabled(False)
        else:
            self.combo_recents.setEnabled(True)
            self.btn_open_last.setEnabled(True)
            self.combo_recents.addItem("Selecteer uit geschiedenis...", "")
            for p in recents:
                name = os.path.basename(p)
                display_path = os.path.dirname(p)
                if len(display_path) > 30:
                    display_path = "..." + display_path[-27:]
                label = f"📁 {name} ({display_path})"
                self.combo_recents.addItem(label, p)
        self.combo_recents.blockSignals(False)

    def on_recent_selected(self, index: int) -> None:
        path = self.combo_recents.currentData()
        if path and os.path.exists(path):
            self.inp_vault_file.setText(path)

    def select_last_vault(self) -> None:
        recents = get_recent_vaults()
        if recents:
            self.inp_vault_file.setText(recents[0])
            self.inp_vault_pass.input.setFocus()

    def check_keychain_autofill(self, path: str) -> None:
        path = path.strip()
        if path and os.path.exists(path):
            kc_pw = VaultEngine.get_keychain_password(path)
            if kc_pw:
                self.inp_vault_pass.setText(kc_pw)
                self.chk_keychain.setChecked(True)
            else:
                self.chk_keychain.setChecked(False)

    def browse_vault_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecteer Kluis (.dmg of .sparsebundle)",
            os.path.expanduser("~/Desktop"),
            "Kluizen (*.dmg *.sparsebundle);;DMG Bestanden (*.dmg);;Sparse Bundle (*.sparsebundle);;Alle Bestanden (*)",
            options=QFileDialog.Option.DontResolveSymlinks,
        )

        if not file_path:
            d = QFileDialog.getExistingDirectory(
                self,
                "Selecteer Sparse Bundle Pakket (.sparsebundle)",
                os.path.expanduser("~/Desktop"),
                QFileDialog.Option.DontResolveSymlinks,
            )
            if d and d.endswith(".sparsebundle"):
                file_path = d

        if file_path:
            self.inp_vault_file.setText(file_path)

    def unlock_vault(self) -> None:
        self.app.reset_auto_lock_timer()
        vault_path = self.inp_vault_file.text().strip()
        password = self.inp_vault_pass.text()

        if not vault_path or not password:
            QMessageBox.warning(
                self, "Invoer Incompleet", "Selecteer een kluis en voer het wachtwoord in."
            )
            return

        success, msg, mount_point = self.engine.mount_vault(vault_path, password)

        if success:
            add_recent_vault(vault_path)
            self.populate_recents()

            # Keychain beheer volgens gebruiker-keuze
            if self.chk_keychain.isChecked():
                VaultEngine.save_keychain_password(vault_path, password)
            else:
                VaultEngine.delete_keychain_password(vault_path)

            self.inp_vault_pass.setText("")
            self.refresh_mounts()
            QMessageBox.information(
                self,
                "Ontgrendeld",
                f"🎉 {msg}\n\nDe kluis is geopend in macOS Finder op:\n{mount_point}",
            )
            subprocess.run(["open", mount_point])
        else:
            QMessageBox.critical(self, "Ontgrendelen Mislukt", msg)

    def refresh_mounts(self) -> None:
        self.mounts_list.clear()
        active = self.engine.get_active_mounts()

        if not active:
            item = QListWidgetItem("Geen actieve geopende kluizen.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.mounts_list.addItem(item)
            return

        for mount_point, vault_path in active.items():
            vault_name = os.path.basename(vault_path)
            size_str = self.engine.get_vault_disk_size(vault_path)
            item_text = f"📂 {vault_name} ({size_str})  -->  {mount_point}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, mount_point)
            item.setToolTip(f"Kluisbestand: {vault_path}\nMountpoint: {mount_point}\nDubbelklik om te openen in Finder")
            self.mounts_list.addItem(item)

    def on_mount_item_double_clicked(self, item: QListWidgetItem) -> None:
        mount_point = item.data(Qt.ItemDataRole.UserRole)
        if mount_point and os.path.exists(mount_point):
            subprocess.run(["open", mount_point])

    def show_mounts_context_menu(self, point) -> None:
        item = self.mounts_list.itemAt(point)
        if not item or not item.data(Qt.ItemDataRole.UserRole):
            return

        mount_point = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)

        act_open = QAction("📂 Openen in Finder", self)
        act_open.triggered.connect(lambda: subprocess.run(["open", mount_point]))
        menu.addAction(act_open)

        act_copy = QAction("📋 Kopieer pad naar klembord", self)
        act_copy.triggered.connect(lambda: QGuiApplication.clipboard().setText(mount_point))
        menu.addAction(act_copy)

        menu.addSeparator()

        act_lock = QAction("🔒 Veilig Vergrendelen (Uitwerpen)", self)
        act_lock.triggered.connect(lambda: self.lock_vault_path(mount_point))
        menu.addAction(act_lock)

        menu.exec(self.mounts_list.mapToGlobal(point))

    def lock_vault_path(self, mount_point: str) -> None:
        self.app.reset_auto_lock_timer()
        success, msg = self.engine.unmount_vault(mount_point)

        if success:
            QMessageBox.information(self, "Vergrendeld", msg)
            self.refresh_mounts()
        else:
            reply = QMessageBox.question(
                self,
                "Vergrendelen Mislukt",
                f"{msg}\n\nWil je het uitwerpen forceren?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                f_success, f_msg = self.engine.unmount_vault(mount_point, force=True)
                if f_success:
                    QMessageBox.information(self, "Geforceerd Vergrendeld", f_msg)
                else:
                    QMessageBox.critical(self, "Fout", f_msg)
                self.refresh_mounts()

    def lock_selected_vault(self) -> None:
        current_item = self.mounts_list.currentItem()
        if not current_item or not current_item.data(Qt.ItemDataRole.UserRole):
            QMessageBox.warning(
                self, "Geen Selectie", "Selecteer eerst een actieve kluis uit de lijst."
            )
            return
        mount_point = current_item.data(Qt.ItemDataRole.UserRole)
        self.lock_vault_path(mount_point)


# --- HOOFD APPLICATIE VENSTER ---
class KluisApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SecureVault Pro")
        self.resize(560, 780)
        self.setMinimumSize(520, 720)
        self.setObjectName("MainWindow")
        self.setAcceptDrops(True)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)

        self.path_logo = os.path.join(project_root, "assets", "logo.png")
        self.path_bg = os.path.join(project_root, "assets", "background.png")

        # Auto-Lock Timer Setup
        self.auto_lock_timer = QTimer(self)
        self.auto_lock_timer.timeout.connect(self.on_auto_lock_timeout)

        self.setup_ui()
        self.apply_styles()

    def setup_ui(self) -> None:
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(24, 24, 24, 24)

        # HEADER
        header_layout = QHBoxLayout()
        logo_label = QLabel()
        if os.path.exists(self.path_logo):
            pixmap = QPixmap(self.path_logo)
            scaled_pixmap = pixmap.scaled(
                QSize(42, 42), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(scaled_pixmap)

        title_container = QVBoxLayout()
        title_container.setSpacing(0)
        title = QLabel("SecureVault")
        title.setObjectName("title")
        subtitle = QLabel("AES-256 Encrypted macOS Vault Manager")
        subtitle.setObjectName("subtitle")

        title_container.addWidget(title)
        title_container.addWidget(subtitle)

        # AUTO LOCK COMBO IN HEADER
        self.combo_autolock = QComboBox()
        self.combo_autolock.setObjectName("autolockCombo")
        self.combo_autolock.addItem("⏰ Auto-Lock: Uit", 0)
        self.combo_autolock.addItem("⏰ Auto-Lock: 15 min", 15)
        self.combo_autolock.addItem("⏰ Auto-Lock: 30 min", 30)
        self.combo_autolock.addItem("⏰ Auto-Lock: 60 min", 60)
        self.combo_autolock.setToolTip("Automatisch alle kluizen vergrendelen bij inactiviteit")
        self.combo_autolock.currentIndexChanged.connect(self.on_autolock_setting_changed)

        btn_help = QToolButton()
        btn_help.setText("?")
        btn_help.setToolTip("Handleiding en informatie")
        btn_help.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_help.setObjectName("helpBtn")
        btn_help.clicked.connect(self.show_help)

        title_center_layout = QHBoxLayout()
        title_center_layout.addWidget(logo_label)
        title_center_layout.addSpacing(10)
        title_center_layout.addLayout(title_container)

        header_layout.addLayout(title_center_layout)
        header_layout.addStretch()
        header_layout.addWidget(self.combo_autolock)
        header_layout.addSpacing(6)
        header_layout.addWidget(btn_help)

        main_layout.addLayout(header_layout)
        main_layout.addSpacing(10)

        # TABS
        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        self.tabs.currentChanged.connect(lambda idx: self.reset_auto_lock_timer())

        self.tab_create = CreateVaultTab(self)
        self.tab_manage = ManageVaultTab(self)

        self.tabs.addTab(self.tab_create, "➕ Nieuwe Kluis")
        self.tabs.addTab(self.tab_manage, "🔓 Kluis Beheren")

        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    def on_autolock_setting_changed(self, index: int) -> None:
        mins = self.combo_autolock.currentData()
        if mins > 0:
            ms = mins * 60 * 1000
            self.auto_lock_timer.start(ms)
        else:
            self.auto_lock_timer.stop()

    def reset_auto_lock_timer(self) -> None:
        mins = self.combo_autolock.currentData()
        if mins > 0:
            ms = mins * 60 * 1000
            self.auto_lock_timer.start(ms)

    def on_auto_lock_timeout(self) -> None:
        unmounted = VaultEngine().unmount_all_vaults()
        if unmounted > 0:
            self.tab_manage.refresh_mounts()

    def apply_styles(self) -> None:
        self.setStyleSheet(stylesheet())

    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#F4F1E9"))

        if os.path.exists(self.path_bg):
            pixmap = QPixmap(self.path_bg)

            target_size = self.size()
            scaled_pixmap = pixmap.scaled(
                target_size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
            )

            painter.drawPixmap(0, 0, scaled_pixmap)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        self.reset_auto_lock_timer()
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path) and not path.endswith(".sparsebundle"):
                self.tab_create.inp_source.setText(path)
                self.tabs.setCurrentIndex(0)
                self.tab_create.log(f"📁 Map geïmporteerd via Drag & Drop: {path}")
            elif path.endswith(".dmg") or path.endswith(".sparsebundle"):
                self.tab_manage.inp_vault_file.setText(path)
                self.tabs.setCurrentIndex(1)
            else:
                QMessageBox.warning(
                    self,
                    "Geen map",
                    "Gelieve een map of kluisbestand te slepen in plaats van een los bestand.",
                )

    def show_help(self) -> None:
        self.reset_auto_lock_timer()
        msg = QMessageBox(self)
        msg.setWindowTitle("Handleiding")
        msg.setText("<b>Hoe werkt SecureVault Pro v2.1?</b>")
        msg.setInformativeText(
            "<br>"
            "1. <b>Nieuwe Kluis Aanmaken:</b><br>"
            "   - Selecteer een bronmap (of sleep hem naar het venster).<br>"
            "   - Kies het type: <i>Gecomprimeerd (Read-Only)</i>, <i>Lees/Schrijf (.dmg)</i> of <i>Meegroeiend (.sparsebundle)</i>.<br>"
            "   - Voer een sterk wachtwoord in en start de beveiliging.<br><br>"
            "2. <b>Kluis Beheren & Ontgrendelen:</b><br>"
            "   - Kies een recente kluis uit de dropdown of blader naar een `.dmg`/`.sparsebundle`.<br>"
            "   - Vink eventueel <i>'Wachtwoord bewaren in Keychain'</i> aan.<br>"
            "   - Klik op <b>'ONTGRENDELEN IN FINDER'</b> om te openen.<br>"
            "   - Rechtermuisklik of dubbelklik op actieve kluisen voor snelle acties (Openen, Vergrendelen, Pad kopiëren).<br><br>"
            "3. <b>Auto-Lock Timer:</b><br>"
            "   - Stel bovenaan een auto-lock timer in (15/30/60 min) om geopende kluizen bij inactiviteit automatisch veilig af te sluiten.<br>"
        )
        msg.setIcon(QMessageBox.Information)
        msg.exec()

    def closeEvent(self, event) -> None:
        """Probeer actieve kluizen veilig te ontkoppelen vóór het venster sluit."""
        active_mounts = VaultEngine().get_active_mounts()
        if active_mounts:
            choice = QMessageBox.question(
                self,
                "Actieve kluizen",
                f"Er zijn nog {len(active_mounts)} kluis(en) geopend. Nu veilig vergrendelen?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if choice != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            VaultEngine().unmount_all_vaults()
        event.accept()