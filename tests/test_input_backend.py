import ctypes
from unittest.mock import patch

import pytest

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
    with pytest.raises(KeyError):
        controller.key_down("not_a_real_key")


def test_input_struct_size_matches_win32_expectation():
    # SendInput validates cbSize against its own fixed INPUT size (the union
    # sized to fit MOUSEINPUT, the largest member): 40 bytes on 64-bit, 28 on
    # 32-bit. A union missing mi/hi silently undersizes INPUT and every
    # SendInput call is rejected with ERROR_INVALID_PARAMETER — this test
    # exists so a mock-only test suite can't hide that regression again.
    expected = 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28
    assert ctypes.sizeof(ib.INPUT) == expected


def test_key_down_actually_succeeds_via_real_sendinput():
    # An unmocked, end-to-end check: mocked SendInput tests can't catch a
    # struct layout bug, since the mock never touches the real Win32 ABI.
    controller = ib.KeyboardController()
    ctypes.set_last_error(0)
    try:
        result = controller.key_down("a")
        assert result is True, f"SendInput failed, GetLastError={ctypes.get_last_error()}"
    finally:
        controller.release_all()
