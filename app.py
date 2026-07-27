import atexit
import ctypes
import tkinter as tk

import keyboard_layout as kl

VK_PAUSE = 0x13
COLOR_RELEASED = "#dddddd"
COLOR_HELD = "#4caf50"
BASE_WIDTH = 4

# A real held key isn't a single make-code: the keyboard hardware itself
# re-sends the make code at a "typematic" rate after an initial delay, which
# is what makes message-based apps (Notepad, Java/AWT clients like OSRS) see
# continuous input. A lone SendInput key-down only produces one WM_KEYDOWN,
# so we replicate the repeat ourselves while a key is toggled held.
INITIAL_REPEAT_DELAY_MS = 500
REPEAT_INTERVAL_MS = 33


class KeyButton:
    def __init__(self, parent, label, key_id, controller, status_var, width, on_toggle):
        self.key_id = key_id
        self.controller = controller
        self.status_var = status_var
        self.held = False
        self.on_toggle = on_toggle
        self.button = tk.Button(
            parent,
            text=label,
            width=max(1, int(width * BASE_WIDTH)),
            bg=COLOR_RELEASED,
            command=self._handle_click,
        )

    def _handle_click(self) -> None:
        if self.held:
            ok = self.controller.key_up(self.key_id)
            if not ok:
                self.status_var.set(f"Failed to toggle {self.button['text']}")
                return
            self.held = False
            self.button.config(bg=COLOR_RELEASED)
        else:
            ok = self.controller.key_down(self.key_id)
            if not ok:
                self.status_var.set(f"Failed to toggle {self.button['text']}")
                return
            self.held = True
            self.button.config(bg=COLOR_HELD)
        self.on_toggle(self)

    def reset(self) -> None:
        self.held = False
        self.button.config(bg=COLOR_RELEASED)


class KeyHolderApp:
    def __init__(self, root: tk.Tk, controller):
        self.root = root
        self.controller = controller
        self.status_var = tk.StringVar(value="Ready")
        self.repeat_enabled = tk.BooleanVar(value=True)
        self.key_buttons: list[KeyButton] = []
        self._repeat_jobs: dict[str, str] = {}
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
        tk.Checkbutton(
            controls_frame,
            text="Repeat mode (for apps that don't poll raw key state)",
            variable=self.repeat_enabled,
            command=self._on_repeat_enabled_changed,
        ).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(controls_frame, text="Panic key: Pause/Break").pack(side=tk.RIGHT)
        tk.Label(controls_frame, textvariable=self.status_var, fg=COLOR_HELD).pack(side=tk.LEFT, expand=True)

    def _build_row(self, parent: tk.Frame, row) -> None:
        row_frame = tk.Frame(parent)
        row_frame.pack(anchor=tk.W)
        for label, key_id, width in row:
            kb = KeyButton(
                row_frame, label, key_id, self.controller, self.status_var, width, self._on_key_toggled
            )
            kb.button.pack(side=tk.LEFT, padx=1, pady=1)
            self.key_buttons.append(kb)

    def _on_key_toggled(self, kb: KeyButton) -> None:
        if kb.held:
            if self.repeat_enabled.get():
                self._start_repeat(kb)
        else:
            self._stop_repeat(kb.key_id)

    def _on_repeat_enabled_changed(self) -> None:
        if self.repeat_enabled.get():
            for kb in self.key_buttons:
                if kb.held:
                    self._start_repeat(kb)
        else:
            for key_id in list(self._repeat_jobs.keys()):
                self._stop_repeat(key_id)

    def _start_repeat(self, kb: KeyButton) -> None:
        self._stop_repeat(kb.key_id)
        job_id = self.root.after(INITIAL_REPEAT_DELAY_MS, self._repeat_tick, kb)
        self._repeat_jobs[kb.key_id] = job_id

    def _repeat_tick(self, kb: KeyButton) -> None:
        if not kb.held:
            self._repeat_jobs.pop(kb.key_id, None)
            return
        self.controller.key_down(kb.key_id)
        job_id = self.root.after(REPEAT_INTERVAL_MS, self._repeat_tick, kb)
        self._repeat_jobs[kb.key_id] = job_id

    def _stop_repeat(self, key_id: str) -> None:
        job_id = self._repeat_jobs.pop(key_id, None)
        if job_id is not None:
            self.root.after_cancel(job_id)

    def release_all(self) -> None:
        for key_id in list(self._repeat_jobs.keys()):
            self._stop_repeat(key_id)
        self.controller.release_all()
        for kb in self.key_buttons:
            kb.reset()
        self.status_var.set("All keys released")

    def _register_exit_handlers(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        atexit.register(self.controller.release_all)

    def _on_close(self) -> None:
        self.release_all()
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
