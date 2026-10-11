"""The scripted game of the macro tests (macros/fakes.py) with a log of when things happened.

Time is the fakes' clock: it only moves when the macro sleeps, so a gap measured here is the pauses
the loop itself makes (naps, pointer steps, key holds), never the cost of a read or a decision. The
wall-clock cost of those is in test_tick_cost.py.
"""

import gzip
import json
import math
import struct
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.combat.takes import Take, monsters_of, player_of
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.model import Ground, Level, Room, Walkable
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.hunt import Hunter, hostiles
from inventory_tracking.macros.world import Monster, Player, Teleport, World
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, KEYS, Game, world


HERE = Room(1, 996, 996, 8, 8)
EAST = tuple(Room(2 + i, 1004 + 8 * i, 996, 8, 8) for i in range(4))
ROOMS = (HERE, *EAST)
STAFF = Teleport(10, 20, True)
CHAMPION = 0x0C
DEATH_MARK_SLOT = HUNT_SLOTS.index(375)
NO_MARK_SLOTS = (*HUNT_SLOTS[:DEATH_MARK_SLOT], None, *HUNT_SLOTS[DEATH_MARK_SLOT + 1 :])  # Death Mark on no key
TICK = 0.04  # one game frame
FIXTURE = Path(__file__).parents[2] / 'combat' / 'fixtures' / 'catacombs-macro'  # a trimmed take of real play
ASPECT = 2560 / 1418


def keys(_world, skills):
    return {skill: KEYS[skill] for skill in skills}


def foe(unit_id, x, y, flags=0, txt_id=19, **changes):
    return Monster(unit_id, txt_id, 1, x, y, 0xFFFFFFFF, flags, **changes)


class Play(Game):
    """`Game` that notes the clock time of each strike, strike-input press and release, pointer move and read."""

    def __init__(self, start: World):
        super().__init__(start)
        self.struck_at: list[tuple[float, int | None]] = []  # (clock, unit hit)
        self.pressed_at: list[tuple[float, int]] = []  # (clock, key code) of every key press
        self.released_at: list[tuple[float, int]] = []
        self.moved_at: list[tuple[float, tuple[int, int]]] = []  # (clock, pointer) of every pointer move
        self.reads: list[float] = []  # clock time of every world read
        press, release, move = self.keys.press, self.keys.release, self.keys.move_pointer

        def noting_press(code):
            self.pressed_at.append((self.clock.now, code))
            return press(code)

        def noting_release(code):
            self.released_at.append((self.clock.now, code))
            return release(code)

        def noting_move(x, y):
            self.moved_at.append((self.clock.now, (x, y)))
            return move(x, y)

        self.keys.press, self.keys.release, self.keys.move_pointer = noting_press, noting_release, noting_move

    def strike(self):
        before = len(self.strikes)
        super().strike()
        self.struck_at += [(self.clock.now, unit) for unit, _ in self.strikes[before:]]

    def read(self):
        if not self.reading:
            self.reads.append(self.clock.now)
        return super().read()

    def strike_presses(self) -> list[float]:
        """Clock times the Echoing Strike key went down."""
        code = self.keys.names.get(KEYS[388])
        return [at for at, pressed in self.pressed_at if pressed == code]

    def strike_releases(self) -> list[float]:
        code = self.keys.names.get(KEYS[388])
        return [at for at, released in self.released_at if released == code]


def game(*monsters, **changes) -> Play:
    changes.setdefault('area', 101)
    changes.setdefault('slots', HUNT_SLOTS)
    play = Play(world(monsters=tuple(monsters), **changes))
    play.staff = STAFF
    return play


def hunter(play, *, ground=(), remembered=(), policy=None) -> Hunter:
    def level():
        return Level(play.world.player.area, ROOMS, tuple(ground))

    return Hunter(level, lambda area: list(remembered), None, policy)


def attack_mode(play, hunt, *, until=30.0, events=()):
    """Run attack mode with `events` ((seconds, callable)) happening meanwhile; cancelled at `until`."""
    run = play.run()
    run.actuator.drift, run.actuator.steady = 10**6, False  # as the runner sets them for the mode
    for at, event in events:
        play.arrivals.append((at, event))
    play.arrivals.append((until, run.cancelled.set))
    play.arrivals.sort(key=lambda pair: pair[0])
    with pytest.raises(Abort, match='cancelled'):
        hunt.attack_mode(run, keys)
    return run


def appear(play, *monsters):
    return lambda: setattr(play, 'world', replace(play.world, monsters=(*play.world.monsters, *monsters)))


def vanish(play, *units):
    """The monsters leave memory (walked off, unloaded): gone, not killed."""
    return lambda: setattr(
        play, 'world', replace(play.world, monsters=tuple(m for m in play.world.monsters if m.unit_id not in units))
    )


def left_click(play, at, seconds=0.08, pixel=(3400, 900)):
    """The player's own left click as an `attack_mode` event (as test_hunt.py): the button is down from
    clock `at` for `seconds` with the pointer at `pixel`; the fake game takes none of it."""

    def state():
        if at - 0.05 <= play.clock.now < at + seconds:
            play.keys.at = pixel
        down = at <= play.clock.now < at + seconds
        return (*play.keys.at, 1 << 8 if down else 0)

    play.keys.pointer_state = state
    play.keys.pointer = lambda: state()[:2]
    return (at, lambda: None)


