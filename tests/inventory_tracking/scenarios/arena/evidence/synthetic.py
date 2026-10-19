"""Small takes made by hand for the evidence tests: frames, path records and missile records in the
layout takes/record.py writes, with only the bytes the evidence reads filled in.

Nothing here is a game id from memory: modes come from hurts.ATTACK_MODES and layout.DEAD_MODES, the
types from the threat table (one it calls ranged, one it does not), the missile from the bundled
tables' own list.
"""

import json
import struct
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from inventory_tracking.combat.mechanics.tables import MISSILES, tables
from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.native.layout import DEAD_MODES
from inventory_tracking.takes.hurts import ATTACK_MODES, TARGET_UNIT, harmless
from inventory_tracking.takes.takes import Take
from tests.inventory_tracking.scenarios.arena.evidence.blows import (
    MONSTER_KIND,
    OWNER,
    PLAYER_KIND,
    TARGET_KIND,
    ranged_type,
    threats,
)


Point = tuple[float, float]
HERO_UNIT, AREA = 1, 25
STRIKE = min(ATTACK_MODES)  # a monster mode in which it strikes
IDLE = next(mode for mode in range(1, 16) if mode not in ATTACK_MODES and mode not in DEAD_MODES)
DEAD = max(DEAD_MODES)  # lying dead
RATE = 25.0
START = 1000.0
# A melee type and a ranged one by the threat table, both with a monstats row in the bundled tables.
MELEE_TXT = next(
    int(txt) for txt in sorted(threats(), key=int) if not ranged_type(int(txt)) and txt in tables()['monsters']
)
RANGED_TXT = next(
    int(txt) for txt in sorted(threats(), key=int) if ranged_type(int(txt)) and txt in tables()['monsters']
)
NOVA_MISSILE = MISSILES[2]  # `coldunique`: a missile that hurts
OWN_MISSILE = MISSILES[0]  # the character's blade: harmless to it
assert NOVA_MISSILE not in harmless()
assert OWN_MISSILE in harmless()


def place_hex(at: Point) -> str:
    """The head of a missile's path record at a whole world point (hurts.missile_point reads it back)."""
    return struct.pack('<HHHH', 0, int(at[0]), 0, int(at[1])).hex()


def owner_record(kind: int, unit: int) -> str:
    """A missile's unit record with its owner where blows.owner_of looks."""
    return (bytes(OWNER) + struct.pack('<II', kind, unit)).hex()


def target_record(kind: int, unit: int) -> str:
    """A monster's path record naming its target where blows.target_of and hurts.target_unit look."""
    assert TARGET_KIND + 4 == TARGET_UNIT
    return (bytes(TARGET_KIND) + struct.pack('<II', kind, unit)).hex()


def monster(
    unit: int,
    txt: int = MELEE_TXT,
    at: Point = (102.0, 100.0),
    mode: int = IDLE,
    flags: int = 0,
    owner: int = NO_OWNER,
    ally: int = 0,
) -> list[Any]:
    """A frame's row of a monster (takes.MonsterRow)."""
    return [unit, txt, mode, at[0], at[1], 128, 128, flags, owner, ally]


def flying(unit: int, txt: int, at: Point) -> list[Any]:
    """A frame's row of a missile (takes.MissileRow)."""
    return [unit, txt, 0, 0, 0, place_hex(at)]


def frame(
    index: int,
    life: int | None,
    monsters: Sequence[list[Any]] = (),
    missiles: Sequence[list[Any]] = (),
    at: Point = (100.0, 100.0),
    most: int = 1000,
    mode: int = 1,
) -> dict[str, Any]:
    """Frame `index` at RATE frames a second; `life` None: the vitals were not read (0 of 0)."""
    vitals = [0, 0] if life is None else [life, most]
    hero = [HERO_UNIT, mode, AREA, at[0], at[1], 0, 388, *vitals, 400, 500]
    return {'t': START + index / RATE, 'n': index, 'p': hero, 'm': [*monsters], 'x': [*missiles]}


def aims(index: int, *targets: tuple[int, int, int]) -> dict[str, Any]:
    """A row of paths.jsonl at frame `index`: each (monster unit, target kind, target unit)."""
    return {'t': START + index / RATE, 'n': index, 'm': [[unit, target_record(kind, to)] for unit, kind, to in targets]}


def at_hero(index: int, *units: int) -> dict[str, Any]:
    return aims(index, *((unit, PLAYER_KIND, HERO_UNIT) for unit in units))


def born(index: int, unit: int, txt: int, owner: int | None, kind: int = MONSTER_KIND) -> dict[str, Any]:
    """A row of missiles.jsonl: missile `unit` first seen at frame `index`; `owner` None: no record."""
    record = '' if owner is None else owner_record(kind, owner)
    return {'t': START + index / RATE, 'unit_id': unit, 'txt_id': txt, 'record': record}


def take(
    frames: Sequence[dict[str, Any]],
    *,
    paths: Sequence[dict[str, Any]] = (),
    missiles: Sequence[dict[str, Any]] = (),
    units: Sequence[dict[str, Any]] = (),
    name: str = '20261011T120000Z-25',
    schema: int = 2,
) -> Take:
    return Take(Path('/nowhere') / name, {'schema': schema}, [*frames], [], [*units], [*missiles], [*paths])


def write(found: Take, root: Path) -> Path:
    """The take as a directory under `root`, as Take.load reads it."""
    directory = root / found.directory.name
    directory.mkdir(parents=True)
    (directory / 'manifest.json').write_text(json.dumps(found.manifest))
    parts = {'frames': found.frames, 'units': found.units, 'missiles': found.missiles, 'paths': found.paths}
    for part, records in parts.items():
        (directory / f'{part}.jsonl').write_text(''.join(json.dumps(record) + '\n' for record in records))
    return directory
