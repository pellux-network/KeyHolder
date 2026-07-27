import atexit
import ctypes

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

import keyboard_layout as kl

VK_PAUSE = 0x13
COLOR_RELEASED = "#3a3d41"
COLOR_RELEASED_TEXT = "#e8e8e8"
COLOR_HELD = "#43a047"
COLOR_HELD_TEXT = "#ffffff"
BASE_WIDTH_PX = 34

STYLESHEET = """
QWidget {
    background-color: #202124;
    color: #e8e8e8;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QPushButton {
    border: 1px solid #4a4d51;
    border-radius: 5px;
    padding: 5px 4px;
}
QPushButton:hover {
    border-color: #6a6d71;
}
QPushButton:pressed {
    padding-top: 6px;
    padding-bottom: 4px;
}
QPushButton#releaseAll {
    background-color: #3a2323;
    border-color: #7a3b3b;
    color: #f2b8b8;
    font-weight: 600;
    padding: 6px 14px;
}
QPushButton#releaseAll:hover {
    border-color: #b25555;
}
QCheckBox {
    spacing: 8px;
}
QLabel#panicLabel {
    color: #9a9da1;
}
"""

# A real held key isn't a single make-code: the keyboard hardware itself
# re-sends the make code at a "typematic" rate after an initial delay, which
# is what makes message-based apps (Notepad, Java/AWT clients like OSRS) see
# continuous input. A lone SendInput key-down only produces one WM_KEYDOWN,
# so we replicate the repeat ourselves while a key is toggled held.
INITIAL_REPEAT_DELAY_MS = 500
REPEAT_INTERVAL_MS = 33


class KeyButton(QPushButton):
    def __init__(self, label, key_id, controller, on_toggle, on_fail, width):
        super().__init__(label)
        self.key_id = key_id
        self.controller = controller
        self.on_toggle = on_toggle
        self.on_fail = on_fail
        self.held = False
        self.setMinimumWidth(max(34, int(width * BASE_WIDTH_PX)))
        self.setMinimumHeight(30)
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style()
        self.clicked.connect(self._handle_click)

    def _apply_style(self) -> None:
        bg, fg = (COLOR_HELD, COLOR_HELD_TEXT) if self.held else (COLOR_RELEASED, COLOR_RELEASED_TEXT)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {"#2e7d32" if self.held else "#4a4d51"};
                border-radius: 5px;
                padding: 5px 4px;
            }}
            QPushButton:hover {{
                border-color: {"#5cb860" if self.held else "#6a6d71"};
            }}
        """)

    def _handle_click(self) -> None:
        if self.held:
            ok = self.controller.key_up(self.key_id)
            if not ok:
                self.on_fail(self.text())
                return
            self.held = False
        else:
            ok = self.controller.key_down(self.key_id)
            if not ok:
                self.on_fail(self.text())
                return
            self.held = True
        self._apply_style()
        self.on_toggle(self)

    def reset(self) -> None:
        self.held = False
        self._apply_style()


class KeyHolderApp(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.key_buttons: list[KeyButton] = []
        self._repeat_timers: dict[str, QTimer] = {}
        self._panic_prev_pressed = False

        self.setWindowTitle("KeyHolder")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(STYLESHEET)
        self._build_ui()

        self._panic_timer = QTimer(self)
        self._panic_timer.timeout.connect(self._poll_panic_key)
        self._panic_timer.start(50)

        atexit.register(self.controller.release_all)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 12)
        outer.setSpacing(14)

        keyboard_row = QHBoxLayout()
        keyboard_row.setSpacing(20)

        keyboard_col = QVBoxLayout()
        keyboard_col.setSpacing(4)
        for row in kl.ROWS:
            keyboard_col.addLayout(self._build_row(row))
        keyboard_row.addLayout(keyboard_col)

        nav_col = QVBoxLayout()
        nav_col.setSpacing(4)
        for row in kl.NAV_ROWS:
            nav_col.addLayout(self._build_row(row))
        keyboard_row.addLayout(nav_col)
        keyboard_row.addStretch()

        outer.addLayout(keyboard_row)

        controls = QHBoxLayout()
        controls.setSpacing(12)

        release_btn = QPushButton("Release All")
        release_btn.setObjectName("releaseAll")
        release_btn.setCursor(Qt.PointingHandCursor)
        release_btn.clicked.connect(self.release_all)
        controls.addWidget(release_btn)

        self.repeat_checkbox = QCheckBox("Repeat mode (for apps that don't poll raw key state)")
        self.repeat_checkbox.setChecked(True)
        self.repeat_checkbox.toggled.connect(self._on_repeat_enabled_changed)
        controls.addWidget(self.repeat_checkbox)

        controls.addStretch()
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(f"color: {COLOR_HELD}; font-weight: 600;")
        controls.addWidget(self.status_label)
        controls.addStretch()

        panic_label = QLabel("Panic key: Pause/Break")
        panic_label.setObjectName("panicLabel")
        controls.addWidget(panic_label)

        outer.addLayout(controls)

    def _build_row(self, row) -> QHBoxLayout:
        row_layout = QHBoxLayout()
        row_layout.setSpacing(3)
        for label, key_id, width in row:
            if key_id is None:
                # Blank spacer slot — occupy the same footprint a same-width
                # button would (its width plus the inter-item spacing) so
                # later items line up under the correct column.
                row_layout.addSpacing(max(34, int(width * BASE_WIDTH_PX)) + row_layout.spacing())
                continue
            kb = KeyButton(label, key_id, self.controller, self._on_key_toggled, self._on_fail, width)
            row_layout.addWidget(kb)
            self.key_buttons.append(kb)
        row_layout.addStretch()
        return row_layout

    def _on_fail(self, label: str) -> None:
        self.status_label.setText(f"Failed to toggle {label}")

    def _on_key_toggled(self, kb: KeyButton) -> None:
        if kb.held:
            if self.repeat_checkbox.isChecked():
                self._start_repeat(kb)
        else:
            self._stop_repeat(kb.key_id)

    def _on_repeat_enabled_changed(self, checked: bool) -> None:
        if checked:
            for kb in self.key_buttons:
                if kb.held:
                    self._start_repeat(kb)
        else:
            for key_id in list(self._repeat_timers.keys()):
                self._stop_repeat(key_id)

    def _start_repeat(self, kb: KeyButton) -> None:
        self._stop_repeat(kb.key_id)
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._repeat_tick(kb))
        timer.start(INITIAL_REPEAT_DELAY_MS)
        self._repeat_timers[kb.key_id] = timer

    def _repeat_tick(self, kb: KeyButton) -> None:
        if not kb.held:
            self._repeat_timers.pop(kb.key_id, None)
            return
        self.controller.key_down(kb.key_id)
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._repeat_tick(kb))
        timer.start(REPEAT_INTERVAL_MS)
        self._repeat_timers[kb.key_id] = timer

    def _stop_repeat(self, key_id: str) -> None:
        timer = self._repeat_timers.pop(key_id, None)
        if timer is not None:
            timer.stop()

    def release_all(self) -> None:
        for key_id in list(self._repeat_timers.keys()):
            self._stop_repeat(key_id)
        self.controller.release_all()
        for kb in self.key_buttons:
            kb.reset()
        self.status_label.setText("All keys released")

    def _poll_panic_key(self) -> None:
        try:
            state = ctypes.windll.user32.GetAsyncKeyState(VK_PAUSE)
            pressed = bool(state & 0x8000)
            if pressed and not self._panic_prev_pressed:
                self.release_all()
            self._panic_prev_pressed = pressed
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        self.release_all()
        super().closeEvent(event)
