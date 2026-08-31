"""Monochrome black & white theme for SecureVault."""

EDITORIAL_STYLESHEET = """
QWidget#MainWindow {
    background-color: #FFFFFF;
}

QWidget {
    color: #111827;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

/* --- TABS --- */
QTabWidget::pane {
    border: 1px solid #E5E7EB;
    border-radius: 4px;
    background-color: #FFFFFF;
    top: -1px;
}

QTabBar {
    qproperty-elideMode: "ElideNone";
}

QTabBar::tab {
    background-color: #F9FAFB;
    border: 1px solid #E5E7EB;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 10px 24px;
    min-width: 150px;
    margin-right: 4px;
    color: #6B7280;
    font-weight: 600;
    font-size: 13px;
}

QTabBar::tab:selected {
    background-color: #111827;
    border-color: #111827;
    color: #FFFFFF;
}

QTabBar::tab:hover:!selected {
    background-color: #F3F4F6;
    color: #111827;
}

/* --- LABELS --- */
QLabel#title {
    font-size: 24px;
    font-weight: 700;
    color: #111827;
    letter-spacing: -0.5px;
}

QLabel#subtitle {
    font-size: 12px;
    color: #6B7280;
    font-weight: 400;
    letter-spacing: 0.2px;
}

QLabel#inputLabel {
    color: #374151;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    margin-bottom: 2px;
}

QLabel#sectionTitle {
    color: #111827;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin-top: 8px;
    margin-bottom: 4px;
}

QLabel#strengthLabel, QLabel#matchLabel {
    font-size: 11px;
    color: #6B7280;
}

/* --- INPUTS & COMBOBOX --- */
QLineEdit, QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    padding: 6px 12px;
    border-radius: 4px;
    color: #111827;
    font-size: 13px;
    min-height: 36px;
    selection-background-color: #111827;
    selection-color: #FFFFFF;
}

QLineEdit:focus, QComboBox:focus {
    border: 1.5px solid #111827;
    background-color: #FFFFFF;
}

QLineEdit:disabled, QComboBox:disabled {
    background-color: #F9FAFB;
    border-color: #E5E7EB;
    color: #9CA3AF;
}

QComboBox {
    padding-right: 24px;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #E5E7EB;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    color: #111827;
    selection-background-color: #111827;
    selection-color: #FFFFFF;
    padding: 4px;
}

/* --- BUTTONS --- */
QPushButton#browseBtn {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    padding: 6px 14px;
    border-radius: 4px;
    color: #111827;
    font-weight: 600;
    font-size: 12px;
    min-height: 36px;
}

QPushButton#browseBtn:hover {
    background-color: #F3F4F6;
    border-color: #9CA3AF;
}

QPushButton#browseBtn:pressed {
    background-color: #E5E7EB;
}

QToolButton#togglePwBtn {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    color: #111827;
    min-height: 36px;
    min-width: 36px;
    font-size: 14px;
}

QToolButton#togglePwBtn:hover {
    background-color: #F3F4F6;
    border-color: #9CA3AF;
}

QToolButton#helpBtn {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    color: #111827;
    font-weight: 700;
    font-size: 12px;
    min-height: 32px;
    min-width: 32px;
}

QToolButton#helpBtn:hover {
    background-color: #F3F4F6;
    border-color: #111827;
}

QPushButton#actionBtn {
    background-color: #111827;
    color: #FFFFFF;
    font-weight: 700;
    padding: 10px 18px;
    font-size: 13px;
    border-radius: 4px;
    border: 1px solid #111827;
    min-height: 40px;
}

QPushButton#actionBtn:hover {
    background-color: #1F2937;
    border-color: #1F2937;
}

QPushButton#actionBtn:pressed {
    background-color: #000000;
    border-color: #000000;
}

QPushButton#actionBtn:disabled {
    background-color: #E5E7EB;
    border-color: #E5E7EB;
    color: #9CA3AF;
}

QPushButton#cancelBtn {
    background-color: #374151;
    color: #FFFFFF;
    font-weight: 700;
    padding: 10px 18px;
    font-size: 13px;
    border-radius: 4px;
    border: 1px solid #374151;
    min-height: 40px;
}

QPushButton#cancelBtn:hover {
    background-color: #111827;
    border-color: #111827;
}

/* --- LISTS & MENUS --- */
QListWidget#mountsList {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    padding: 6px;
    color: #111827;
    font-size: 12px;
    min-height: 120px;
}

QListWidget#mountsList::item {
    padding: 8px 10px;
    border-radius: 3px;
    margin-bottom: 2px;
}

QListWidget#mountsList::item:selected {
    background-color: #F3F4F6;
    color: #111827;
    font-weight: 600;
}

QMenu {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    color: #111827;
    padding: 4px;
}

QMenu::item {
    padding: 6px 20px;
    border-radius: 2px;
}

QMenu::item:selected {
    background-color: #111827;
    color: #FFFFFF;
}

/* --- LOG CONSOLE --- */
QTextEdit {
    background-color: #111827;
    border: 1px solid #111827;
    color: #F9FAFB;
    font-family: "SF Mono", "Menlo", "Courier New", monospace;
    font-size: 12px;
    line-height: 1.4;
    border-radius: 4px;
    padding: 8px;
    min-height: 85px;
}

/* --- PROGRESS BAR --- */
QProgressBar {
    background-color: #E5E7EB;
    border-radius: 2px;
    height: 4px;
    min-height: 4px;
    max-height: 4px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #111827;
    border-radius: 2px;
}

/* --- CHECKBOX --- */
QCheckBox {
    color: #374151;
    font-size: 12px;
    spacing: 8px;
}

QCheckBox#keychainChk, QCheckBox#overwriteChk {
    margin-top: 4px;
    margin-bottom: 4px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #D1D5DB;
    border-radius: 3px;
    background-color: #FFFFFF;
}

QCheckBox::indicator:hover {
    border-color: #111827;
}

QCheckBox::indicator:checked {
    background-color: #111827;
    border-color: #111827;
    image: none;
}

/* --- DIALOGS (QMessageBox) --- */
QMessageBox {
    background-color: #FFFFFF;
}

QMessageBox QLabel {
    color: #111827;
    font-size: 13px;
}

QMessageBox QPushButton {
    background-color: #111827;
    color: #FFFFFF;
    padding: 8px 18px;
    border-radius: 4px;
    border: 1px solid #111827;
    font-weight: 600;
    font-size: 12px;
    min-width: 80px;
    min-height: 32px;
}

QMessageBox QPushButton:hover {
    background-color: #1F2937;
    border-color: #1F2937;
}

/* --- SCROLLBARS --- */
QScrollBar:vertical {
    border: none;
    background-color: transparent;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #D1D5DB;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #9CA3AF;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

WINDOW_BACKGROUND = "#FFFFFF"
PAPER_BACKGROUND = "#FFFFFF"
INK = "#111827"
ACCENT = "#111827"
MUTED = "#6B7280"
BORDER = "#E5E7EB"


def stylesheet() -> str:
    return EDITORIAL_STYLESHEET


__all__ = [
    "stylesheet",
    "EDITORIAL_STYLESHEET",
    "WINDOW_BACKGROUND",
    "PAPER_BACKGROUND",
    "INK",
    "ACCENT",
    "MUTED",
    "BORDER",
]

