import sys
import tkinter as tk

from app import KeyHolderApp
from input_backend import KeyboardController


def main() -> None:
    if sys.platform != "win32":
        print(
            "KeyHolder requires Windows (it uses the Win32 SendInput API).",
            file=sys.stderr,
        )
        sys.exit(1)

    root = tk.Tk()
    root.title("KeyHolder")
    controller = KeyboardController()
    KeyHolderApp(root, controller)
    root.mainloop()


if __name__ == "__main__":
    main()
