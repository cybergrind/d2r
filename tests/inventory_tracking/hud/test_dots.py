"""The canvas reads every monster dot itself (rca/2026-10-14/run-1916-hud-findings.md §2)."""

import ctypes
import errno
import struct

from inventory_tracking.hud.dots import (
    HELD_TILES,
    UNIT_RECORD,
    WALK_SECONDS,
    DotStats,
    LiveDots,
)
from inventory_tracking.hud.live import follow
from inventory_tracking.hud.scene import Widget
from inventory_tracking.native.memory import vm_read_spans
from inventory_tracking.terror.monsters import Monster
from inventory_tracking.terror.tracker import ALIGNMENT_STAT, HELD_RANGE


PLAYER = 0x1000
TABLE = 0x9000


def record(uid, mode=2, path=0, kind=1):
    raw = bytearray(UNIT_RECORD)
    struct.pack_into('<IIII', raw, 0, kind, 7, uid, mode)
    struct.pack_into('<Q', raw, 0x38, path)
    return bytes(raw)


def path_bytes(x_tiles, y_tiles):
    return struct.pack('<HHHH', 0, round(x_tiles * 5), 0, round(y_tiles * 5))


class Memory(dict):
    """address -> bytes; any other address is unreadable, as /proc/pid/mem says."""

    def read(self, fd, size, address):
        data = self.get(address)
        if data is None:
            raise OSError(errno.EIO, 'unmapped')
        return data[:size]


def dots(memory, walk=None, stats=None):
    return LiveDots(
        open_memory=lambda pid: 3,
        read=memory.read,
        call=None,
        walk=walk or (lambda read, table, known: ([], True)),
        stats=stats or DotStats(log=lambda *a: None),
    )


def card(*rows, units=None):
    return {'player': [20.0, 30.0], 'live': [7, PLAYER], 'pois': [list(row) for row in rows], 'units': units}


def row(uid, x, y, kind='mob'):
    return ['monster', kind, x, y, 0x5000 + uid, 0x6000 + uid, uid]


def test_each_dot_is_where_its_unit_is_now_and_a_dead_one_goes_at_once():
    memory = Memory({PLAYER: path_bytes(20, 30)})
    memory[0x6001], memory[0x5001] = record(1, path=0x5001), path_bytes(22, 31)
    memory[0x6002] = record(2, mode=12, path=0x5002)  # dead
    reader = dots(memory)

    moved = reader.frame(card(row(1, 21.0, 30.0), row(2, 25.0, 30.0)), None, 100.0)

    assert moved is not None
    assert moved['player'] == [20.0, 30.0]
    assert moved['dots'] == {1: [22.0, 31.0], 2: None}


def test_a_freed_record_keeps_its_dot_out_of_range_and_drops_it_where_the_client_would_hold_it():
    assert HELD_TILES == HELD_RANGE / 5
    memory = Memory({PLAYER: path_bytes(20, 30)})
    memory[0x6001] = record(99, path=0x5001)  # reused by another unit
    far, near = row(1, 20.0 + HELD_TILES + 4, 30.0), row(2, 21.0, 30.0)
    memory[0x6002] = record(2, kind=4)  # not a monster any more

    moved = dots(memory).frame(card(far, near), None, 100.0)

    assert moved is not None
    assert moved['dots'] == {1: [far[2], 30.0], 2: None}


def test_new_hostiles_come_from_the_canvas_walk_and_allies_never_do():
    from inventory_tracking.terror.tracker import BARRICADES

    memory = Memory({PLAYER: path_bytes(20, 30)})
    for uid in (1, 5, 6, 7):
        memory[0x6000 + uid], memory[0x5000 + uid] = record(uid, path=0x5000 + uid), path_bytes(24, 30)
    plain = 'ff' * 0x1A + '00' + '00' * 0x40
    held = [
        Monster(5, 300, 2, 120, 150, 108, None, plain, (), (), path=0x5005, unit=0x6005),  # new: a dot
        Monster(6, 300, 2, 120, 150, 108, None, plain, ((0, ALIGNMENT_STAT, 1),), (), path=0x5006, unit=0x6006),
        Monster(7, min(BARRICADES), 2, 120, 150, 108, None, plain, (), (), path=0x5007, unit=0x6007),
        Monster(1, 300, 2, 120, 150, 108, None, plain, (), (), path=0x5001, unit=0x6001),  # on the card already
        Monster(8, 300, 12, 120, 150, 108, None, plain, (), (), path=0x5008, unit=0x6008),  # dead
        Monster(9, 300, 2, 120, 150, 40, None, plain, (), (), path=0x5009, unit=0x6009),  # another level
    ]
    walks = []

    def walk(read, table, known):
        walks.append((table, set(known)))
        return held, True

    reader = dots(memory, walk)
    shown = card(row(1, 24.0, 30.0), units=[TABLE, 108])

    moved = reader.frame(shown, None, 100.0)
    assert moved is not None
    assert [r[:4] + r[5:] for r in moved['extra']] == [['monster', 'mob', 24.0, 30.0, 0x6005, 5]]
    reader.frame(shown, None, 100.0 + WALK_SECONDS / 2)
    reader.frame(shown, None, 100.0 + WALK_SECONDS)
    assert walks == [(TABLE, set()), (TABLE, {5, 6, 7, 1, 8, 9})]  # each first sight is judged once

    # The card brings it: it is the card's dot from then on.
    moved = reader.frame(card(row(1, 24.0, 30.0), row(5, 24.0, 30.0), units=[TABLE, 108]), None, 100.1)
    assert moved is not None
    assert moved['extra'] == []
    assert moved['dots'][5] == [24.0, 30.0]


