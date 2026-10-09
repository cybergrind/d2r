"""The canvas follows the player and the marked monsters by reading their path bytes itself."""

import struct

from inventory_tracking.hud.live import (
    Entrance,
    LiveUnits,
    OpenPanels,
    follow,
    ground_payload_of,
    panel_source,
    position,
)
from inventory_tracking.hud.scene import Widget


PLAYER, MONSTER = 0x1000, 0x2000


def path_bytes(x, y, x_fraction=0, y_fraction=0):
    return struct.pack('<HHHH', x_fraction, x, y_fraction, y)


def payload(player=(20.0, 30.0), live=(7, PLAYER), marks=(('leader', 21.0, 30.0),)):
    return {'player': list(player), 'marks': [list(mark) for mark in marks], 'live': list(live) if live else None}


def reader(memory, calls=None):
    """`memory`: address -> path bytes or an exception; other addresses are unreadable."""

    def read(fd, size, address):
        if calls is not None:
            calls.append((fd, size, address))
        data = memory.get(address, OSError('unmapped'))
        if isinstance(data, Exception):
            raise data
        return data

    return LiveUnits(open_memory=lambda pid: 100 + pid, read=read)


def test_path_bytes_are_whole_world_units_plus_a_fraction_in_tiles():
    assert position(path_bytes(100, 150)) == (20.0, 30.0)
    assert position(path_bytes(101, 150, x_fraction=0x8000)) == (20.3, 30.0)


def test_the_position_is_read_at_the_published_address_of_the_published_process(monkeypatch):
    monkeypatch.setattr('os.close', lambda fd: None)
    calls = []
    live = reader({PLAYER: path_bytes(103, 149)}, calls)

    assert live.locate(payload())['player'] == [20.6, 29.8]
    assert live.locate(payload())['player'] == [20.6, 29.8]
    assert calls == [(107, 8, PLAYER)] * 2  # one open, reused


def test_a_mark_with_a_path_address_is_read_like_the_player(monkeypatch):
    monkeypatch.setattr('os.close', lambda fd: None)
    marks = (('leader', 21.0, 30.0, MONSTER), ('stairs', 25.0, 31.0))
    live = reader({PLAYER: path_bytes(100, 150), MONSTER: path_bytes(110, 152)})

    assert live.locate(payload(marks=marks)) == {
        'player': [20.0, 30.0],
        'marks': [['leader', 22.0, 30.4, MONSTER], ['stairs', 25.0, 31.0]],
        'live': [7, PLAYER],
    }


def test_each_published_position_stands_when_its_own_read_fails_or_is_far_off(monkeypatch):
    monkeypatch.setattr('os.close', lambda fd: None)
    marks = (('leader', 21.0, 30.0, MONSTER),)
    published = payload(marks=marks)

    assert reader({}).locate(payload(live=None)) is None
    # a freed monster path does not stop the player being followed, and the other way round
    assert reader({PLAYER: path_bytes(103, 149)}).locate(published) == {**published, 'player': [20.6, 29.8]}
    moved = reader({MONSTER: path_bytes(110, 152)}).locate(published)
    assert moved == {**published, 'marks': [['leader', 22.0, 30.4, MONSTER]]}
    # another level, or a path the game reused
    far = reader({PLAYER: path_bytes(4000, 149), MONSTER: path_bytes(4000, 152)})
    assert far.locate(published) == published


def test_a_game_that_cannot_be_opened_leaves_the_payload_alone():
    def refuse(pid):
        raise PermissionError('ptrace scope')

    assert LiveUnits(open_memory=refuse).locate(payload()) is None


