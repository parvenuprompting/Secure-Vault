import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from src.ui import KluisApp

# Versie beheer op 1 centrale plek
VERSION = "2.0.0"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Pad naar assets/logo.png
    base_dir = os.path.dirname(__file__)
    icon_path = os.path.join(base_dir, 'assets', 'logo.png')
    
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        # Voor Mac Dock icon fix
        try:
            from ctypes import c_void_p, cdll
            # Dit forceert het icoon ook in de Dock tijdens dev
            pass 
        except:
            pass

    window = KluisApp()
    window.setWindowTitle(f"SecureVault v{VERSION}")
    window.show()
    
    sys.exit(app.exec())