def test_follow_moves_the_map_dots_and_the_ground_marks_and_adds_the_new():
    shown = card(row(1, 21.0, 30.0), row(2, 25.0, 30.0, 'leader'), ['Cave', 'stairs', 40.0, 40.0])
    ground = {'player': [20.0, 30.0], 'marks': [r[1:] for r in shown['pois'][1:]], 'live': [7, PLAYER]}
    boxes = [
        (Widget('ground', 'ground', 'ground', ground), (0, 0, 800, 450)),
        (Widget('map', 'guide', 'map', {'lines': [], 'map': {'map': shown}}), (0, 0, 400, 300)),
    ]
    new = ['unique', 'leader', 30.0, 30.0, 0, 0x6009, 9]
    moved = {'player': [20.5, 30.0], 'dots': {1: [22.0, 31.0], 2: None}, 'extra': [new]}

    ground_now, map_now = (widget.payload for widget, _ in follow(boxes, None, moved))

    assert map_now['map']['map']['player'] == [20.5, 30.0]
    assert map_now['map']['map']['pois'] == [row(1, 22.0, 31.0), ['Cave', 'stairs', 40.0, 40.0], new]
    assert ground_now['marks'] == [['stairs', 40.0, 40.0], new[1:]]


def test_a_batched_read_skips_the_span_it_stopped_at_and_asks_the_rest_again():
    memory = {0x100: b'AAAA', 0x300: b'CCCC'}
    calls = []

    def call(pid, local, count, remote, remote_count, flags):
        spans = [(remote[i].iov_base, remote[i].iov_len) for i in range(remote_count)]
        calls.append([address for address, _ in spans])
        done = b''
        for address, size in spans:
            if address not in memory:
                break
            done += memory[address][:size]
        if not done:
            ctypes.set_errno(errno.EFAULT)
            return -1
        ctypes.memmove(local._obj.iov_base, done, len(done))
        return len(done)

    assert vm_read_spans(call, 7, [(0x100, 4), (0x200, 4), (0x300, 4)]) == [b'AAAA', None, b'CCCC']
    assert calls == [[0x100, 0x200, 0x300], [0x300]]

    def refused(*args):
        ctypes.set_errno(errno.EPERM)
        return -1

    assert vm_read_spans(refused, 7, [(0x100, 4)]) is None


def test_a_refused_batch_reads_one_pread_each_from_then_on():
    memory = Memory({0x100: b'AAAA'})
    reader = dots(memory)

    def refused(*args):
        ctypes.set_errno(errno.EPERM)
        return -1

    reader.call = refused
    reader.attach(7)

    assert reader.spans([(0x100, 4), (0x200, 4)]) == [b'AAAA', None]
    assert reader.call is None


def test_the_stats_line_says_who_saw_a_monster_first_and_how_much_later_the_card_was():
    lines = []
    stats = DotStats(every=60.0, log=lambda text, *args: lines.append(text % args))
    stats.framed(0.0, {}, {}, {}, 0.3, 10)
    stats.walked(0.1, 2.0, {5: []})
    stats.drew(0.12, 4.0)
    stats.framed(0.2, {}, {}, {}, 0.3, 10)
    stats.framed(1.9, {5: (), 6: ()}, {5: [1.0, 2.0], 6: None}, {}, 0.4, 12)  # the card brings 5; 6 read dead
    stats.drew(1.92, 4.5)
    stats.framed(3.9, {5: ()}, {5: [1.0, 2.0]}, {}, 0.4, 12)  # the card drops 6
    stats.framed(61.0, {5: ()}, {5: [1.0, 2.0]}, {}, 0.4, 12)

    [line] = lines
    assert line.startswith('HUD: dots: 2 new in 61 s (1 first by the walk, 1 by the card)')
    assert 'card later than the walk by 1.80 s median' in line
    assert '1 deaths read by the frame, card dropped them 2.00 s median' in line
    assert 'had→painted 0.02 s median' in line


def test_the_card_carries_each_dots_unit_and_the_table_to_the_canvas():
    from inventory_tracking.hud.ground import ground_payload
    from inventory_tracking.hud.live import map_card_of
    from inventory_tracking.levels.map_card import MapCard, MapPoi

    dot = MapPoi('unique', 'leader', 21.0, 30.0, 0x5001, 0x6001, 1)
    card = MapCard(((0, 0, 8, 8),), (20.0, 30.0), (dot, MapPoi('Cave', 'stairs', 4.0, 4.0)), units=(TABLE, 108))
    payload = card.to_payload()

    assert MapCard.from_payload(payload) == card
    shown = map_card_of([(Widget('map', 'guide', 'map', {'lines': [], 'map': payload}), (0, 0, 1, 1))])
    assert shown is not None
    assert shown['pois'][0] == ['unique', 'leader', 21.0, 30.0, 0x5001, 0x6001, 1]
    assert shown['units'] == [TABLE, 108]
    ground = ground_payload(card)
    assert ground is not None
    assert ground['marks'] == [['leader', 21.0, 30.0, 0x5001, 0x6001, 1], ['stairs', 4.0, 4.0]]
