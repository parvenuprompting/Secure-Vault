from __future__ import annotations

import os
import subprocess
import threading
from typing import Optional, List, Dict, Set

from PySide6.QtCore import QSize, Qt, QThread, Signal, QSettings, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPixmap, QGuiApplication, QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
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


# --- WORKER THREAD VOOR BROWSER SCAN ---
class VaultScanWorker(QThread):
    progress_signal = Signal(str)
    finish_signal = Signal(list)
    error_signal = Signal(str)

    def __init__(
        self,
        search_roots: Optional[List[str]] = None,
        filter_securevault_only: bool = True,
    ):
        super().__init__()
        self.search_roots = search_roots
        self.filter_securevault_only = filter_securevault_only
        self.engine = VaultEngine()
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def run(self) -> None:
        try:
            results = self.engine.scan_vaults_on_system(
                search_roots=self.search_roots,
                filter_securevault_only=self.filter_securevault_only,
                progress_callback=lambda msg: self.progress_signal.emit(msg),
            )
            if not self._is_cancelled:
                self.finish_signal.emit(results)
        except Exception as e:
            if not self._is_cancelled:
                self.error_signal.emit(str(e))


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
            self.btn_toggle.setFixedSize(36, 36)
            self.btn_toggle.clicked.connect(self.toggle_password_visibility)
            row.addWidget(self.btn_toggle)

        if browse_func:
            btn_browse = QPushButton("Bladeren...")
            btn_browse.setToolTip("Selecteer via de bestandskiezer")
            btn_browse.setCursor(Qt.PointingHandCursor)
            btn_browse.setObjectName("browseBtn")
            btn_browse.setFixedWidth(100)
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
                "border: 1.5px solid #111827; background-color: #FFFFFF;"
            )
        elif status == "invalid":
            self.input.setStyleSheet(
                "border: 1.5px solid #6B7280; background-color: #F9FAFB;"
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
        # Scrollbare wrapper — content is altijd bereikbaar ongeacht venstergrootte

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

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
        # Voorkom dat langste optietekst de minimumbreedte van de widget dicteert
        self.combo_format.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.combo_format.setMinimumContentsLength(20)
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
        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.setLayout(outer)

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
                "QProgressBar#strengthBar::chunk { background-color: #9CA3AF; }"
            )
            self.lbl_strength.setText(f"Sterkte: {msg}")
            self.lbl_strength.setStyleSheet("color: #6B7280; font-size: 11px;")
        elif score < 75:
            self.strength_bar.setStyleSheet(
                "QProgressBar#strengthBar::chunk { background-color: #4B5563; }"
            )
            self.lbl_strength.setText(f"Sterkte: {msg}")
            self.lbl_strength.setStyleSheet("color: #374151; font-size: 11px;")
        else:
            self.strength_bar.setStyleSheet(
                "QProgressBar#strengthBar::chunk { background-color: #111827; }"
            )
            self.lbl_strength.setText(f"Sterkte: {msg}")
            self.lbl_strength.setStyleSheet("color: #111827; font-size: 11px; font-weight: 600;")

        if is_valid:
            self.inp_pass.set_border_status("valid")
        else:
            self.inp_pass.set_border_status("invalid")

        if pw_confirm:
            if pw == pw_confirm:
                self.inp_pass_confirm.set_border_status("valid")
                self.lbl_match.setText("✅ Wachtwoorden komen overeen")
                self.lbl_match.setStyleSheet("color: #111827; font-size: 11px; font-weight: 600;")
            else:
                self.inp_pass_confirm.set_border_status("invalid")
                self.lbl_match.setText("❌ Wachtwoorden komen niet overeen")
                self.lbl_match.setStyleSheet("color: #6B7280; font-size: 11px;")
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
        # Scrollbare wrapper — content is altijd bereikbaar ongeacht venstergrootte

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # RECENT VAULTS DROPDOWN
        lbl_recents = QLabel("🕒 RECENT GEOPENDE KLUIZEN")
        lbl_recents.setObjectName("inputLabel")
        layout.addWidget(lbl_recents)

        rec_row = QHBoxLayout()
        self.combo_recents = QComboBox()
        self.combo_recents.setObjectName("recentsCombo")
        self.combo_recents.setToolTip("Selecteer een recent gebruikte kluis uit het overzicht")
        # Voorkom dat bestandspaden de minimumbreedte dicteren
        self.combo_recents.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.combo_recents.setMinimumContentsLength(20)

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
        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.setLayout(outer)

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


