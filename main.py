"""Launch the resource monitor."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("PYQTGRAPH_QT_LIB", "PySide6")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from monitor.window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("资源监视器")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
