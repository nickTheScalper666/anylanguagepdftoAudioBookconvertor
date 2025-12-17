from __future__ import annotations

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(980, 720)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