# --- WIDGET TAB 3: KLUIS BROWSER ---
class VaultBrowserTab(QWidget):
    def __init__(self, parent_app: KluisApp):
        super().__init__()
        self.app = parent_app
        self.engine = VaultEngine()
        self.worker: Optional[VaultScanWorker] = None
        self.all_vaults: List[Dict[str, object]] = []
        self.custom_folder_path: Optional[str] = None
        self.setup_ui()

    def setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # 1. SCOPE & SCAN CONTROLS
        lbl_scope = QLabel("🔍 ZOEKLOCATIES & SCAN")
        lbl_scope.setObjectName("inputLabel")
        layout.addWidget(lbl_scope)

        scope_row = QHBoxLayout()
        scope_row.setSpacing(12)

        self.chk_home = QCheckBox("🏠 Homemap (~)")
        self.chk_home.setChecked(True)
        self.chk_home.setToolTip("Doorzoek je persoonlijke gebruikersmap en documenten")
        scope_row.addWidget(self.chk_home)

        self.chk_volumes = QCheckBox("💾 Externe Volumes (/Volumes)")
        self.chk_volumes.setChecked(os.path.exists("/Volumes"))
        self.chk_volumes.setToolTip("Doorzoek aangesloten externe schijven en USB-sticks")
        scope_row.addWidget(self.chk_volumes)

        self.btn_custom_folder = QPushButton("📁 Kies Map...")
        self.btn_custom_folder.setObjectName("browseBtn")
        self.btn_custom_folder.setToolTip("Voeg een specifieke extra zoekmap toe")
        self.btn_custom_folder.setCursor(Qt.PointingHandCursor)
        self.btn_custom_folder.clicked.connect(self.browse_custom_folder)
        scope_row.addWidget(self.btn_custom_folder)

        scope_row.addStretch()

        self.btn_scan = QPushButton("🔍 SCAN KLUIZEN")
        self.btn_scan.setObjectName("actionBtn")
        self.btn_scan.setCursor(Qt.PointingHandCursor)
        self.btn_scan.setToolTip("Zoek alle kluizen op je systeem via Spotlight en opslaglocaties")
        self.btn_scan.clicked.connect(self.start_scan)
        scope_row.addWidget(self.btn_scan)

        self.btn_cancel_scan = QPushButton("❌ ANNULEREN")
        self.btn_cancel_scan.setObjectName("cancelBtn")
        self.btn_cancel_scan.setCursor(Qt.PointingHandCursor)
        self.btn_cancel_scan.clicked.connect(self.cancel_scan)
        self.btn_cancel_scan.hide()
        scope_row.addWidget(self.btn_cancel_scan)

        layout.addLayout(scope_row)

        self.lbl_custom_folder = QLabel("")
        self.lbl_custom_folder.setObjectName("strengthLabel")
        self.lbl_custom_folder.hide()
        layout.addWidget(self.lbl_custom_folder)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # 2. FILTERBALK & RESULTATENTELLER
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        self.inp_filter = QLineEdit()
        self.inp_filter.setPlaceholderText("🔎 Filter op naam of locatie...")
        self.inp_filter.textChanged.connect(self.on_filter_changed)
        filter_row.addWidget(self.inp_filter, stretch=1)

        self.lbl_count = QLabel("Klik op 'Scan Kluizen' om te starten.")
        self.lbl_count.setObjectName("strengthLabel")
        filter_row.addWidget(self.lbl_count)

        layout.addLayout(filter_row)

        # 3. RESULTATENTABEL
        self.table = QTableWidget()
        self.table.setObjectName("browserTable")
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Kluis Naam", "Locatie", "Type", "Omvang", "🔑 Sleutelhanger", "Status"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.setMinimumHeight(240)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(0, 160)

        layout.addWidget(self.table)

        # 4. DIRECT ONTGRENDELEN SECTIE
        layout.addSpacing(6)
        lbl_unlock_sec = QLabel("🔓 DIRECT ONTGRENDELEN")
        lbl_unlock_sec.setObjectName("sectionTitle")
        layout.addWidget(lbl_unlock_sec)

        self.lbl_selected = QLabel("Selecteer een kluis uit de lijst om direct te openen.")
        self.lbl_selected.setObjectName("strengthLabel")
        layout.addWidget(self.lbl_selected)

        self.inp_pass = ModernInput(
            "WACHTWOORD",
            is_password=True,
            tooltip="Voer het wachtwoord van deze kluis in (of automatisch geladen via Keychain)",
        )
        layout.addWidget(self.inp_pass)

        self.chk_keychain = QCheckBox("🔑 Wachtwoord opslaan in macOS Sleutelhangertoegang (Keychain)")
        self.chk_keychain.setObjectName("keychainChk")
        layout.addWidget(self.chk_keychain)
        layout.addSpacing(4)

        btn_row = QHBoxLayout()
        self.btn_unlock = QPushButton("🔓 ONTGRENDELEN IN FINDER")
        self.btn_unlock.setObjectName("actionBtn")
        self.btn_unlock.setCursor(Qt.PointingHandCursor)
        self.btn_unlock.setEnabled(False)
        self.btn_unlock.clicked.connect(self.unlock_selected)
        btn_row.addWidget(self.btn_unlock)

        self.btn_lock = QPushButton("🔒 VERGRENDELEN (UITWERPEN)")
        self.btn_lock.setObjectName("cancelBtn")
        self.btn_lock.setCursor(Qt.PointingHandCursor)
        self.btn_lock.setEnabled(False)
        self.btn_lock.clicked.connect(self.lock_selected)
        btn_row.addWidget(self.btn_lock)

        self.btn_reveal = QPushButton("📁 TOON IN FINDER")
        self.btn_reveal.setObjectName("browseBtn")
        self.btn_reveal.setCursor(Qt.PointingHandCursor)
        self.btn_reveal.setEnabled(False)
        self.btn_reveal.clicked.connect(self.reveal_selected)
        btn_row.addWidget(self.btn_reveal)

        layout.addLayout(btn_row)
        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.setLayout(outer)

    def browse_custom_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Kies zoekmap voor kluizen")
        if d:
            self.custom_folder_path = d
            self.lbl_custom_folder.setText(f"📁 Extra zoekmap: {d}")
            self.lbl_custom_folder.show()

    def start_scan(self) -> None:
        self.app.reset_auto_lock_timer()
        roots: List[str] = []
        if self.chk_home.isChecked():
            roots.append(os.path.expanduser("~"))
        if self.chk_volumes.isChecked() and os.path.exists("/Volumes"):
            roots.append("/Volumes")
        if self.custom_folder_path and os.path.exists(self.custom_folder_path):
            roots.append(self.custom_folder_path)

        if not roots:
            QMessageBox.warning(self, "Geen Locaties", "Selecteer ten minste één zoeklocatie.")
            return

        self.btn_scan.setEnabled(False)
        self.btn_cancel_scan.show()
        self.progress_bar.show()
        self.lbl_count.setText("Kluizen zoeken op het systeem...")

        self.worker = VaultScanWorker(search_roots=roots)
        self.worker.progress_signal.connect(lambda msg: self.lbl_count.setText(msg))
        self.worker.finish_signal.connect(self.on_scan_finished)
        self.worker.error_signal.connect(self.on_scan_error)
        self.worker.start()

    def cancel_scan(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
        self.btn_scan.setEnabled(True)
        self.btn_cancel_scan.hide()
        self.progress_bar.hide()
        self.lbl_count.setText("Scan geannuleerd.")

    def on_scan_finished(self, results: List[Dict[str, object]]) -> None:
        self.btn_scan.setEnabled(True)
        self.btn_cancel_scan.hide()
        self.progress_bar.hide()
        self.all_vaults = results
        self.populate_table(results)
        self.lbl_count.setText(f"🎉 {len(results)} kluis(en) gevonden.")

    def on_scan_error(self, err: str) -> None:
        self.btn_scan.setEnabled(True)
        self.btn_cancel_scan.hide()
        self.progress_bar.hide()
        self.lbl_count.setText(f"❌ Fout tijdens scannen: {err}")

    def populate_table(self, vaults: List[Dict[str, object]]) -> None:
        self.table.setRowCount(len(vaults))
        for row, v in enumerate(vaults):
            name_item = QTableWidgetItem(str(v.get("name", "")))
            name_item.setData(Qt.ItemDataRole.UserRole, v)

            path_item = QTableWidgetItem(str(v.get("path", "")))
            path_item.setToolTip(str(v.get("path", "")))

            ext_item = QTableWidgetItem(str(v.get("ext", "")))
            ext_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            size_item = QTableWidgetItem(str(v.get("size", "")))
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            kc_item = QTableWidgetItem("🔑 Opgeslagen" if v.get("keychain") else "—")
            kc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            mounted = bool(v.get("mounted"))
            status_item = QTableWidgetItem("🟢 Geopend" if mounted else "🔒 Vergrendeld")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, path_item)
            self.table.setItem(row, 2, ext_item)
            self.table.setItem(row, 3, size_item)
            self.table.setItem(row, 4, kc_item)
            self.table.setItem(row, 5, status_item)

    def on_filter_changed(self, text: str) -> None:
        q = text.strip().lower()
        if not q:
            self.populate_table(self.all_vaults)
            self.lbl_count.setText(f"Totaal: {len(self.all_vaults)} kluis(en).")
            return
        filtered = [
            v for v in self.all_vaults
            if q in str(v.get("name", "")).lower() or q in str(v.get("path", "")).lower()
        ]
        self.populate_table(filtered)
        self.lbl_count.setText(f"Gefilterd: {len(filtered)} van {len(self.all_vaults)} kluis(en).")

    def get_selected_vault_data(self) -> Optional[Dict[str, object]]:
        current_row = self.table.currentRow()
        if current_row < 0:
            return None
        item = self.table.item(current_row, 0)
        if not item:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            return data
        return None

    def on_selection_changed(self) -> None:
        v = self.get_selected_vault_data()
        if not v:
            self.lbl_selected.setText("Selecteer een kluis uit de lijst om direct te openen.")
            self.btn_unlock.setEnabled(False)
            self.btn_lock.setEnabled(False)
            self.btn_reveal.setEnabled(False)
            return

        path = str(v.get("path", ""))
        name = str(v.get("name", ""))
        mounted = bool(v.get("mounted"))

        self.lbl_selected.setText(f"Geselecteerd: <b>{name}</b> ({path})")
        self.btn_reveal.setEnabled(True)
        self.btn_unlock.setEnabled(not mounted)
        self.btn_lock.setEnabled(mounted)

        kc_pw = VaultEngine.get_keychain_password(path)
        if kc_pw:
            self.inp_pass.setText(kc_pw)
            self.chk_keychain.setChecked(True)
        else:
            self.inp_pass.setText("")
            self.chk_keychain.setChecked(False)

    def on_item_double_clicked(self, item: QTableWidgetItem) -> None:
        v = self.get_selected_vault_data()
        if not v:
            return
        mounted = bool(v.get("mounted"))
        mount_point = str(v.get("mount_point", ""))
        if mounted and mount_point and os.path.exists(mount_point):
            subprocess.run(["open", mount_point])
        elif not mounted:
            if self.inp_pass.text():
                self.unlock_selected()
            else:
                self.inp_pass.input.setFocus()

    def unlock_selected(self) -> None:
        self.app.reset_auto_lock_timer()
        v = self.get_selected_vault_data()
        if not v:
            QMessageBox.warning(self, "Geen Selectie", "Selecteer eerst een kluis.")
            return

        path = str(v.get("path", ""))
        password = self.inp_pass.text()

        if not password:
            QMessageBox.warning(self, "Wachtwoord Vereist", "Voer het wachtwoord voor deze kluis in.")
            self.inp_pass.input.setFocus()
            return

        success, msg, mount_point = self.engine.mount_vault(path, password)
        if success:
            if self.chk_keychain.isChecked():
                self.engine.save_keychain_password(path, password)
            else:
                self.engine.delete_keychain_password(path)

            add_recent_vault(path)
            self.app.tab_manage.populate_recents()
            self.app.tab_manage.refresh_mounts()
            self.refresh_browser_status()

            if mount_point and os.path.exists(mount_point):
                subprocess.run(["open", mount_point])

            QMessageBox.information(
                self,
                "Kluis Geopend",
                f"🎉 Kluis '{v.get('name')}' is succesvol ontgrendeld!\n\nLocatie in Finder:\n{mount_point}",
            )
        else:
            QMessageBox.critical(self, "Ontgrendelen Mislukt", msg)

    def lock_selected(self) -> None:
        self.app.reset_auto_lock_timer()
        v = self.get_selected_vault_data()
        if not v:
            return
        path = str(v.get("path", ""))
        active = self.engine.get_active_mounts()
        mount_point = None
        for m, vp in active.items():
            if os.path.abspath(vp) == os.path.abspath(path):
                mount_point = m
                break

        if not mount_point:
            mount_point = str(v.get("mount_point", ""))

        if not mount_point or not os.path.exists(mount_point):
            QMessageBox.information(self, "Al Vergrendeld", "Deze kluis is niet meer gekoppeld.")
            self.refresh_browser_status()
            return

        success, msg = self.engine.unmount_vault(mount_point)
        if success:
            QMessageBox.information(self, "Vergrendeld", msg)
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

        self.app.tab_manage.refresh_mounts()
        self.refresh_browser_status()

    def reveal_selected(self) -> None:
        v = self.get_selected_vault_data()
        if v and os.path.exists(str(v.get("path", ""))):
            subprocess.run(["open", "-R", str(v.get("path"))])

    def refresh_browser_status(self) -> None:
        active_mounts = self.engine.get_active_mounts()
        mount_lookup = {os.path.abspath(vp): mp for mp, vp in active_mounts.items()}

        for v in self.all_vaults:
            p = os.path.abspath(str(v.get("path", "")))
            if p in mount_lookup:
                v["mounted"] = True
                v["mount_point"] = mount_lookup[p]
            else:
                v["mounted"] = False
                v["mount_point"] = ""

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                v = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(v, dict):
                    p = os.path.abspath(str(v.get("path", "")))
                    is_mounted = p in mount_lookup
                    v["mounted"] = is_mounted
                    v["mount_point"] = mount_lookup.get(p, "")
                    status_item = self.table.item(row, 5)
                    if status_item:
                        status_item.setText("🟢 Geopend" if is_mounted else "🔒 Vergrendeld")

        self.on_selection_changed()

    def show_context_menu(self, pos) -> None:
        v = self.get_selected_vault_data()
        if not v:
            return

        menu = QMenu(self)
        path = str(v.get("path", ""))
        mounted = bool(v.get("mounted"))

        if not mounted:
            act_unlock = QAction("🔓 Ontgrendelen in Finder", self)
            act_unlock.triggered.connect(self.unlock_selected)
            menu.addAction(act_unlock)
        else:
            act_open = QAction("📂 Openen in Finder", self)
            act_open.triggered.connect(lambda: subprocess.run(["open", str(v.get("mount_point") or path)]))
            menu.addAction(act_open)

            act_lock = QAction("🔒 Vergrendelen (Uitwerpen)", self)
            act_lock.triggered.connect(self.lock_selected)
            menu.addAction(act_lock)

        menu.addSeparator()

        act_reveal = QAction("📁 Toon bestand in Finder", self)
        act_reveal.triggered.connect(self.reveal_selected)
        menu.addAction(act_reveal)

        act_copy = QAction("📋 Kopieer kluispad", self)
        act_copy.triggered.connect(lambda: QGuiApplication.clipboard().setText(path))
        menu.addAction(act_copy)

        if v.get("keychain"):
            menu.addSeparator()
            act_del_kc = QAction("🗑️ Verwijder wachtwoord uit Keychain", self)
            act_del_kc.triggered.connect(lambda: self.delete_keychain_entry(path))
            menu.addAction(act_del_kc)

        menu.exec(self.table.mapToGlobal(pos))

    def delete_keychain_entry(self, path: str) -> None:
        self.engine.delete_keychain_password(path)
        QMessageBox.information(self, "Sleutelhanger", "Wachtwoord is verwijderd uit macOS Keychain.")
        self.refresh_browser_status()