def test_only_the_ground_widget_follows_the_live_positions():
    ground = Widget('ground', 'ground', 'ground', payload())
    card = Widget('map', 'guide', 'map', {'lines': [], 'map': None})
    boxes = [(ground, (0, 0, 800, 450)), (card, (10, 10, 50, 50))]
    live = {**payload(), 'player': [21.5, 30.0]}

    moved = follow(boxes, live)

    assert moved[0][0].payload == live
    assert moved[0][1] == (0, 0, 800, 450)
    assert moved[1] == boxes[1]
    assert follow(boxes, None) is boxes
    assert ground_payload_of(boxes) == payload()
    assert ground_payload_of(boxes[1:]) is None


def test_the_time_since_entering_restarts_with_another_level_and_not_with_moving_marks():
    entrance = Entrance()
    here = {**payload(), 'level': 11}

    assert entrance.age(here, 100.0) == 0.0
    assert entrance.age({**here, 'player': [25.0, 30.0], 'marks': []}, 101.5) == 1.5
    assert entrance.age({**here, 'level': 12}, 102.0) == 0.0
    assert entrance.age(None, 103.0) is None  # the marks are hidden: shown again, they start over
    assert entrance.age({**here, 'level': 12}, 104.0) == 0.0


def test_the_map_card_player_follows_the_live_position():
    card = {'lines': [], 'map': {'map': {'rooms': [[0, 0, 8, 8]], 'player': [20.0, 30.0], 'pois': []}}}
    boxes = [
        (Widget('map', 'guide', 'map', card), (0, 0, 400, 300)),
        (Widget('rows', 'guide', 'guide', {'lines': []}), (0, 0, 1, 1)),
    ]

    moved = follow(boxes, {**payload(), 'player': [20.6, 29.8]})

    assert moved[0][0].payload['map']['map']['player'] == [20.6, 29.8]
    assert moved[0][0].payload['map']['map']['rooms'] == [[0, 0, 8, 8]]
    assert card['map']['map']['player'] == [20.0, 30.0]
    assert moved[1] == boxes[1]


FLAGS = 0x3000


def panel_bytes(*names):
    from inventory_tracking.native.layout import PANEL_FLAGS, UI_PANELS_SIZE

    raw = bytearray(UI_PANELS_SIZE)
    for name in names:
        raw[PANEL_FLAGS[name]] = 1
    return bytes(raw)


def panels(memory, names=('inventory', 'mercenary')):
    def read(fd, size, address):
        data = memory.get(address, OSError('unmapped'))
        if isinstance(data, Exception):
            raise data
        return data

    return OpenPanels(names, open_memory=lambda pid: 100 + pid, read=read)


def test_an_open_item_panel_is_read_at_the_published_address(monkeypatch):
    monkeypatch.setattr('os.close', lambda fd: None)

    assert panels({FLAGS: panel_bytes('mercenary')}).reading([7, FLAGS])
    assert panels({FLAGS: panel_bytes('inventory', 'stash')}).reading([7, FLAGS])
    # panels the player does not read items in, and no panel at all
    assert not panels({FLAGS: panel_bytes('belt_rows', 'chat')}).reading([7, FLAGS])
    assert not panels({FLAGS: panel_bytes()}).reading([7, FLAGS])


def test_nothing_is_dimmed_when_the_flags_cannot_be_trusted(monkeypatch):
    monkeypatch.setattr('os.close', lambda fd: None)

    def refuse(pid):
        raise PermissionError('ptrace scope')

    assert not panels({}).reading(None)  # no producer names the game
    assert not panels({}).reading([7, FLAGS])  # the game is gone
    assert not panels({FLAGS: b'\x02' + panel_bytes('inventory')[1:]}).reading([7, FLAGS])  # not a flag array
    assert not OpenPanels(('inventory',), open_memory=refuse).reading([7, FLAGS])


def test_the_panel_source_is_taken_out_of_the_scene_before_layout():
    source = Widget('panels', 'panels', 'panels', {'live': [7, FLAGS]})
    card = Widget('map', 'guide', 'map', {'lines': [], 'map': None})

    assert panel_source([card, source]) == ([7, FLAGS], [card])
    assert panel_source([card]) == (None, [card])
