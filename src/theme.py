"""Monochrome editorial Qt theme for SecureVault."""

EDITORIAL_STYLESHEET = """
QWidget#MainWindow { background: #F4F1E9; }
QWidget { color: #19202C; font-family: ".AppleSystemUIFont", "Helvetica Neue", sans-serif; }
QTabWidget::pane { border: 1px solid #C9C4B8; border-radius: 2px; background: #FAF8F2; }
QTabBar::tab { background: #E8E4DA; border: 1px solid #C9C4B8; padding: 10px 18px; color: #687080; font-weight: 600; }
QTabBar::tab:selected { background: #19202C; color: #F4F1E9; border-bottom-color: #19202C; }
QTabBar::tab:hover { color: #19202C; }
QMessageBox { background: #F4F1E9; }
QMessageBox QLabel { color: #19202C; font-size: 13px; }
QMessageBox QPushButton { background: #19202C; color: #F4F1E9; padding: 7px 18px; border-radius: 2px; border: 1px solid #19202C; }
QMessageBox QPushButton:hover { background: #F2673F; border-color: #F2673F; }
QCheckBox#keychainChk { color: #4D5665; font-size: 11px; margin-top: 4px; }
QCheckBox#keychainChk::indicator { width: 14px; height: 14px; }
QLabel#title { font-size: 22px; font-weight: 600; color: #19202C; }
QLabel#subtitle { font-size: 11px; color: #687080; letter-spacing: 0.5px; }
QLabel#inputLabel { color: #687080; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
QLabel#sectionTitle { color: #F2673F; font-size: 12px; font-weight: 700; letter-spacing: 0.5px; margin-top: 6px; }
QLabel#strengthLabel, QLabel#matchLabel { font-size: 11px; color: #687080; }
QLineEdit, QComboBox { background: #FAF8F2; border: 1px solid #C9C4B8; padding: 9px; border-radius: 2px; color: #19202C; font-size: 13px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #F2673F; }
QComboBox QAbstractItemView { background: #FAF8F2; color: #19202C; selection-background-color: #E8E4DA; }
QPushButton#browseBtn { background: #E8E4DA; border: 1px solid #C9C4B8; padding: 9px 14px; border-radius: 2px; color: #19202C; font-weight: 600; }
QPushButton#browseBtn:hover { background: #D9D4C9; }
QToolButton#togglePwBtn, QToolButton#helpBtn { background: #E8E4DA; border: 1px solid #C9C4B8; border-radius: 2px; color: #19202C; }
QToolButton#togglePwBtn:hover, QToolButton#helpBtn:hover { background: #D9D4C9; }
QPushButton#actionBtn { background: #19202C; color: #F4F1E9; font-weight: 700; padding: 12px; font-size: 13px; border-radius: 2px; border: none; }
QPushButton#actionBtn:hover { background: #F2673F; }
QPushButton#actionBtn:disabled { background: #C9C4B8; color: #687080; }
QPushButton#cancelBtn { background: #F2673F; color: #F4F1E9; font-weight: 700; padding: 12px; font-size: 13px; border-radius: 2px; border: none; }
QPushButton#cancelBtn:hover { background: #19202C; }
QListWidget#mountsList { background: #FAF8F2; border: 1px solid #C9C4B8; border-radius: 2px; padding: 6px; color: #19202C; font-size: 12px; }
QListWidget#mountsList::item:selected { background: #E8E4DA; color: #19202C; }
QMenu { background: #FAF8F2; border: 1px solid #C9C4B8; color: #19202C; }
QMenu::item:selected { background: #E8E4DA; color: #19202C; }
QTextEdit { background: #19202C; border: 1px solid #19202C; color: #F4F1E9; font-family: "Menlo", "Courier New", monospace; font-size: 11px; border-radius: 2px; }
QProgressBar { background: #E8E4DA; border-radius: 2px; height: 6px; }
QProgressBar::chunk { background: #F2673F; border-radius: 2px; }
"""

WINDOW_BACKGROUND = "#F4F1E9"
PAPER_BACKGROUND = "#FAF8F2"
INK = "#19202C"
ACCENT = "#F2673F"
MUTED = "#687080"
BORDER = "#C9C4B8"


def stylesheet() -> str:
    return EDITORIAL_STYLESHEET


__all__ = ["stylesheet", "EDITORIAL_STYLESHEET"]
