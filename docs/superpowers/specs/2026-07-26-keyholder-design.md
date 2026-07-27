# KeyHolder — Design Spec

Date: 2026-07-26

## Purpose

A Windows desktop app with a visual keyboard interface where clicking a key toggles it between "released" and "held," simulating a real held-down keypress at the OS level. Primary use case: games / anti-AFK, where synthetic input must be realistic enough that games reading raw/DirectInput key state treat it as a genuine held key.

## Platform & Constraints

- Windows only (`sys.platform == "win32"`), since key simulation uses the Win32 `SendInput` API.
- Zero external dependencies — GUI via `tkinter` (stdlib), input simulation via `ctypes` (stdlib) calling `SendInput` directly with hardware scan codes.
- Python 3.14 (as installed in the dev environment).

## Architecture

```
keyholder/
  main.py              entry point: platform check, wiring, exit cleanup
  app.py                Tkinter UI: keyboard grid, toggle buttons, panic-key polling
  keyboard_layout.py    layout data: rows of (label, key_id, width)
  input_backend.py      SendInput wrapper + scan code table
tests/
  test_input_backend.py
```

### `input_backend.py`

- `SCANCODES: dict[str, tuple[int, bool]]` — maps each `key_id` to `(scan_code, is_extended)` using the Windows Set-1 hardware scan code table. Extended keys (arrows, right ctrl/alt, ins/del/home/end/pgup/pgdn) are flagged so `KEYEVENTF_EXTENDEDKEY` is set.
- `KeyboardController`:
  - `key_down(key_id)` — sends one `SendInput` `KEYDOWN` event with `KEYEVENTF_SCANCODE` (+ `KEYEVENTF_EXTENDEDKEY` if applicable). Tracks `key_id` in a `held` set. Returns `bool` success (checks `SendInput` return value).
  - `key_up(key_id)` — sends one `SendInput` `KEYUP` event. Removes from `held`.
  - `release_all()` — calls `key_up` for every currently held key; safe to call repeatedly/on empty state.
  - Uses `ctypes.Structure` definitions for `KEYBDINPUT`/`INPUT` matching the MSDN layout (`wVk=0`, `wScan=<scancode>`, `dwFlags=KEYEVENTF_SCANCODE|...`).

### `keyboard_layout.py`

- Static data describing a TKL (tenkeyless) layout: Esc row, F1–F12, number row, QWERTY/ASDF/ZXCV rows, modifier/space row, and a navigation cluster (arrows, ins/del/home/end/pgup/pgdn). No numpad.
- Each entry: `(display_label, key_id, relative_width)`. `key_id` matches a `SCANCODES` key.

### `app.py`

- Builds one `tk.Button` per layout entry, arranged in rows via `grid`/`pack` matching physical keyboard proportions (using `relative_width` to size keys like backspace/enter/space wider).
- Button click handler: flips a toggle; on toggle-on calls `key_down`, on toggle-off calls `key_up`. On success, recolors button (gray = released, green = held). On `SendInput` failure, reverts the toggle and shows a brief warning in a status label — does not claim a held state that didn't actually happen.
- "Release All" button: calls `release_all()` and resets every button to released/gray.
- Panic hotkey: a `root.after(50, poll_panic_key)` loop calls `ctypes.windll.user32.GetAsyncKeyState(VK_PAUSE)`; on a fresh press (edge-triggered, not held-down spam) it calls `release_all()` and resets the UI. Polling continues regardless of window focus.
- On `WM_DELETE_WINDOW` and via `atexit.register`, calls `release_all()` so closing the app (or a crash) never leaves keys stuck down.

### `main.py`

- Checks `sys.platform == "win32"`; if not, prints a clear error and exits (no partial UI).
- Constructs `KeyboardController`, builds the Tkinter root/app, starts `mainloop()`.

## Data Flow

Click → toggle flips → `KeyboardController.key_down`/`key_up` → `SendInput` (scan code, correct flags) → OS delivers a real key-down/up to whichever app has focus → button recolors on confirmed success.

## Error Handling

- `SendInput` return value of 0 → treated as failure: toggle reverts, status label shows a short warning (e.g. "Failed to hold <key>").
- Panic-key poll loop wraps its body in try/except so one failure doesn't kill the periodic callback.
- Non-Windows platforms: fail fast at startup with a clear message rather than silently doing nothing.

## Known Limitations (documented, not solved in code)

- Anti-cheat systems and games using low-level raw input filtering may ignore all synthetic input regardless of technique; this app cannot defeat that.
- Using synthetic input in multiplayer games likely violates the game's terms of service — user's responsibility.
- If the target application runs elevated (as Administrator), Windows UIPI may block `SendInput` from a non-elevated KeyHolder; user may need to run KeyHolder as Administrator too. Not auto-elevated.

## Testing Plan

- **Unit** (`tests/test_input_backend.py`): mock `ctypes.windll.user32.SendInput`, assert `key_down`/`key_up` construct the correct scan code + extended-key flag per key_id; assert `release_all()` calls `key_up` for every held key and clears state; assert failure path (mocked return 0) does not add to `held`.
- **Manual**: toggle a handful of keys and confirm behavior in Notepad (character keys) and verify the Pause key releases all held keys from an unfocused window.

## Out of Scope

- Numpad keys.
- Global hotkey via `RegisterHotKey`/window message hook (polling `GetAsyncKeyState` instead — simpler, works unfocused, sufficient latency for a panic button).
- Admin auto-elevation.
- Saving/loading toggle presets.
