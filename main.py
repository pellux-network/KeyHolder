import os
import sys
import tkinter as tk

from app import KeyHolderApp
from input_backend import KeyboardController

ICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")


def main() -> None:
    if sys.platform != "win32":
        print(
            "KeyHolder requires Windows (it uses the Win32 SendInput API).",
            file=sys.stderr,
        )
        sys.exit(1)

    root = tk.Tk()
    root.title("KeyHolder")
    if os.path.exists(ICON_PATH):
        root.iconbitmap(ICON_PATH)
    controller = KeyboardController()
    KeyHolderApp(root, controller)
    root.mainloop()


if __name__ == "__main__":
    main()
