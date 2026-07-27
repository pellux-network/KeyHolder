import ctypes
import os
import sys
import tkinter as tk

from app import KeyHolderApp
from input_backend import KeyboardController

ICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
APP_USER_MODEL_ID = "PelluxNetwork.KeyHolder"


def main() -> None:
    if sys.platform != "win32":
        print(
            "KeyHolder requires Windows (it uses the Win32 SendInput API).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Without this, Windows groups the taskbar button under python.exe's own
    # icon (since that's the actual running process) instead of ours, even
    # though iconbitmap() correctly sets the title bar icon.
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass

    root = tk.Tk()
    root.title("KeyHolder")
    if os.path.exists(ICON_PATH):
        root.iconbitmap(ICON_PATH)
    controller = KeyboardController()
    KeyHolderApp(root, controller)
    root.mainloop()


if __name__ == "__main__":
    main()
