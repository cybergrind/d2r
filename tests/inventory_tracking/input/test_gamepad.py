"""The gamepad experiment's hotkey (input/gamepad.py): what a press does with and without a device."""

import os
import struct
from pathlib import Path

import pytest

from inventory_tracking.input import gamepad
from inventory_tracking.input.gamepad import ABS_COUNT, Pad, PadKeys


class FakePad:
    def __init__(self) -> None:
        self.taps: list[str] = []
        self.closed = False
        self.pressed_at: float | None = None

    def tap(self, button: str) -> None:
        self.taps.append(button)
        self.pressed_at = 50.0 + len(self.taps)

    def close(self) -> None:
        self.closed = True


def test_a_press_makes_the_pad_once_and_taps_the_button(monkeypatch) -> None:
    monkeypatch.setattr(gamepad, 'problem', lambda: None)
    made: list[FakePad] = []
    keys = PadKeys(make=lambda: made.append(FakePad()) or made[-1])
    assert keys.request('a', 10.0, 10.2)
    assert keys.request('rt', 11.0, 11.1)
    assert len(made) == 1
    assert made[0].taps == ['a', 'rt']
    assert keys.pressed_at == 52.0  # the device's own time of the press, for the flip timing
    assert keys.request('up', 12.0, 12.1)  # a d-pad direction is a name too
    keys.close()
    assert made[0].closed
    assert keys.pad is None


def test_a_stale_press_or_an_unknown_button_does_nothing(monkeypatch) -> None:
    monkeypatch.setattr(gamepad, 'problem', lambda: None)
    made: list[FakePad] = []
    keys = PadKeys(make=lambda: made.append(FakePad()) or made[-1])
    assert not keys.request('a', 10.0, 12.0)
    assert not keys.request('nose', 10.0, 10.1)
    assert not made


def test_no_device_is_said_and_no_pad_is_made(monkeypatch, caplog) -> None:
    monkeypatch.setattr(gamepad, 'problem', lambda: '/dev/uinput is not there: `sudo modprobe uinput`')
    keys = PadKeys(make=lambda: (_ for _ in ()).throw(AssertionError('made')))
    with caplog.at_level('WARNING'):
        keys.start()
        assert not keys.request('a', 10.0, 10.1)
    assert 'modprobe uinput' in caplog.text


def test_the_setup_record_is_the_kernels_size() -> None:
    # struct uinput_user_dev: char name[80]; struct input_id (4 x u16); u32; 4 x s32[ABS_CNT]
    assert struct.calcsize('80sHHHHI') + 4 * ABS_COUNT * 4 == 1116


def bindings(skills: dict[int, int]) -> bytes:
    rows = [
        struct.pack('<7i', skills.get(at, -1), -1, 0x379C4001 if at in skills else 1, 4, 255, 0, 0) for at in range(32)
    ]
    return b'\x01\x00\x00\x00' + b''.join(rows)


def ctlo(saved: Path, name: str, skills: dict[int, int]) -> Path:
    path = saved / name
    path.write_bytes(bindings(skills))
    return path


def record(data: bytes, at: int) -> tuple[int, ...]:
    return struct.unpack_from('<7i', data, 4 + 28 * at)


TABLE = {1: 370, 3: 388, 4: 390, 9: 375}


def test_the_table_goes_on_empty_records_with_the_hand_of_each_skill_and_the_file_as_it_was_is_kept(tmp_path) -> None:
    saved, keep = tmp_path / 'saved', tmp_path / 'keep'
    saved.mkdir()
    before = bindings({0: 0, 2: 395, 7: 359})
    path = ctlo(saved, 'CybergrindAA194867311.ctlo', {0: 0, 2: 395, 7: 359})
    other = ctlo(saved, 'CybergrindAAB1.ctlo', {0: 0, 2: 395, 7: 359})  # another character: its start is the same
    said = gamepad.bind_table(saved, 'CybergrindAA', TABLE, keep, stamp=lambda: 'T1', names={388: 'Echoing Strike'})
    after = path.read_bytes()
    assert record(after, 1) == (370, -1, 0x379C4000, 4, 255, 0, 0)  # right hand, the first record's padding
    assert record(after, 3) == (388, -1, 0x379C4001, 4, 255, 0, 0)  # left hand (skills.txt leftskill)
    assert [record(after, at)[0] for at in range(12)] == [0, 370, 395, 388, 390, -1, -1, 359, -1, 375, -1, -1]
    assert after[:4] == before[:4]
    assert after[4 + 28 * 12 :] == before[4 + 28 * 12 :]
    assert (keep / 'CybergrindAA194867311.ctlo.T1').read_bytes() == before
    assert other.read_bytes() == before
    assert 'CybergrindAA194867311.ctlo: record 3 (Y) empty -> Echoing Strike' in said
    assert 'CybergrindAA194867311.ctlo: record 9 (LT+Y) empty -> Death Mark' not in said  # no name given: its id
    assert 'CybergrindAA194867311.ctlo: record 9 (LT+Y) empty -> skill 375' in said
    # a second start changes nothing and copies nothing
    again = gamepad.bind_table(saved, 'CybergrindAA', TABLE, keep, stamp=lambda: 'T2')
    assert again == ['CybergrindAA194867311.ctlo: nothing to write (records in use: 0: 0, 1: 370, 2: 395, '
                     '3: 388, 4: 390, 7: 359, 9: 375)']  # fmt: skip
    assert path.read_bytes() == after
    assert not (keep / 'CybergrindAA194867311.ctlo.T2').exists()


