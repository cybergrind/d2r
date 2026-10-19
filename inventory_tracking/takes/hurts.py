"""What took the character's life: every drop of it, with who was striking and what flew by.

The recorder writes a `hurt` event at each drop (takes/record.py), and `hurts` derives the same rows
from a take recorded before it did, so that the size of a blow can be laid against the type, the
rank and the enchantments of whoever dealt it (user, 2026-10-12: "we need to record such things and
use it in our threat calculation and tests"). A row:

- `lost`, `life`, `max_life`: the points gone between two frames, what is left and of how many;
  `dead` when nothing is;
- `by`: the suspects, nearest first, each `[unit, txt, flags, mode, distance, aimed, mods]`: a
  hostile within SUSPECT_REACH that is in an attack mode or whose path record names the character
  as its target (`aimed`: 1, 0, or None without a path record), and anything within BESIDE. `mods`
  are its enchantments (monumod ids), None when not known;
- `near`: the missiles within MISSILE_REACH that can hurt, `[txt, distance]`: not the character's own
  and not those that collide with nothing and carry no damage (blood, ice breaking, a sigil's mark:
  mechanics/tables.py `harmless_missiles`).

A row does not say who dealt the blow. `sole` picks the rows where one monster alone was striking
(beside the character or aimed at it) and nothing flew by: those are what a blow's size is fitted on.

    uv run --offline python -m inventory_tracking.takes.hurts [take directories ...]

prints the drops of the takes (default: all under runs/combat) by the rank and enchantment of the one
that struck alone. A take from before 2026-10-12 does not hold the enchantments: they are then looked
up in the terror probe logs of the same hours (runs/alt-d/*/terror-probe.jsonl, `--probe`).
"""

import argparse
import json
import math
import struct
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.game.layout import LEADER_FLAGS, MINION_FLAG, MODIFIERS, NO_OWNER
from inventory_tracking.native.layout import DEAD_MODES


Point = tuple[float, float]
# Monster modes in which it strikes: attack 1 and 2, cast, skills 1-4, sequence (monmode.txt).
ATTACK_MODES = frozenset((4, 5, 7, 8, 9, 10, 11, 14))
TARGET_UNIT = 0x7C  # path record: the unit id of the target (combat/plan.md, the Tower Cellar 5 take)
HURT_LEAST = 5  # points: a smaller drop is not written
SUSPECT_REACH = 12.0  # units: a striker or one aimed at the character this near is a suspect
BESIDE = 4.5  # units: whatever stands this near is one too
MISSILE_REACH = 3.0  # units from the character a missile is listed within
LIGHTNING, FIRE, COLD, STRONG = 17, 9, 18, 5  # monumod ids
ENCHANTMENTS = {LIGHTNING: 'lightning enchanted', FIRE: 'fire enchanted', COLD: 'cold enchanted', STRONG: 'strong'}


@dataclass(frozen=True)
class Foe:
    """A hostile monster as a frame shows it."""

    unit: int
    txt: int
    flags: int
    mode: int
    x: float
    y: float
    target: int | None = None  # the unit its path record names; None without a record
    mods: tuple[int, ...] | None = None  # None: not known


def target_unit(path: bytes) -> int | None:
    return struct.unpack_from('<I', path, TARGET_UNIT)[0] if len(path) >= TARGET_UNIT + 4 else None


def missile_point(path: str) -> Point:
    """Where a missile is, from the head of its path record as a frame holds it (hex)."""
    part_x, x, part_y, y = struct.unpack_from('<HHHH', bytes.fromhex(path[:16]))
    return x + part_x / 65536, y + part_y / 65536


def suspects(character: int, at: Point, foes: Iterable[Foe]) -> list[list[Any]]:
    """The `by` of a row: of each unit the nearest sight in `foes` (the frames around the drop)."""
    found: dict[int, tuple[bool, float, list[Any]]] = {}
    for foe in foes:
        away = math.dist((foe.x, foe.y), at)
        aimed = None if foe.target is None else int(foe.target == character)
        striking = foe.mode in ATTACK_MODES
        if away > BESIDE and not (away <= SUSPECT_REACH and (striking or aimed)):
            continue
        mods = None if foe.mods is None else [*foe.mods]
        kept = found.get(foe.unit)
        # A striking sight is kept over a nearer one that is not: the blow came from the swing.
        if kept is None or (striking, -away) > (kept[0], -kept[1]):
            found[foe.unit] = (striking, away, [foe.unit, foe.txt, foe.flags, foe.mode, round(away, 1), aimed, mods])
    return [row for _striking, _away, row in sorted(found.values(), key=lambda kept: kept[1])]


