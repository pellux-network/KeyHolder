![KeyHolder](assets/logo.png)

[![CI](https://github.com/pellux-network/KeyHolder/actions/workflows/ci.yml/badge.svg)](https://github.com/pellux-network/KeyHolder/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/pellux-network/KeyHolder)](https://github.com/pellux-network/KeyHolder/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Toggle keyboard keys on/off as if physically held down, via a PySide6 UI.
Uses the Win32 `SendInput` API with hardware scan codes — Windows only.

## Download

Grab the latest `KeyHolder.exe` from the [Releases page](https://github.com/pellux-network/KeyHolder/releases/latest) —
no Python install required. Each release's exe is built and verified on GitHub's
own servers directly from the tagged source.

## Run from source

    pip install -e .
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
- Python 3.10+
- `PySide6` (installed automatically via `pip install -e .`)

## Development

    pip install -e .[dev]
    python -m ruff check .
    python -m pytest -v

CI runs both on every push and pull request. `master` is a protected branch —
changes go through a pull request, which must pass CI before merging.

Releases are automated: [release-please](https://github.com/googleapis/release-please)
opens a release PR from [Conventional Commits](https://www.conventionalcommits.org/)
on `master`; merging it tags a release, which triggers a workflow that builds
`KeyHolder.exe` with PyInstaller on a GitHub-hosted Windows runner and attaches
it to that release.

## Known limitations

- Anti-cheat systems and games that filter raw/low-level input may ignore
  all synthetic input regardless of technique.
- Using synthetic input in multiplayer games likely violates that game's
  terms of service — that's on you.
- If the target application runs elevated (as Administrator), Windows UIPI
  may block input from a non-elevated KeyHolder; run KeyHolder as
  Administrator too in that case.

## License

[MIT](LICENSE)
