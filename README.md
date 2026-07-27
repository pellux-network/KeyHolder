![KeyHolder](assets/logo.png)

Toggle keyboard keys on/off as if physically held down, via a Tkinter UI.
Uses the Win32 `SendInput` API with hardware scan codes — Windows only.

## Run

    python main.py

## Usage

- Click any key to toggle it held (green) / released (gray). Clicking the
  button gives KeyHolder itself focus — switch to your target app shortly
  after clicking, well within the initial repeat delay (see below), so it
  keeps receiving key-down events.
- **Repeat mode** (checkbox, on by default): while a key is held, re-sends
  the key-down roughly every 33ms (after an initial ~500ms delay, like a
  real keyboard's typematic repeat). Needed for apps that read normal
  keyboard messages instead of polling raw key state. Turn it off for apps
  that poll raw key state (`GetAsyncKeyState`/DirectInput/raw input): a
  single key-down already registers as held for those, and skipping the
  repeat avoids the continuous stream of synthetic events entirely.
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