@cache
def harmless() -> frozenset[int]:
    return frozenset(tables()['harmless_missiles'])


def beside(at: Point, missiles: Iterable[tuple[int, Point]]) -> list[list[Any]]:
    """The `near` of a row, from (txt, point) of the missiles in flight."""
    found = [[txt, round(math.dist(point, at), 1)] for txt, point in missiles if txt not in harmless()]
    return sorted((row for row in found if row[1] <= MISSILE_REACH), key=lambda row: row[1])


def row(lost: int, life: int, max_life: int, by: list[list[Any]], near: list[list[Any]]) -> dict[str, Any]:
    return {'lost': lost, 'life': life, 'max_life': max_life, 'dead': life <= 0, 'by': by, 'near': near}


def lost(life_before: int, most_before: int, life: int, most: int) -> int:
    """The points a blow took between two frames. When the most the life can be fell with it (a buff
    ran out, the other weapons were taken), the life is first brought down in the same proportion and
    that is no blow: of 34 drops in five takes of 2026-10-12 the largest two were Consume ending, 1818
    of 1818 to 1580 of 1580 and 1612 of 1783 to 1392 of 1540. Not at a death: it ends the buffs itself
    (Tower Cellar 5: 1051 of 1783 to 0 of 1540), and the whole life was the blow's."""
    if life <= 0 or most >= most_before or not most_before:
        return life_before - life
    return round(life_before * most / most_before) - life


def rank(flags: int) -> str:
    if flags & MINION_FLAG:
        return 'minion'
    return 'leader' if flags & LEADER_FLAGS else 'plain'


def sole(hurt: Mapping[str, Any]) -> list[Any] | None:
    """The one suspect of a drop that was striking, beside the character or with it as its target, with
    no missile near: the monster the blow can be put on. None when there is none or more than one.
    (A swing lands from further off than it looks: the Herald of Tower Cellar 5 took 210 points
    swinging 7.7 units away, with nothing else striking.)"""
    if hurt['near']:
        return None
    striking = [s for s in hurt['by'] if s[3] in ATTACK_MODES and (s[4] <= BESIDE or s[5])]
    return striking[0] if len(striking) == 1 else None


def hurts(take: Any, mods: Mapping[int, Sequence[int]] | None = None) -> list[dict[str, Any]]:
    """The rows of a take (takes/takes.py `Take`), each with its frame's `t`. Enchantments from the
    take's units when it holds them, else from `mods` (unit id -> monumod ids)."""
    known: dict[int, tuple[int, ...]] = {unit: tuple(found) for unit, found in (mods or {}).items()}
    known.update((unit['unit'], tuple(unit['mods'])) for unit in take.units if 'mods' in unit)
    targets: dict[int, int | None] = {}
    paths, taken = take.paths, 0
    found: list[dict[str, Any]] = []
    before: dict[str, Any] | None = None
    for frame in take.frames:
        while taken < len(paths) and paths[taken]['t'] <= frame['t']:
            for unit, record in paths[taken]['m']:
                targets[unit] = target_unit(bytes.fromhex(record[: 2 * (TARGET_UNIT + 4)]))
            taken += 1
        character = frame.get('p')
        if not character or len(character) < 9 or not character[8]:
            before = None
            continue
        fell = 0 if before is None else lost(before['p'][7], before['p'][8], character[7], character[8])
        if before is not None and before['p'][0] == character[0] and fell >= HURT_LEAST:
            at = (before['p'][3], before['p'][4])
            foes = [
                Foe(m[0], m[1], m[7], m[2], m[3], m[4], targets.get(m[0]), known.get(m[0]))
                for sight in (before, frame)
                for m in sight['m']
                if not m[9] and m[8] == NO_OWNER and m[2] not in DEAD_MODES
            ]
            flying = [(x[1], missile_point(x[5])) for x in before['x']]
            hurt = row(fell, character[7], character[8], suspects(character[0], at, foes), beside(at, flying))
            found.append({'t': frame['t'], **hurt})
        before = frame
    return found


