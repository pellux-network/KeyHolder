import input_backend as ib
import keyboard_layout as kl


def test_every_key_id_in_layout_has_a_scancode():
    # A None key_id is a blank spacer slot, not a key — see NAV_ROWS.
    missing = []
    for row in kl.ROWS + kl.NAV_ROWS:
        for _label, key_id, _width in row:
            if key_id is not None and key_id not in ib.SCANCODES:
                missing.append(key_id)
    assert missing == []


def test_layout_has_no_duplicate_key_ids():
    seen = []
    for row in kl.ROWS + kl.NAV_ROWS:
        for _label, key_id, _width in row:
            if key_id is not None:
                seen.append(key_id)
    assert len(seen) == len(set(seen)), "duplicate key_id in layout"
