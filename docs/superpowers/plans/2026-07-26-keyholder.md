# KeyHolder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows Tkinter app where clicking a visual key toggles a real OS-level held keypress via `SendInput`, with a panic hotkey and guaranteed release-on-exit.

**Architecture:** Four stdlib-only modules — `input_backend.py` (ctypes `SendInput` wrapper + scan code table), `keyboard_layout.py` (layout data), `app.py` (Tkinter UI), `main.py` (entry point). No git commits (project has no git repo; skip version control steps).

**Tech Stack:** Python 3.14, `tkinter` (stdlib), `ctypes` (stdlib), `pytest` for `input_backend` unit tests.

---

## Task 1: Project scaffolding

**Files:**
- Create: `main.py` (empty stub)
- Create: `app.py` (empty stub)
- Create: `keyboard_layout.py` (empty stub)
- Create: `input_backend.py` (empty stub)
- Create: `conftest.py`
- Create: `tests/__init__.py` (empty)
- Create: `tests/test_input_backend.py` (empty stub)
- Create: `tests/test_keyboard_layout.py` (empty stub)

- [ ] **Step 1: Create the directory structure and empty files**

```bash
cd "C:\Users\Pellux\Coding\KeyHolder"
touch main.py app.py keyboard_layout.py input_backend.py conftest.py
mkdir -p tests
touch tests/__init__.py tests/test_input_backend.py tests/test_keyboard_layout.py
```

- [ ] **Step 2: Write `conftest.py` so tests can import root-level modules**

```python
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
```

- [ ] **Step 3: Install pytest**

```bash
pip install pytest
```

Expected: pytest installs successfully (check with `pip show pytest`).

---

## Task 2: Input backend — scan code table and structures

**Files:**
- Modify: `input_backend.py`
- Test: `tests/test_input_backend.py`

- [ ] **Step 1: Write the failing test for a basic key-down call**

```python
# tests/test_input_backend.py
from unittest.mock import patch

import input_backend as ib


def _capture_send_input():
    """Returns (fake_send_input, captured) — captured fills in during the call."""
    captured = {}

    def fake_send_input(n_inputs, inp_ptr, size):
        captured["scan"] = inp_ptr[0].union.ki.wScan
        captured["flags"] = inp_ptr[0].union.ki.dwFlags
        return 1

    return fake_send_input, captured


def test_key_down_sends_correct_scancode_and_sets_scancode_flag():
    controller = ib.KeyboardController()
    fake_send_input, captured = _capture_send_input()

    with patch.object(ib.user32, "SendInput", side_effect=fake_send_input):
        result = controller.key_down("a")

    assert result is True
    assert captured["scan"] == 0x1E
    assert captured["flags"] & ib.KEYEVENTF_SCANCODE
    assert not captured["flags"] & ib.KEYEVENTF_KEYUP
    assert "a" in controller.held
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_input_backend.py::test_key_down_sends_correct_scancode_and_sets_scancode_flag -v
```

Expected: FAIL with `ModuleNotFoundError` or `AttributeError` (no `input_backend` contents yet).

- [ ] **Step 3: Implement the scan code table, ctypes structures, and `KeyboardController.key_down`**

```python
# input_backend.py
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


class _InputUnion(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_input_backend.py::test_key_down_sends_correct_scancode_and_sets_scancode_flag -v
```

Expected: PASS

---

## Task 3: Input backend — key_up, extended keys, release_all, failure path

