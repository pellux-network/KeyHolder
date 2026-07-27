import ctypes
import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app import KeyHolderApp
from input_backend import KeyboardController

# When frozen by PyInstaller (--onefile), files bundled via --add-data land
# in a temp extraction dir given by sys._MEIPASS, not next to the exe.
_BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
ICON_PATH = os.path.join(_BASE_DIR, "assets", "icon.ico")
APP_USER_MODEL_ID = "PelluxNetwork.KeyHolder"


def main() -> None:
    if sys.platform != "win32":
        print(
            "KeyHolder requires Windows (it uses the Win32 SendInput API).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Only affects taskbar grouping when run as `python main.py` (the
    # packaged exe already groups under its own distinct path). Harmless,
    # not load-bearing for the window icon itself — Qt handles that.
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass

    app = QApplication(sys.argv)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    controller = KeyboardController()
    window = KeyHolderApp(controller)
    window.setWindowIcon(app.windowIcon())
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
