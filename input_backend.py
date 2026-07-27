import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

PUL = ctypes.POINTER(ctypes.c_ulong)


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _InputUnion(ctypes.Union):
    # Must include mi/hi, not just ki: SendInput validates the cbSize argument
    # against its own (fixed) INPUT size, which is sized to fit the largest
    # union member (MOUSEINPUT). A union with only ki produces a struct that's
    # too small, so SendInput rejects every call with ERROR_INVALID_PARAMETER.
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _InputUnion)]


user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wintypes.UINT

# key_id -> (scan_code, is_extended)
SCANCODES: dict[str, tuple[int, bool]] = {
    "esc": (0x01, False),
    "1": (0x02, False), "2": (0x03, False), "3": (0x04, False), "4": (0x05, False),
    "5": (0x06, False), "6": (0x07, False), "7": (0x08, False), "8": (0x09, False),
    "9": (0x0A, False), "0": (0x0B, False),
    "minus": (0x0C, False), "equals": (0x0D, False), "backspace": (0x0E, False),
    "tab": (0x0F, False),
    "q": (0x10, False), "w": (0x11, False), "e": (0x12, False), "r": (0x13, False),
    "t": (0x14, False), "y": (0x15, False), "u": (0x16, False), "i": (0x17, False),
    "o": (0x18, False), "p": (0x19, False),
    "lbracket": (0x1A, False), "rbracket": (0x1B, False), "enter": (0x1C, False),
    "lctrl": (0x1D, False),
    "a": (0x1E, False), "s": (0x1F, False), "d": (0x20, False), "f": (0x21, False),
    "g": (0x22, False), "h": (0x23, False), "j": (0x24, False), "k": (0x25, False),
    "l": (0x26, False),
    "semicolon": (0x27, False), "quote": (0x28, False), "backtick": (0x29, False),
    "lshift": (0x2A, False),
    "backslash": (0x2B, False),
    "z": (0x2C, False), "x": (0x2D, False), "c": (0x2E, False), "v": (0x2F, False),
    "b": (0x30, False), "n": (0x31, False), "m": (0x32, False),
    "comma": (0x33, False), "period": (0x34, False), "slash": (0x35, False),
    "rshift": (0x36, False),
    "lalt": (0x38, False),
    "space": (0x39, False),
    "capslock": (0x3A, False),
    "f1": (0x3B, False), "f2": (0x3C, False), "f3": (0x3D, False), "f4": (0x3E, False),
    "f5": (0x3F, False), "f6": (0x40, False), "f7": (0x41, False), "f8": (0x42, False),
    "f9": (0x43, False), "f10": (0x44, False),
    "scrolllock": (0x46, False),
    "f11": (0x57, False), "f12": (0x58, False),
    # Extended keys (E0 prefix)
    "rctrl": (0x1D, True), "ralt": (0x38, True),
    "insert": (0x52, True), "delete": (0x53, True),
    "home": (0x47, True), "end": (0x4F, True),
    "pageup": (0x49, True), "pagedown": (0x51, True),
    "up": (0x48, True), "left": (0x4B, True), "right": (0x4D, True), "down": (0x50, True),
    "lwin": (0x5B, True), "rwin": (0x5C, True), "menu": (0x5D, True),
}


class KeyboardController:
    def __init__(self) -> None:
        self.held: set[str] = set()

    def key_down(self, key_id: str) -> bool:
        return self._send(key_id, key_up=False, on_success=self.held.add)

    def key_up(self, key_id: str) -> bool:
        return self._send(key_id, key_up=True, on_success=self.held.discard)

    def release_all(self) -> None:
        for key_id in list(self.held):
            self.key_up(key_id)

    def _send(self, key_id: str, key_up: bool, on_success) -> bool:
        if key_id not in SCANCODES:
            raise KeyError(f"Unknown key_id: {key_id!r}")
        scan_code, extended = SCANCODES[key_id]
        flags = KEYEVENTF_SCANCODE
        if extended:
            flags |= KEYEVENTF_EXTENDEDKEY
        if key_up:
            flags |= KEYEVENTF_KEYUP
        ki = KEYBDINPUT(wVk=0, wScan=scan_code, dwFlags=flags, time=0, dwExtraInfo=None)
        inp = INPUT(type=INPUT_KEYBOARD, union=_InputUnion(ki=ki))
        sent = user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(INPUT))
        success = sent == 1
        if success:
            on_success(key_id)
        return success
