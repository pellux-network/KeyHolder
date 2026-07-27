# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Run the app:
```
python main.py
```

Run the full test suite (pytest's scripts aren't on PATH, so invoke via `-m`):
```
python -m pytest -v
```

Run a single test:
```
python -m pytest tests/test_input_backend.py::test_key_down_sends_correct_scancode_and_sets_scancode_flag -v
```

Install dev dependencies (stdlib-only at runtime otherwise):
```
pip install -e .[dev]
```

Lint (must pass in CI):
```
python -m ruff check .
```

Note: `python -m ruff format` is *not* enforced — its default style would explode the compact `SCANCODES` dict in `input_backend.py` and the `ROWS`/`NAV_ROWS` tables in `keyboard_layout.py` into one-entry-per-line, which hurts their readability as scannable grids. Only `ruff check` (actual lint rules) is required.

Build the standalone Windows exe locally (same command CI uses on release):
```
pyinstaller --onefile --windowed --icon=assets/icon.ico --name KeyHolder main.py
```

## Architecture

Windows-only desktop app (Tkinter UI + Win32 `SendInput`) that lets you toggle a key into a simulated "held" state, for games/anti-AFK use. Four flat modules, no package directory:

- **`input_backend.py`** — the only module that talks to Win32. Defines `SCANCODES`, a `key_id -> (scan_code, is_extended)` table (Set-1 hardware scan codes, extended-key flag for arrows/ins/del/home/end/pgup/pgdn/right-ctrl/right-alt/win/menu), and `KeyboardController` (`key_down`/`key_up`/`release_all`), which injects events via `ctypes` + `SendInput` using `KEYEVENTF_SCANCODE` (not virtual-key codes) so input is closer to real hardware. `KeyboardController.held` tracks which `key_id`s are currently down.

  **Non-obvious gotcha:** the ctypes `INPUT` struct's union must define `mi` (`MOUSEINPUT`) and `hi` (`HARDWAREINPUT`) alongside `ki` (`KEYBDINPUT`), even though only `ki` is ever used. `SendInput` validates the `cbSize` argument against its own fixed struct size (sized to fit the largest union member, `MOUSEINPUT`); a union with only `ki` computes a smaller `sizeof(INPUT)` and every call silently fails with `ERROR_INVALID_PARAMETER` (confirmed via `GetLastError`). `test_input_struct_size_matches_win32_expectation` guards this.

- **`keyboard_layout.py`** — pure data: `ROWS` (main TKL block) and `NAV_ROWS` (ins/home/pgup/del/end/pgdn/arrows), each a list of rows of `(display_label, key_id, relative_width)`. No numpad. Every `key_id` referenced here must exist in `input_backend.SCANCODES` — enforced by `test_every_key_id_in_layout_has_a_scancode`.

- **`app.py`** — Tkinter UI. `KeyButton` wraps one `tk.Button` and toggles held/released on click. `KeyHolderApp` builds the full layout from `keyboard_layout`, plus a "Release All" button and status label.

  **Typematic repeat:** a single `SendInput` key-down only produces one `WM_KEYDOWN` — real hardware repeats the make code at a fixed rate while a key is physically held, which is what makes message-based clients (Notepad, Java/AWT clients like OSRS) register continuous input. `KeyHolderApp` replicates this itself: `_start_repeat` schedules `_repeat_tick` via `root.after` after `INITIAL_REPEAT_DELAY_MS` (500ms), which then re-sends `key_down` every `REPEAT_INTERVAL_MS` (33ms, though Tkinter/timer overhead typically stretches this to ~46ms in practice) for as long as the button stays toggled on. Games that poll raw key state (`GetAsyncKeyState`/DirectInput/raw input) don't need this — the state is already correct after one `key_down` — but message-based apps do. Clicking a key button always gives KeyHolder's own window focus at that instant, so the target app must be focused within the initial delay window for the repeated events to land on it.

  **`repeat_enabled`** (`tk.BooleanVar`, default `True`, global — not per-key) is a UI checkbox gating the above: `_on_key_toggled` only calls `_start_repeat` when it's set. `_on_repeat_enabled_changed` reconciles state when the checkbox itself is flipped mid-session — starting repeat for any already-held keys if turned on, cancelling all `_repeat_jobs` if turned off. Off is the leaner/quieter mode for polling-based games (no continuous synthetic events); on is required for message-based apps.

  Also polls `GetAsyncKeyState(VK_PAUSE)` every 50ms as a global panic hotkey (`_poll_panic_key`) that calls `release_all()` regardless of which window has focus, and registers `release_all()` on both `WM_DELETE_WINDOW` and `atexit` so closing the app never leaves a key stuck down.

- **`main.py`** — entry point; exits early with a clear message on non-Windows platforms (`SendInput` is Win32-only), then wires `KeyboardController` and `KeyHolderApp` together.

- **`conftest.py`** — adds the repo root to `sys.path` so `tests/` (which has no parent package) can `import input_backend` / `import keyboard_layout` directly.

### Testing approach

`tests/test_input_backend.py` mostly mocks `input_backend.user32.SendInput` (via a `side_effect` that dereferences the `INPUT` pointer it's called with, to assert on the actual scan code/flags sent) rather than mocking at a higher level — this is what lets tests assert on the real struct contents built by `KeyboardController`. One test, `test_key_down_actually_succeeds_via_real_sendinput`, intentionally does *not* mock and calls the real Win32 API, specifically because the struct-size bug above only manifests against the real API — a fully-mocked suite could not have caught it.

`app.py` has no automated tests by design (GUI construction/interaction) — verify UI changes manually by running `python main.py`.

### Design docs

`docs/superpowers/specs/` and `docs/superpowers/plans/` hold the original design spec and implementation plan for this project, written via the superpowers brainstorming/planning skills — useful background on *why* things are shaped this way, not just what they do.

### CI/CD and release process

- **`master` is a protected branch.** Changes go through a pull request; `.github/workflows/ci.yml` (ruff + pytest) must pass before merging. No required review (solo-dev project).
- **Releases are managed by [release-please](https://github.com/googleapis/release-please)** (`.github/workflows/release-please.yml`, config in `release-please-config.json` / `.release-please-manifest.json`, release-type `simple`). It reads Conventional Commit messages on `master` and keeps an open "release PR" (updating `CHANGELOG.md` and the version) up to date. Merging that PR creates the actual GitHub Release + tag. The very first release was bootstrapped to `1.0.0` via a `Release-As: 1.0.0` commit trailer rather than natural semver bumping from zero.
- **`.github/workflows/release-build.yml`** triggers on `release: published`, builds `KeyHolder.exe` with PyInstaller on `windows-latest`, and uploads it as an asset on that same release via `gh release upload`.
- Commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`, `ci:`, `docs:`, `style:`, etc.) since release-please parses them to decide the next version bump.