Sightings = dict[int, list[tuple[float, int, tuple[int, ...]]]]
SAME_GAME = 1800.0  # seconds between a probe log's sight of a unit and a take's start for it to be that unit


def sightings(logs: Iterable[Path]) -> Sightings:
    """unit id -> (clock, txt, enchantments) of each first sight in the terror probe logs."""
    found: Sightings = {}
    for log in logs:
        with log.open(encoding='utf-8') as handle:
            for line in handle:
                if '"seen"' not in line or 'data_hex' not in line:
                    continue
                event = json.loads(line)
                data = bytes.fromhex(event.get('data_hex') or '')
                if len(data) >= MODIFIERS.stop and event.get('txt_id') is not None:
                    seen = (event['t'], event['txt_id'], tuple(mod for mod in data[MODIFIERS] if mod))
                    found.setdefault(event['unit_id'], []).append(seen)
    return found


def enchantments(seen: Sightings, take: Any) -> dict[int, tuple[int, ...]]:
    """The enchantments of a take's units by the probe logs: the sight of the same unit and type nearest
    the take's start (a unit id comes back in another game)."""
    start = take.frames[0]['t'] if take.frames else 0.0
    found = {}
    for unit in take.units:
        same = [s for s in seen.get(unit['unit'], ()) if s[1] == unit['txt'] and abs(s[0] - start) <= SAME_GAME]
        if same:
            found[unit['unit']] = min(same, key=lambda sight: abs(sight[0] - start))[2]
    return found


def spread(values: Sequence[float]) -> str:
    ordered = sorted(values)
    half, most = ordered[len(ordered) // 2], ordered[min(len(ordered) - 1, int(0.9 * len(ordered)))]
    return f'{len(ordered):5d} {half:6.0f} {most:6.0f} {ordered[-1]:6.0f}'


def report(rows: Sequence[Mapping[str, Any]]) -> str:
    groups: dict[tuple[str, str], list[int]] = {}
    alone = 0
    for hurt in rows:
        suspect = sole(hurt)
        if suspect is None:
            continue
        alone += 1
        found = suspect[6]
        what = 'not known' if found is None else next((ENCHANTMENTS[m] for m in ENCHANTMENTS if m in found), 'none')
        groups.setdefault((rank(suspect[2]), what), []).append(hurt['lost'])
    lines = [
        f'{len(rows)} drops, {sum(1 for hurt in rows if hurt["dead"])} deaths, {alone} with one monster striking alone',
        f'{"rank, enchantment":34}    n    p50    p90    max',
    ]
    lines += [f'{" ".join(key):34}{spread(lost)}' for key, lost in sorted(groups.items())]
    return '\n'.join(lines)


def main(argv=None) -> int:
    from inventory_tracking.takes.takes import Take

    parser = argparse.ArgumentParser(description="The drops of the character's life in the takes, by who struck.")
    runs = Path(__file__).resolve().parents[1] / 'runs'
    parser.add_argument('takes', nargs='*', type=Path, help='take directories (default: all under runs/combat)')
    parser.add_argument(
        '--probe', nargs='*', type=Path, default=sorted((runs / 'alt-d').glob('*/terror-probe.jsonl')),
        help='terror probe logs to take the enchantments of older takes from (default: all under runs/alt-d)',
    )  # fmt: skip
    args = parser.parse_args(argv)
    seen = sightings(args.probe)
    found: list[dict[str, Any]] = []
    for directory in args.takes or sorted(path.parent for path in (runs / 'combat').glob('*/manifest.json')):
        try:
            take = Take.load(directory)
            found += hurts(take, enchantments(seen, take))
        except (OSError, ValueError) as exc:
            print(f'{directory.name}: not read ({exc})')
    print(report(found))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
