"""Readers of what a schema 4 take holds raw (combat/record.py): the unit records of `records.jsonl`, the
path records of `paths.jsonl` and the missiles' first sights, by the offsets the client's code gives
(rca/2026-10-13/re-findings.md, "What to decode from the raw bytes now on record" and the fourth and fifth
pass). Nothing in the production code reads these yet; this is the decode step the replay of a take needs
(replay.py: the seal bosses by their superuniques row) and the inventory of
rca/2026-10-13/replay-readiness.md counts with.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.records4 <take directory> ...
"""

import struct
import sys
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from inventory_tracking.combat.takes import Take, carried, monsters_of, player_of, records


UNIT_RECORD = 0x1C0  # bytes of a unit record in a row; a monster's 0x58 of monster data follow
MONSTER_DATA = 0x58
SUPER_UNIQUE = 0x02  # monster data +0x1A: the type flags (2 super unique, 8 unique, 0x10 minion)
# superuniques.txt rows of the Chaos Sanctuary's seal bosses, read from pricing/raw/game-excel (2026-10-13,
# rows 36 to 38 of the file) and seen at monster data +0x2A of the three bosses of take 20261013T093331Z-108.
# The names are the routes' (routes/catalog) and the elite table's.
SEAL_BOSSES = {36: 'Infector of Souls', 37: 'Lord De Seis', 38: 'Grand Vizier of Chaos'}
PLAYER_TYPE, MONSTER_TYPE = 0, 1


@dataclass(frozen=True)
class Unit:
    """One row of `records.jsonl` read: the animation as the record has it live and as of the last whole
    tick, the cast counter, a monster's type flags and boss row, the skill in use (None: not striking)."""

    unit: int
    kind: int  # 0 the character, 1 a monster
    txt: int
    frame: float  # +0x5C, frames
    length: float  # +0x64, frames
    speed: float  # +0x68, frames a tick
    tick_valid: bool  # +0x18C
    tick_frame: float  # +0x19C
    tick_length: float  # +0x1A4
    event: int  # +0x1A8: the frame flag crossed in the last whole tick
    counter: int  # +0x12C
    flags: int | None  # monster data +0x1A
    boss: int | None  # monster data +0x2A when the flags say super unique
    skill: int | None  # the skill in use: its skills.txt row
    skill_level: int | None  # the skill record's +0x38

    @property
    def sound(self) -> bool:
        """The animation fields make sense: a length, and a frame within it."""
        return 0 < self.length <= 0x90 and 0 <= self.frame < self.length + 1


def unit_of(row: list) -> Unit:
    """One `[unit, record, states, skill]` of a `records.jsonl` row."""
    raw = bytes.fromhex(row[1])
    skill = bytes.fromhex(row[3]) if len(row) > 3 and row[3] else b''
    u32 = lambda at: struct.unpack_from('<I', raw, at)[0]  # noqa: E731
    flags = boss = None
    if len(raw) >= UNIT_RECORD + MONSTER_DATA:
        data = raw[UNIT_RECORD:]
        flags = struct.unpack_from('<H', data, 0x1A)[0]
        boss = struct.unpack_from('<h', data, 0x2A)[0] if flags & SUPER_UNIQUE else None
    return Unit(
        unit=row[0],
        kind=u32(0x00),
        txt=u32(0x04),
        frame=u32(0x5C) / 256,
        length=u32(0x64) / 256,
        speed=struct.unpack_from('<h', raw, 0x68)[0] / 256,
        tick_valid=raw[0x18C] == 1,
        tick_frame=u32(0x19C) / 256,
        tick_length=u32(0x1A4) / 256,
        event=raw[0x1A8],
        counter=u32(0x12C),
        flags=flags,
        boss=boss,
        skill=struct.unpack_from('<H', skill, 0)[0] if len(skill) >= 2 else None,
        skill_level=struct.unpack_from('<I', skill, 2 + 0x38)[0] if len(skill) >= 2 + 0x3C else None,
    )


def units(directory: Path) -> Iterator[tuple[float, Unit]]:
    """(the row's time, the unit read) for every unit of every row of a take's `records.jsonl`."""
    for row in records(directory):
        for found in row['u']:
            yield row['t'], unit_of(found)


def bosses(directory: Path) -> dict[int, str]:
    """The seal bosses of a take by unit id: the monsters whose monster data names a superuniques row of
    SEAL_BOSSES. (kp4.py had them by hand, from the type flags and the log.)"""
    found: dict[int, str] = {}
    for _, unit in units(directory):
        if unit.boss in SEAL_BOSSES:
            found[unit.unit] = SEAL_BOSSES[unit.boss]
    return found