# --- HOOFD APPLICATIE VENSTER ---
class KluisApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SecureVault Pro")
        self.resize(660, 840)
        self.setMinimumSize(560, 720)
        self.setObjectName("MainWindow")
        self.setAcceptDrops(True)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)

        self.path_logo = os.path.join(project_root, "assets", "logo.png")

        # Auto-Lock Timer Setup
        self.auto_lock_timer = QTimer(self)
        self.auto_lock_timer.timeout.connect(self.on_auto_lock_timeout)

        self.setup_ui()
        self.apply_styles()
        self.center_on_screen()

    def center_on_screen(self) -> None:
        """Centreer het venster netjes op het actieve scherm."""
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            geo = self.frameGeometry()
            geo.moveCenter(screen_geo.center())
            self.move(geo.topLeft())

    def setup_ui(self) -> None:
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(32, 20, 32, 20)
        main_layout.setSpacing(14)

        # HEADER
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        title_container = QVBoxLayout()
        title_container.setSpacing(2)
        title = QLabel("SecureVault")
        title.setObjectName("title")
        subtitle = QLabel("AES-256 Encrypted macOS Vault Manager")
        subtitle.setObjectName("subtitle")

        title_container.addWidget(title)
        title_container.addWidget(subtitle)

        # AUTO LOCK COMBO IN HEADER
        self.combo_autolock = QComboBox()
        self.combo_autolock.setObjectName("autolockCombo")
        self.combo_autolock.setMinimumWidth(170)
        self.combo_autolock.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
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
        btn_help.setFixedSize(36, 36)
        btn_help.clicked.connect(self.show_help)

        header_layout.addLayout(title_container)
        header_layout.addStretch()
        header_layout.addWidget(self.combo_autolock)
        header_layout.addSpacing(6)
        header_layout.addWidget(btn_help)

        main_layout.addLayout(header_layout)

        # TABS
        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        self.tabs.setElideMode(Qt.TextElideMode.ElideNone)
        if self.tabs.tabBar():
            self.tabs.tabBar().setElideMode(Qt.TextElideMode.ElideNone)
            self.tabs.tabBar().setExpanding(False)
        self.tabs.currentChanged.connect(lambda idx: self.reset_auto_lock_timer())

        self.tab_create = CreateVaultTab(self)
        self.tab_manage = ManageVaultTab(self)
        self.tab_browser = VaultBrowserTab(self)

        self.tabs.addTab(self.tab_create, "➕ Nieuwe Kluis")
        self.tabs.addTab(self.tab_manage, "🔓 Kluis Beheren")
        self.tabs.addTab(self.tab_browser, "🔍 Kluis Browser")

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
            if hasattr(self, "tab_browser"):
                self.tab_browser.refresh_browser_status()

    def apply_styles(self) -> None:
        self.setStyleSheet(stylesheet())

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