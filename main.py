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

# X11 WM_CLASS is a Latin-1 string. A Chinese application name is shown as
# mojibake in the GNOME top bar, so the class stays ASCII and the visible
# name comes from the desktop file.
APP_ID = "systemmonitor"
APP_NAME = "资源监视器"


def _desktop_token(path: Path) -> str:
    text = str(path)
    if any(char in text for char in ' \t\n"\\'):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def _ensure_desktop_entry() -> None:
    """Install a desktop file so the top bar can show the Chinese name."""
    apps = Path.home() / ".local" / "share" / "applications"
    apps.mkdir(parents=True, exist_ok=True)
    path = apps / f"{APP_ID}.desktop"
    script = Path(__file__).resolve()
    python = Path(sys.executable).resolve()
    text = "\n".join(
        (
            "[Desktop Entry]",
            "Type=Application",
            "Version=1.0",
            f"Name={APP_NAME}",
            "Comment=CPU、内存与 GPU 资源监视器",
            f"Exec={_desktop_token(python)} {_desktop_token(script)}",
            "Icon=utilities-system-monitor",
            "Terminal=false",
            "Categories=System;Monitor;",
            f"StartupWMClass={APP_ID}",
            "",
        )
    )
    if path.is_file():
        try:
            if path.read_text(encoding="utf-8") == text:
                return
        except OSError:
            pass
    path.write_text(text, encoding="utf-8")


def main() -> None:
    _ensure_desktop_entry()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName(APP_NAME)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