def target_of(path: str) -> tuple[int, int] | None:
    """(unit type, unit id) of the unit a path record names as its target (+0x78, +0x7C); None: none, or a
    record cut short of them."""
    raw = bytes.fromhex(path)
    if len(raw) < 0x80:
        return None
    kind, unit = struct.unpack_from('<II', raw, 0x78)
    return None if not kind and not unit else (kind, unit)


@dataclass(frozen=True)
class Shot:
    """A missile at its first sight (`missiles.jsonl`): who let it go, with what skill at what level, and
    the cast counter its unit record keeps (+0x12C)."""

    unit: int
    txt: int
    owner_type: int
    owner: int
    skill: int | None
    level: int | None
    counter: int


def shot_of(row: dict) -> Shot:
    record = bytes.fromhex(row['record'])
    data = bytes.fromhex(row.get('data') or '')
    owner_type, owner = struct.unpack_from('<II', record, 0xE8)
    skill, level = struct.unpack_from('<HH', data, 0x0C) if len(data) >= 0x10 else (None, None)
    return Shot(
        row['unit_id'], row['txt_id'], owner_type, owner, skill, level, struct.unpack_from('<I', record, 0x12C)[0]
    )


def inventory(directory: Path) -> dict[str, object]:
    """What of a take decodes, in numbers: the report's table is made of these."""
    take = Take.load(directory)
    first = player_of(take.frames[0])
    hero = first.unit if first is not None else -1
    hostile, mates, txt = set(), set(), {}
    for frame in take.frames:
        for row in monsters_of(frame):
            txt[row.unit] = row.txt
            (mates if row.ally or row.owner != 0xFFFFFFFF else hostile).add(row.unit)
    rows = sound = valid = tick_sound = 0
    seen, skills, with_boss = set(), Counter(), {}
    for _, unit in units(directory):
        rows += 1
        seen.add(unit.unit)
        sound += unit.sound
        valid += unit.tick_valid
        tick_sound += unit.tick_valid and unit.tick_length == unit.length and unit.tick_frame < unit.length + 1
        if unit.skill is not None and unit.kind == MONSTER_TYPE:
            skills[(unit.txt, unit.skill, unit.skill_level)] += 1
        if unit.boss is not None:
            with_boss[unit.unit] = (unit.txt, unit.boss)
    targets = Counter()
    for row in take.paths:
        for unit, path in row['m']:
            if unit not in hostile:
                continue
            found = target_of(path)
            if found is None:
                targets['none'] += 1
            elif found == (PLAYER_TYPE, hero):
                targets['the character'] += 1
            elif found[0] == MONSTER_TYPE and found[1] in mates:
                targets['a companion'] += 1
            else:
                targets['other'] += 1
    owners, levels, groups = Counter(), Counter(), Counter()
    for row in take.missiles:
        shot = shot_of(row)
        mine = shot.owner_type == PLAYER_TYPE and shot.owner == hero
        who = (
            'the character'
            if mine
            else 'a companion'
            if shot.owner in mates
            else 'a hostile'
            if shot.owner in hostile
            else 'unknown'
        )
        owners[who] += 1
        levels['skill and level' if shot.skill else 'no skill (an effect)'] += 1
        if mine:
            groups[shot.counter] += 1
    keys = {key: sum(1 for value in carried(take, key) if value is None) for key in 'rswbfgio'}
    return {
        'take': directory.name,
        'frames': len(take.frames),
        'frames without the character': sum(1 for frame in take.frames if not frame.get('p') or not frame['p'][8]),
        'frames before each key is first written': keys,
        'record rows': rows,
        'units with a record': f'{len(seen)} of {len(txt) + 1}',
        'animation sound': f'{sound} of {rows}',
        'tick copy valid': f'{valid} of {rows}',
        'tick copy sound': f'{tick_sound} of {valid}',
        'bosses (unit: txt, superuniques row)': with_boss,
        'monster skills in use (txt, skill, level): rows': dict(sorted(skills.items())),
        'path targets of hostiles, by row': dict(targets),
        'missile owners': dict(owners),
        'missiles': dict(levels),
        'own casts by counter': f'{len(groups)} groups of {sum(groups.values())} missiles',
        'events': dict(Counter(event['event'] for event in take.events)),
    }


if __name__ == '__main__':
    for name in sys.argv[1:]:
        for key, value in inventory(Path(name)).items():
            print(f'{key}: {value}')
        print()
