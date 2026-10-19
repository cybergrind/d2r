"""The game's input mode, read only (tracking/input_mode.py): the readers, the flip timing, the watch."""

import struct

import pytest

from inventory_tracking.models import InputMode
from inventory_tracking.native import memory as native_memory
from inventory_tracking.native.layout import (
    CONTROLLER_MODE_RVA,
    CTL_BINDINGS_RVA,
    CTL_PRESSED_RECORD,
    CTL_PRESSED_SKILL,
    CTL_STATE_RVA,
    CTL_STATE_STRIDE,
    CTL_TARGET,
    PANEL_MANAGER_RVA,
    PANEL_PENDING,
    PLAYER_SLOT_RVA,
)
from inventory_tracking.tracking.input_mode import (
    Flips,
    InputModeWatch,
    describe,
    read_bindings,
    read_controller,
    read_input_mode,
)


BASE = 0x140000000
MANAGER = 0x5000_0000
UNIT = 0x6000_0000


class Memory:
    """Bytes at addresses; a read must start at a stored address and fit in it."""

    def __init__(self, cells: dict[int, bytes]) -> None:
        self.cells = cells

    def __call__(self, address: int, size: int) -> bytes:
        data = self.cells.get(address)
        if data is None or len(data) < size:
            raise OSError(f'unmapped {address:#x}')
        return data[:size]


def memory(mode=0, pending=0, wanted=0, manager=MANAGER, slot=0, target=0, record=-1, skill=-1, skills=None):
    state = BASE + CTL_STATE_RVA + CTL_STATE_STRIDE * slot
    rows = skills or {}
    table = b''.join(struct.pack('<7i', rows.get(at, -1), -1, 1, 4, 255, 0, 0) for at in range(32))
    return Memory({
        BASE + CONTROLLER_MODE_RVA: bytes([mode]),
        BASE + PANEL_MANAGER_RVA: struct.pack('<Q', manager),
        MANAGER + PANEL_PENDING: bytes([pending, wanted]),
        BASE + CTL_BINDINGS_RVA: table,
        BASE + PLAYER_SLOT_RVA: struct.pack('<I', slot),
        state + CTL_TARGET: struct.pack('<Q', target),
        state + CTL_PRESSED_RECORD: struct.pack('<i', record),
        state + CTL_PRESSED_SKILL: struct.pack('<i', skill),
        UNIT: struct.pack('<III', 1, 42, 7001),
    })  # fmt: skip


def test_the_mode_byte_and_the_panel_managers_flag_are_read():
    assert read_input_mode(memory(), BASE) == InputMode(False)
    assert read_input_mode(memory(mode=1), BASE) == InputMode(True)
    assert read_input_mode(memory(pending=1, wanted=1), BASE) == InputMode(False, True, True)
    assert read_input_mode(memory(mode=1, manager=0), BASE) == InputMode(True)
    with pytest.raises(ValueError, match='reads 7'):
        read_input_mode(memory(mode=7), BASE)


def test_the_label_says_where_a_flip_is_going():
    assert InputMode(False).label == 'keyboard'
    assert InputMode(True).label == 'controller'
    assert InputMode(False, True, True).label == 'switching to controller'
    assert InputMode(True, True, False).label == 'switching to keyboard'
    assert InputMode(True, True, True).label == 'controller'  # a reload in the same mode (the pad's glyphs)


def test_the_loaded_bindings_and_the_controllers_target_are_read():
    assert read_bindings(memory(skills={0: 0, 1: 370, 7: 359}), BASE)[:8] == (0, 370, -1, -1, -1, -1, -1, 359)
    state = read_controller(memory(mode=1, slot=1, target=UNIT, record=3, skill=388), BASE)
    assert (state.target, state.record, state.skill) == ((1, 7001), 3, 388)
    assert read_controller(memory(mode=1), BASE).fields() == {'target': None, 'record': -1, 'skill': -1}


class Log:
    def __init__(self) -> None:
        self.notes: list[tuple[str, dict]] = []

    def __call__(self, kind: str, **fields) -> None:
        self.notes.append((kind, fields))


