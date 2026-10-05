"""The canvas follows the player by reading the path bytes itself, and distrusts a stale address."""

import struct

from inventory_tracking.hud.live import LivePlayer, follow, ground_payload_of, position
from inventory_tracking.hud.scene import Widget


def path_bytes(x, y, x_fraction=0, y_fraction=0):
    return struct.pack('<HHHH', x_fraction, x, y_fraction, y)


def payload(player=(20.0, 30.0), live=(7, 0x1000)):
    return {'player': list(player), 'marks': [['leader', 21.0, 30.0]], 'live': list(live) if live else None}


def reader(data, calls=None):
    def read(fd, size, address):
        if calls is not None:
            calls.append((fd, size, address))
        if isinstance(data, Exception):
            raise data
        return data

    return LivePlayer(open_memory=lambda pid: 100 + pid, read=read)


def test_path_bytes_are_whole_world_units_plus_a_fraction_in_tiles():
    assert position(path_bytes(100, 150)) == (20.0, 30.0)
    assert position(path_bytes(101, 150, x_fraction=0x8000)) == (20.3, 30.0)


def test_the_position_is_read_at_the_published_address_of_the_published_process(monkeypatch):
    monkeypatch.setattr('os.close', lambda fd: None)
    calls = []
    live = reader(path_bytes(103, 149), calls)

    assert live.locate(payload()) == (20.6, 29.8)
    assert live.locate(payload()) == (20.6, 29.8)
    assert calls == [(107, 8, 0x1000)] * 2  # one open, reused


def test_the_published_position_stands_without_an_address_or_when_the_read_fails_or_is_far_off(monkeypatch):
    monkeypatch.setattr('os.close', lambda fd: None)

    assert reader(path_bytes(103, 149)).locate(payload(live=None)) is None
    assert reader(OSError('gone')).locate(payload()) is None
    assert reader(path_bytes(4000, 149)).locate(payload()) is None  # another level, or a freed path


def test_only_the_ground_widget_follows_the_live_position():
    ground = Widget('ground', 'ground', 'ground', payload())
    card = Widget('map', 'guide', 'map', {'lines': [], 'map': None})
    boxes = [(ground, (0, 0, 800, 450)), (card, (10, 10, 50, 50))]

    moved = follow(boxes, (21.5, 30.0))

    assert moved[0][0].payload == {**payload(), 'player': [21.5, 30.0]}
    assert moved[0][1] == (0, 0, 800, 450)
    assert moved[1] == boxes[1]
    assert follow(boxes, None) is boxes
    assert ground_payload_of(boxes) == payload()
    assert ground_payload_of(boxes[1:]) is None
