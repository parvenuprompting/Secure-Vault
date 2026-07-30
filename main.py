from __future__ import annotations

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from src.ui import KluisApp

# Versiebeheer op 1 centrale plek
VERSION = "2.0.0"


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("SecureVault")
    app.setApplicationVersion(VERSION)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "assets", "logo.png")

    if os.path.exists(icon_path):
        icon = QIcon(icon_path)
        app.setWindowIcon(icon)

    window = KluisApp()
    window.setWindowTitle(f"SecureVault v{VERSION}")
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()