# --- recorded play (the checked-in trim of a Catacombs take) ---


def recorded() -> tuple[Take, Ground, tuple[Room, ...], tuple[Walkable, ...]]:
    take = Take.load(FIXTURE)
    with gzip.open(FIXTURE / 'level.json.gz', 'rt', encoding='utf-8') as handle:
        level = json.load(handle)
    grids = tuple(Walkable(**grid) for grid in level.get('ground', ()))
    rooms = tuple(Room(r['preset'], r['x'], r['y'], r['width'], r['height']) for r in level['rooms'])
    return take, Ground(grids), rooms, grids


def busiest_frame(take: Take) -> dict:
    """The frame with the most live hostiles."""
    return max((f for f in take.frames if f.get('p')), key=lambda f: sum(m.hostile for m in monsters_of(f)))


def recorded_world(frame: dict, count: int | None = None) -> World:
    """The frame as the macro's `World`. With `count`, that many hostiles: the frame's own, the nearest
    first, and when it has fewer, the same pack again on rings 6 to 26 units around the character
    (synthetic: the Catacombs takes never held more than 36 in sight)."""
    row = player_of(frame)
    assert row is not None
    stand = Player(row.unit, 'CybergrindAA', 1, row.area, row.x, row.y, False, right_skill=388)
    live = [
        Monster(m.unit, m.txt, m.mode, m.x, m.y, m.owner, m.flags, bool(m.ally), m.life, m.max_life)
        for m in monsters_of(frame)
        if m.alive
    ]
    doors = tuple(Door(d[0], d[1], d[2], float(d[3]), float(d[4])) for d in frame.get('d', ()))
    seen = World(True, (), 'recorded', (), player=stand, monsters=tuple(live), doors=doors)
    if count is None:
        return seen
    here = (stand.x, stand.y)
    foes = sorted(hostiles(seen), key=lambda m: math.dist(here, (m.x, m.y)))
    pack = []
    for index in range(count):
        source = foes[index % len(foes)]
        away = 6.0 + (index * 37 % 200) / 10
        angle = 2 * math.pi * (index * 0.618 % 1.0)
        at = (source.x, source.y) if index < len(foes) and math.dist(here, (source.x, source.y)) <= 26 else None
        x, y = at or (here[0] + away * math.cos(angle), here[1] + away * math.sin(angle))
        pack.append(replace(source, unit_id=10_000 + index, x=x, y=y))
    return replace(seen, monsters=(*pack, *(m for m in live if m.ally or m.owner != 0xFFFFFFFF)))


# --- a counted memory (no game): what one look costs in reads ---


class CountedMemory:
    """Blocks of bytes at addresses, as tests/inventory_tracking/macros/test_world.py, counting the reads."""

    def __init__(self) -> None:
        self.blocks: dict[int, bytearray] = {}
        self.reads: list[tuple[int, int]] = []  # (address, size)

    def block(self, address: int, size: int) -> bytearray:
        self.blocks[address] = bytearray(size)
        return self.blocks[address]

    def read(self, address: int, size: int) -> bytes:
        self.reads.append((address, size))
        for start, data in self.blocks.items():
            if start <= address and address + size <= start + len(data):
                return bytes(data[address - start : address - start + size])
        raise ValueError(f'unmapped range at {address:#x}')


def skill_table(slots) -> bytes:
    """The game's skill slot table holding `slots` (world.decode_slots reads it)."""
    return b''.join(struct.pack('<7I', 0xFFFFFFFF if s is None else s, 0xFFFFFFFF, 0, 4, 255, 0, 0) for s in slots)


def monster_table(memory: CountedMemory, table: int, count: int) -> None:
    """`count` live hostile monsters (128 at most: one a bucket) in the unit table at `table`, each with a
    path, monster data and a stat list holding life 90 of 128."""
    heads = memory.block(table + 1024, 1024)
    for index in range(count):
        unit_id = 128 * 7 + index
        address, data, path, stats = (base + index * 0x400 for base in (0x700000, 0x800000, 0x900000, 0xA00000))
        header = memory.block(address, 0x160)
        struct.pack_into('<IIII', header, 0, 1, 19, unit_id, 1)
        struct.pack_into('<Q', header, 0x10, data)
        struct.pack_into('<Q', header, 0x38, path)
        struct.pack_into('<Q', header, 0x88, stats)
        struct.pack_into('<I', memory.block(data, 0x80), 84, 0xFFFFFFFF)  # no owner
        struct.pack_into('<HHHH', memory.block(path, 0x28), 0, 0, 5010 + index, 0, 5020)
        struct.pack_into('<QQ', memory.block(stats, 0x100), 0xE8, stats + 0x200, 2)
        values = memory.block(stats + 0x200, 0x100)
        struct.pack_into('<HHi', values, 0, 0, 6, 90 << 8)
        struct.pack_into('<HHi', values, 8, 0, 7, 128 << 8)
        struct.pack_into('<Q', heads, (unit_id % 128) * 8, address)