def test_a_flip_is_timed_from_the_ask_to_the_byte_and_to_the_reload(caplog):
    notes = Log()
    flips = Flips(pressed=lambda: 9.96, noted=notes)
    assert flips.see(10.0, InputMode(False)) is None
    assert flips.see(10.01, InputMode(False, True, True)) is None  # the pad press asked
    assert flips.see(11.21, InputMode(True, True, True)) is None  # the byte changed, the reload goes on
    with caplog.at_level('INFO'):
        flip = flips.see(11.26, InputMode(True))
    assert flip is not None
    assert (flip['from'], flip['to'], flip['changed']) == ('keyboard', 'controller', True)
    assert (flip['switched_ms'], flip['done_ms'], flip['from_press_ms'], flip['press_before_ask_ms']) == (
        1200,
        1250,
        1300,
        50,
    )
    assert flips.flips == 1
    assert flips.last_ms == 1250
    assert 'keyboard -> controller: switched 1200 ms after the ask, panels ready at 1250 ms' in caplog.text
    assert [fields.get('pending') for kind, fields in notes.notes] == [False, True, False]
    assert notes.notes[-1][1]['flip'] == flip


def test_a_flip_between_two_readings_is_said_as_such_and_an_old_press_is_not_its_cause():
    flips = Flips(pressed=lambda: 1.0)
    flips.see(10.0, InputMode(True))
    flip = flips.see(10.01, InputMode(False))
    assert flip is not None
    assert (flip['from'], flip['to'], flip['within_ms'], flip['from_press_ms'], flip['done_ms']) == (
        'controller',
        'keyboard',
        10,
        None,
        None,
    )
    assert describe(flip) == 'Input mode: controller -> keyboard: within one reading (10 ms)'


def test_a_reload_with_no_change_and_an_unreadable_game_are_no_flips():
    flips = Flips()
    flips.see(1.0, InputMode(True))
    flips.see(1.1, InputMode(True, True, True))
    flip = flips.see(1.3, InputMode(True))
    assert flip is not None
    assert not flip['changed']
    assert flips.flips == 0
    assert describe(flip).startswith('Input mode: the panels were reloaded, still controller')
    assert flips.see(2.0, None) is None
    assert flips.see(2.1, InputMode(False)) is None  # the first reading after: no flip


class Source:
    def __init__(self) -> None:
        self.pid, self.images = 1234, {'candidate_base': BASE}


def watch_on(cells: Memory, **kwargs) -> InputModeWatch:
    watch = InputModeWatch(Source(), start=False, **kwargs)
    watch.memory.fd, watch.bound = 99, (1234, BASE)
    watch.read = cells  # type: ignore[method-assign]
    return watch


def test_the_watch_reads_logs_the_bindings_and_notes_the_controllers_target(caplog):
    notes = Log()
    cells = memory(skills={0: 0, 1: 370, 3: 388, 7: 359})
    watch = watch_on(cells, noted=notes, names=lambda skills: f'{len([s for s in skills[:12] if s != -1])} bound')
    with caplog.at_level('INFO'):
        watch.step(5.0)
    assert watch.current == InputMode(False)
    assert 'Controller bindings loaded: 4 bound' in caplog.text
    assert watch.bindings is not None
    assert watch.bindings[3] == 388
    assert watch.controller is None
    cells.cells.update(memory(mode=1, target=UNIT, record=3, skill=388, skills={0: 0, 1: 370, 3: 388, 7: 359}).cells)
    watch.step(5.01)
    assert watch.current == InputMode(True)
    assert ('ctl', {'target': [1, 7001], 'record': 3, 'skill': 388}) in notes.notes
    watch.step(5.02)  # nothing changed: no second note
    assert sum(kind == 'ctl' for kind, _ in notes.notes) == 1


def test_an_unreadable_game_reads_as_none_and_poll_binds_the_attached_game(monkeypatch):
    watch = watch_on(Memory({}))
    watch.step(1.0)
    assert watch.current is None
    opened = []
    monkeypatch.setattr(native_memory.os, 'open', lambda path, flags: opened.append(path) or 77)
    monkeypatch.setattr(native_memory.os, 'close', lambda fd: None)
    fresh = InputModeWatch(Source(), start=False)
    fresh.poll(0.0)
    fresh.poll(0.5)  # within the poll interval: nothing
    assert opened == ['/proc/1234/mem']
    assert fresh.bound == (1234, BASE)