def test_the_players_records_and_skills_they_placed_elsewhere_are_left_alone_unless_named(tmp_path) -> None:
    saved, keep = tmp_path / 'saved', tmp_path / 'keep'
    saved.mkdir()
    path = ctlo(saved, 'Name.ctl', {0: 0, 2: 395, 3: 36, 5: 388})
    said = gamepad.bind_table(saved, 'Name', {2: 377, 3: 388, 4: 390}, keep, stamp=lambda: 'T')
    skills = [record(path.read_bytes(), at)[0] for at in range(6)]
    assert skills == [0, -1, 395, 36, 390, 388]
    assert any('record 2 holds Miasma Bolt (set by the player), skill 377 not written' in line for line in said)
    assert any('skill 388 is on record 5 already, not put on 3' in line for line in said)
    said = gamepad.bind_table(saved, 'Name', {2: 377}, keep, overwrite=(2,), stamp=lambda: 'U')
    assert record(path.read_bytes(), 2)[0] == 377
    assert 'Name.ctl: record 2 (B) Miasma Bolt -> skill 377' in said


def test_a_file_of_another_size_or_no_file_is_not_touched(tmp_path) -> None:
    saved = tmp_path / 'saved'
    saved.mkdir()
    before = bindings({0: 0, 1: 36})
    (saved / 'Name.ctl').write_bytes(before[:-1])
    assert 'not touched' in gamepad.bind_table(saved, 'Name', TABLE, tmp_path / 'keep')[0]
    assert (saved / 'Name.ctl').read_bytes() == before[:-1]
    assert 'no controller bindings' in gamepad.bind_table(saved, 'Other', TABLE, tmp_path / 'keep')[0]
    assert not (tmp_path / 'keep').exists()


def test_records_name_their_buttons_and_the_legend_lists_the_bound_ones() -> None:
    assert gamepad.record_buttons(3) == ('y',)
    assert gamepad.record_buttons(9) == ('lt', 'y')
    assert [gamepad.record_label(at) for at in (0, 1, 2, 5, 6, 11, 19, 30)] == [
        'A', 'X', 'B', 'RT', 'LT+A', 'LT+RT', 'Y (other weapons)', 'record 30'
    ]  # fmt: skip
    assert gamepad.legend((0, 370, -1, 388) + (-1,) * 3 + (359,), {388: 'Echoing Strike'}) == (
        'A Attack, X Loot to Cube, Y Echoing Strike, LT+X Town Portal'
    )


def test_records_12_to_15_are_reached_by_keys_and_the_legend_reaches_the_other_weapon_set() -> None:
    # rca/2026-10-13/controller-gaps.md section 2: records 12-15 have no pad button; 16-27 the second weapon set.
    assert [gamepad.record_label(at) for at in (12, 15, 16, 27, 28)] == [
        'record 12 (by key)', 'record 15 (by key)', 'A (other weapons)', 'LT+RT (other weapons)', 'record 28'
    ]  # fmt: skip
    skills = (0,) + (-1,) * 11 + (382, 379) + (-1,) * 2 + (54,) + (-1,) * 15
    assert gamepad.legend(skills, {379: 'Engorge', 382: 'Bind Demon'}) == 'A Attack'  # records 0-11 by default
    assert gamepad.legend(skills, {379: 'Engorge', 382: 'Bind Demon'}, upto=28) == (
        'A Attack, record 12 (by key) Bind Demon, record 13 (by key) Engorge, A (other weapons) Teleport'
    )