**Files:**
- Modify: `tests/test_input_backend.py` (add tests; `input_backend.py` already supports these via Task 2's `_send`)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_input_backend.py (append)

def test_key_up_sets_keyup_flag_and_removes_from_held():
    controller = ib.KeyboardController()
    controller.held.add("a")
    fake_send_input, captured = _capture_send_input()

    with patch.object(ib.user32, "SendInput", side_effect=fake_send_input):
        result = controller.key_up("a")

    assert result is True
    assert captured["flags"] & ib.KEYEVENTF_KEYUP
    assert "a" not in controller.held


def test_extended_key_sets_extended_flag():
    controller = ib.KeyboardController()
    fake_send_input, captured = _capture_send_input()

    with patch.object(ib.user32, "SendInput", side_effect=fake_send_input):
        controller.key_down("right")

    assert captured["scan"] == 0x4D
    assert captured["flags"] & ib.KEYEVENTF_EXTENDEDKEY


def test_release_all_releases_every_held_key():
    controller = ib.KeyboardController()
    with patch.object(ib.user32, "SendInput", return_value=1):
        controller.key_down("w")
        controller.key_down("a")
        controller.key_down("s")
        controller.key_down("d")

    with patch.object(ib.user32, "SendInput", return_value=1) as mock_send:
        controller.release_all()

    assert mock_send.call_count == 4
    assert controller.held == set()


def test_release_all_on_empty_state_is_a_no_op():
    controller = ib.KeyboardController()
    with patch.object(ib.user32, "SendInput", return_value=1) as mock_send:
        controller.release_all()

    mock_send.assert_not_called()


def test_key_down_failure_does_not_mark_key_as_held():
    controller = ib.KeyboardController()
    with patch.object(ib.user32, "SendInput", return_value=0):
        result = controller.key_down("a")

    assert result is False
    assert "a" not in controller.held


def test_unknown_key_id_raises_keyerror():
    controller = ib.KeyboardController()
    try:
        controller.key_down("not_a_real_key")
        assert False, "expected KeyError"
    except KeyError:
        pass
```

- [ ] **Step 2: Run tests to verify they fail or pass appropriately**

```bash
pytest tests/test_input_backend.py -v
```

Expected: All tests PASS, since `_send`/`key_down`/`key_up`/`release_all` were already implemented generically in Task 2. If any fail, fix `input_backend.py` until green (this task is a verification/coverage pass on Task 2's implementation, not new production code).

- [ ] **Step 3: Run the full test file to confirm everything is green**

```bash
pytest tests/test_input_backend.py -v
```

Expected: PASS (7 tests total)

---

## Task 4: Keyboard layout data

**Files:**
- Modify: `keyboard_layout.py`
- Test: `tests/test_keyboard_layout.py`

- [ ] **Step 1: Write the failing consistency test**

```python
# tests/test_keyboard_layout.py
import input_backend as ib
import keyboard_layout as kl


def test_every_key_id_in_layout_has_a_scancode():
    missing = []
    for row in kl.ROWS + kl.NAV_ROWS:
        for _label, key_id, _width in row:
            if key_id not in ib.SCANCODES:
                missing.append(key_id)
    assert missing == []


def test_layout_has_no_duplicate_key_ids():
    seen = []
    for row in kl.ROWS + kl.NAV_ROWS:
        for _label, key_id, _width in row:
            seen.append(key_id)
    assert len(seen) == len(set(seen)), "duplicate key_id in layout"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_keyboard_layout.py -v
```

Expected: FAIL (`ROWS`/`NAV_ROWS` don't exist yet)

- [ ] **Step 3: Implement the layout data**

Each row entry is `(display_label, key_id, relative_width)`. `relative_width` is in units of one standard keycap (used later to size Tkinter buttons).

```python
# keyboard_layout.py

ROWS = [
    [
        ("Esc", "esc", 1),
        ("F1", "f1", 1), ("F2", "f2", 1), ("F3", "f3", 1), ("F4", "f4", 1),
        ("F5", "f5", 1), ("F6", "f6", 1), ("F7", "f7", 1), ("F8", "f8", 1),
        ("F9", "f9", 1), ("F10", "f10", 1), ("F11", "f11", 1), ("F12", "f12", 1),
    ],
    [
        ("`", "backtick", 1),
        ("1", "1", 1), ("2", "2", 1), ("3", "3", 1), ("4", "4", 1), ("5", "5", 1),
        ("6", "6", 1), ("7", "7", 1), ("8", "8", 1), ("9", "9", 1), ("0", "0", 1),
        ("-", "minus", 1), ("=", "equals", 1), ("Backspace", "backspace", 2),
    ],
    [
        ("Tab", "tab", 1.5),
        ("Q", "q", 1), ("W", "w", 1), ("E", "e", 1), ("R", "r", 1), ("T", "t", 1),
        ("Y", "y", 1), ("U", "u", 1), ("I", "i", 1), ("O", "o", 1), ("P", "p", 1),
        ("[", "lbracket", 1), ("]", "rbracket", 1), ("\\", "backslash", 1.5),
    ],
    [
        ("Caps", "capslock", 1.75),
        ("A", "a", 1), ("S", "s", 1), ("D", "d", 1), ("F", "f", 1), ("G", "g", 1),
        ("H", "h", 1), ("J", "j", 1), ("K", "k", 1), ("L", "l", 1),
        (";", "semicolon", 1), ("'", "quote", 1), ("Enter", "enter", 2.25),
    ],
    [
        ("Shift", "lshift", 2.25),
        ("Z", "z", 1), ("X", "x", 1), ("C", "c", 1), ("V", "v", 1), ("B", "b", 1),
        ("N", "n", 1), ("M", "m", 1),
        (",", "comma", 1), (".", "period", 1), ("/", "slash", 1),
        ("Shift", "rshift", 2.75),
    ],
    [
        ("Ctrl", "lctrl", 1.25), ("Win", "lwin", 1.25), ("Alt", "lalt", 1.25),
        ("Space", "space", 6.25),
        ("Alt", "ralt", 1.25), ("Win", "rwin", 1.25), ("Menu", "menu", 1.25),
        ("Ctrl", "rctrl", 1.25),
    ],
]

NAV_ROWS = [
    [("Ins", "insert", 1), ("Home", "home", 1), ("PgUp", "pageup", 1)],
    [("Del", "delete", 1), ("End", "end", 1), ("PgDn", "pagedown", 1)],
    [("", "_gap1", 1)],
    [("Up", "up", 1)],
    [("Left", "left", 1), ("Down", "down", 1), ("Right", "right", 1)],
]
```

Wait — `_gap1` is not a real key and would fail the consistency test. Remove the blank spacer row instead of faking a key:

```python
NAV_ROWS = [
    [("Ins", "insert", 1), ("Home", "home", 1), ("PgUp", "pageup", 1)],
    [("Del", "delete", 1), ("End", "end", 1), ("PgDn", "pagedown", 1)],
    [("Up", "up", 1)],
    [("Left", "left", 1), ("Down", "down", 1), ("Right", "right", 1)],
]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_keyboard_layout.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 5: Run the full test suite**

```bash
pytest -v
```

Expected: All 9 tests PASS (7 from `test_input_backend.py`, 2 from `test_keyboard_layout.py`)

---

## Task 5: Tkinter UI

**Files:**
- Modify: `app.py`

No automated tests for this task — per the design spec, GUI behavior is verified manually in Task 7. `app.py` only consumes `KeyboardController` and the layout data already covered by Tasks 2–4.

- [ ] **Step 1: Implement `KeyButton` and `KeyHolderApp`**

```python
# app.py
import atexit
import ctypes
import tkinter as tk

import keyboard_layout as kl

VK_PAUSE = 0x13
COLOR_RELEASED = "#dddddd"
COLOR_HELD = "#4caf50"
BASE_WIDTH = 4


class KeyButton:
    def __init__(self, parent, label, key_id, controller, status_var, width):
        self.key_id = key_id
        self.controller = controller
        self.status_var = status_var
        self.held = False
        self.button = tk.Button(
            parent,
            text=label,
            width=max(1, int(width * BASE_WIDTH)),
            bg=COLOR_RELEASED,
            command=self.toggle,
        )

    def toggle(self) -> None:
        if self.held:
            ok = self.controller.key_up(self.key_id)
            if ok:
                self.held = False
                self.button.config(bg=COLOR_RELEASED)
        else:
            ok = self.controller.key_down(self.key_id)
            if ok:
                self.held = True
                self.button.config(bg=COLOR_HELD)
        if not ok:
            self.status_var.set(f"Failed to toggle {self.button['text']}")

    def reset(self) -> None:
        self.held = False
        self.button.config(bg=COLOR_RELEASED)


class KeyHolderApp:
    def __init__(self, root: tk.Tk, controller):
        self.root = root
        self.controller = controller
        self.status_var = tk.StringVar(value="Ready")
        self.key_buttons: list[KeyButton] = []
        self._panic_prev_pressed = False

        self._build_ui()
        self._register_exit_handlers()
        self._poll_panic_key()

    def _build_ui(self) -> None:
        main_frame = tk.Frame(self.root)
        main_frame.pack(padx=8, pady=8)

        keyboard_frame = tk.Frame(main_frame)
        keyboard_frame.pack(side=tk.LEFT)
        for row in kl.ROWS:
            self._build_row(keyboard_frame, row)

        nav_frame = tk.Frame(main_frame)
        nav_frame.pack(side=tk.LEFT, padx=(16, 0))
        for row in kl.NAV_ROWS:
            self._build_row(nav_frame, row)

        controls_frame = tk.Frame(self.root)
        controls_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        tk.Button(controls_frame, text="Release All", command=self.release_all).pack(side=tk.LEFT)
        tk.Label(controls_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(controls_frame, text="Panic key: Pause/Break").pack(side=tk.RIGHT)

    def _build_row(self, parent: tk.Frame, row) -> None:
        row_frame = tk.Frame(parent)
        row_frame.pack(anchor=tk.W)
        for label, key_id, width in row:
            kb = KeyButton(row_frame, label, key_id, self.controller, self.status_var, width)
            kb.button.pack(side=tk.LEFT, padx=1, pady=1)
            self.key_buttons.append(kb)

    def release_all(self) -> None:
        self.controller.release_all()
        for kb in self.key_buttons:
            kb.reset()
        self.status_var.set("All keys released")

    def _register_exit_handlers(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        atexit.register(self.controller.release_all)

    def _on_close(self) -> None:
        self.controller.release_all()
        self.root.destroy()

    def _poll_panic_key(self) -> None:
        try:
            state = ctypes.windll.user32.GetAsyncKeyState(VK_PAUSE)
            pressed = bool(state & 0x8000)
            if pressed and not self._panic_prev_pressed:
                self.release_all()
            self._panic_prev_pressed = pressed
        except Exception:
            pass
        self.root.after(50, self._poll_panic_key)
```

- [ ] **Step 2: Verify the module imports cleanly**

```bash
python -c "import app; print('ok')"
```

Expected: `ok` (no syntax/import errors)

---

## Task 6: Entry point

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Implement `main.py`**

```python
# main.py
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
```

- [ ] **Step 2: Run the full automated test suite one more time**

```bash
pytest -v
```

Expected: All 9 tests PASS

- [ ] **Step 3: Launch the app**

```bash
python main.py
```

Expected: A window titled "KeyHolder" opens showing the full keyboard layout plus a nav cluster, a "Release All" button, and a status label reading "Ready".

---

## Task 7: Manual verification

**Files:** none (manual testing only)

- [ ] **Step 1: Verify a basic held key works**

Open Notepad. In KeyHolder, click the "A" key (should turn green). Click into Notepad — Windows' own key-repeat should start inserting "a" characters (confirms the OS sees a genuine held key, not a one-shot press). Click "A" again in KeyHolder (turns gray) — the repeated input stops.

- [ ] **Step 2: Verify multiple simultaneous held keys**

Click "W" and "D" together (both green). This is the standard test for games reading multiple simultaneous key states (e.g. diagonal movement). Click "Release All" — both turn gray and `controller.held` is empty (observable via the status label reading "All keys released").

- [ ] **Step 3: Verify the panic hotkey works while unfocused**

With one or more keys toggled held in KeyHolder, click into a different window (e.g. Notepad) so KeyHolder loses focus. Press Pause/Break. Within ~50ms, switch back to KeyHolder and confirm all keys reset to gray and the status label reads "All keys released".

- [ ] **Step 4: Verify exit safety**

Toggle a key on, then close the KeyHolder window via the X button. Reopen KeyHolder — confirm no key was left stuck (test by holding nothing and checking Notepad doesn't keep receiving input from the previous session).

---

## Task 8: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write a short usage README**

```markdown
# KeyHolder

Toggle keyboard keys on/off as if physically held down, via a Tkinter UI.
Uses the Win32 `SendInput` API with hardware scan codes — Windows only.

## Run

    python main.py

## Usage

- Click any key to toggle it held (green) / released (gray).
- "Release All" releases every held key immediately.
- **Panic key: Pause/Break** — releases all held keys instantly, even if
  KeyHolder isn't the focused window.
- Closing the window automatically releases all held keys.

## Requirements

- Windows
- Python 3.10+ (stdlib only — `tkinter` and `ctypes`)
- `pytest` for running the test suite (`pip install pytest`, then `pytest -v`)

## Known limitations

- Anti-cheat systems and games that filter raw/low-level input may ignore
  all synthetic input regardless of technique.
- Using synthetic input in multiplayer games likely violates that game's
  terms of service — that's on you.
- If the target application runs elevated (as Administrator), Windows UIPI
  may block input from a non-elevated KeyHolder; run KeyHolder as
  Administrator too in that case.
```

- [ ] **Step 2: Confirm the final file layout**

```bash
ls "C:\Users\Pellux\Coding\KeyHolder"
```

Expected: `main.py`, `app.py`, `keyboard_layout.py`, `input_backend.py`, `conftest.py`, `README.md`, `tests/`, `docs/`

---

## Plan Self-Review Notes

- **Spec coverage:** platform check (Task 6), zero external deps for input (Task 2), full TKL layout minus numpad (Task 4), toggle-to-hold via SendInput+scancodes (Task 2/5), panic hotkey via GetAsyncKeyState polling (Task 5), auto-release on close/atexit (Task 5), failure handling with reverted state + status message (Task 5), unit tests for input_backend (Task 2/3), manual test plan (Task 7), known limitations documented (Task 8 README) — all covered.
- **Fixed during drafting:** Task 4 initially included a fake `_gap1` spacer key_id in `NAV_ROWS`, which would have failed its own consistency test — replaced with a layout that has no fake keys instead of special-casing the test.
- **No git steps:** omitted per user's choice to skip version control for this project.