def test_the_summon_defiler_record_replaces_miasma_bolt_and_the_key_records_go_on_empty_ones(tmp_path) -> None:
    # The table of 2026-10-13 late (config gamepad_bindings with gamepad_overwrite (2,)) on the file as it was.
    saved, keep = tmp_path / 'saved', tmp_path / 'keep'
    saved.mkdir()
    was = {0: 0, 1: 370, 2: 395, 3: 388, 4: 390, 5: 54, 6: 387, 7: 359, 8: 389, 9: 375, 10: 393, 11: 381}
    path = ctlo(saved, 'CybergrindAA194867311.ctlo', was)
    table = {**{at: skill for at, skill in was.items() if at not in (0, 2, 7)}, 2: 377, 12: 382, 13: 379}
    said = gamepad.bind_table(saved, 'CybergrindAA', table, keep, overwrite=(2,), stamp=lambda: 'T')
    after = path.read_bytes()
    assert [record(after, at)[0] for at in range(16)] == [*(was[at] for at in range(2)), 377, *(
        was[at] for at in range(3, 12)), 382, 379, -1, -1]  # fmt: skip
    assert record(after, 13)[2] & 0xFF == 1  # Engorge: the left hand (skills.txt leftskill)
    assert record(after, 12)[2] & 0xFF == 0
    assert 'CybergrindAA194867311.ctlo: record 2 (B) Miasma Bolt -> skill 377' in said
    assert 'CybergrindAA194867311.ctlo: record 13 (record 13 (by key)) empty -> skill 379' in said


def test_the_controller_settings_are_read_from_settings_json(tmp_path) -> None:
    (tmp_path / 'Settings.json').write_text(
        '{"Quick Cast Enabled": 1, "Controller Weapon Swap Separate Bindings": 0, "Other": 3}'
    )
    assert gamepad.read_settings(tmp_path) == {
        'Quick Cast Enabled': 1, 'Controller Weapon Swap Separate Bindings': 0
    }  # fmt: skip
    (tmp_path / 'Settings.json').write_text('{}')
    assert gamepad.read_settings(tmp_path) == {
        'Quick Cast Enabled': None,
        'Controller Weapon Swap Separate Bindings': None,
    }
    with pytest.raises(FileNotFoundError):
        gamepad.read_settings(tmp_path / 'none')


class Device:
    """A pipe in place of /dev/uinput: what the pad writes is read back as input events."""

    def __init__(self) -> None:
        self.read_end, self.write_end = os.pipe()

    def events(self) -> list[tuple[int, int, int]]:
        size = struct.calcsize('llHHi')
        data = b''
        os.set_blocking(self.read_end, False)
        try:
            while chunk := os.read(self.read_end, 65536):
                data += chunk
        except BlockingIOError:
            pass
        return [struct.unpack_from('llHHi', data, at)[2:] for at in range(0, len(data), size)]


def pad_on(device: Device, slept: list[float]) -> Pad:
    return Pad(sleep=slept.append, clock=lambda: 100.0, open_device=lambda: device.write_end)


SYN = (0, 0, 0)


def test_a_record_is_pressed_with_its_modifier_first_and_let_go_in_reverse() -> None:
    device, slept = Device(), []
    pad = pad_on(device, slept)
    pad.tap_record(9, hold=0.05)
    assert device.events() == [(3, 2, 255), SYN, (1, 0x134, 1), SYN, (1, 0x134, 0), SYN, (3, 2, 0), SYN]
    assert slept == [gamepad.SETTLE, 0.05]  # the first input waits for Wine to have the device
    assert not pad.held()


def test_held_inputs_and_sticks_are_known_and_neutral_lets_everything_go() -> None:
    device, slept = Device(), []
    pad = pad_on(device, slept)
    pad.press('rb', 'up')
    pad.stick('left', 3.0, -4.0)  # cut to length 1
    assert pad.held()
    assert pad.down == {'rb', 'up'}
    assert pad.sticks['left'] == pytest.approx((0.6, -0.8))
    pad.press('down')  # the other way on the same axis replaces 'up'
    assert pad.down == {'rb', 'down'}
    device.events()
    pad.neutral()
    events = device.events()
    assert {(1, 0x137, 0), (3, 17, 0), (3, 0, 0), (3, 1, 0)} <= set(events)
    assert not pad.held()


def test_a_held_stick_is_centred_after_its_time_and_unknown_names_are_refused() -> None:
    device, slept = Device(), []
    pad = pad_on(device, slept)
    pad.hold_stick('right', 1.0, 0.0, 0.3)
    assert device.events() == [(3, 3, 32767), (3, 4, 0), SYN, (3, 3, 0), (3, 4, 0), SYN]
    assert slept[-1] == 0.3
    assert not pad.held()
    with pytest.raises(ValueError, match='nose'):
        pad.press('nose')
    with pytest.raises(ValueError, match='middle'):
        pad.stick('middle', 0, 0)
