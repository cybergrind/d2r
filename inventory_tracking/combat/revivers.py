"""Who raises whom: the monsters whose skill brings the dead of their kind back, read off the game's own tables, and
what a fight does about them (REVIVERS_FIRST, 2026-10-23).

The live fight of 2026-10-23 02:08:06-02:08:41 (session 20261022T223539Z-d878def0, take 20261022T230603Z-3, Cold
Plains, anomaly JUMP_CLUSTER): 35 s, 15 jumps and 16 casts, 0 kills, against a tier 5 Herald pack of Fallen (monstats
19 `fallen1`) with Fallen Shamans (58 `fallenshaman1`, Skill1 Resurrect): the strikes and the marks went on Fallen
that the shamans stood up again. The player's goal: "push xp/hour", and of fights that jump about: "what is estimated
exp/hour if we're jumping around without kills?".

The table (data/revivers.json) is built by `main` from the dumped excel tables (pricing/raw/game-excel: monstats,
skills, monsters-strings; not checked in); do not edit it by hand:

    uv run --offline python -m inventory_tracking.combat.revivers

A reviver is a monstats row (enabled) with one of its Skill1..8 a skills.txt row whose `srvdofunc` is RESURRECT (97,
`TargetCorpse` 1: Resurrect and Resurrect2). What it raises and from how far is its AI, not a table column: the Hell AI
parameters `aipN(H)` are read by position (RULES), the positions' meaning taken from the legacy server's source
(third-parties/D2MOO source/D2Game/src/AI/AiThink.cpp: `D2C_FallenShamanAIParams` and `AITHINK_TargetCallback_
FallenShaman`, which skips a unique's or a champion's corpse; `D2C_GreatMummyAIParams`; `D2C_FetishShamanAIParams`).
Three families come out: the Fallen Shamans (Resurrect: the Fallen and other shamans), the Greater Mummies (Unravelers,
Horadrim Ancients, Radament: Resurrect2 on any low undead), the Fetish Shamans (Resurrect2: the Flayers). Not
revivers, though their skill names sound so: SkeletonRaise (no server function: a skeleton's own rising), Self-
resurrect (the Reanimated Horde gets up by itself: nobody to kill first), CorpseCycler, the corpse explosions. The
Oblivion Knights and the Unravelers' undead neighbours raise nothing.

What the fight does (REVIVERS_FIRST): a live reviver *raising* (a hostile it can raise stands within its raise range,
COVER_MARGIN more: what the fight kills there lies in its reach) comes before what it raises:

- the strike's lines (combat/policy.py `observe` sets `Foe.weight`): a point off a raising reviver counts
  REVIVER_WEIGHT, a point off one it can raise RAISED_WEIGHT (what dies there comes back); a place's worth (combat/
  stance.py `taken`) the reviver's alone. A hold of the strike on the reviver till it dies (as HOLD_LEADER's) was
  tried and taken out: in the arena's level runs it cleared the shamans among their Fallen in 13.8 s against 12.3 for
  the weights alone (11.6 off), the shamans 5 behind in 18 of 20 plays against 19 (20 seeds, 2026-10-23);
- the designated Death Mark (builds/warlock/mark.py `reviver_designated`) goes on one past the blades' reach before the
  Herald pack's order or a leader, its mark worth casting whatever the trash rule says (the demons are its answer);
- the agenda (macros/agenda.py `Agenda.observe`) gives a raising reviver among the leaders the Herald's tier.

A Herald's minion is raised like any other; a unique's or super unique's corpse never is, a champion's only by the
Greater Mummies (`spared`, by the rank flags of game/layout.py).
"""

import csv
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from inventory_tracking.game.layout import CHAMPION_FLAG, MINION_FLAG, SUPER_FLAG, UNIQUE_FLAG
from inventory_tracking.levels.geometry import Point


FILE = Path(__file__).parent / 'data' / 'revivers.json'
EXCEL = Path(__file__).parents[2] / 'pricing' / 'raw' / 'game-excel'
RESURRECT = '97'  # skills.txt srvdofunc of Resurrect and Resurrect2
GAME_RATE = 25  # frames a second

# The player, 2026-10-23 (the module text): "push xp/hour"; a tier 5 Herald pack of Fallen fought 35 s for no kill while
# its Fallen Shamans raised them. True: a raising reviver comes first (the module text: the strike's lines, the
# designated Death Mark past the blades' reach, the agenda's tier), with macros/hunting/revive.py REVIVER_STAND (its
# firing spot and "never left alone"): the two were measured together. The arena's level runs, 20 seeds, off -> on
# (tests/inventory_tracking/scenarios/arena/situations/revivers.py, 2026-10-23), no death either way: shamans 10 behind
# the Fallen cleared in 20 plays of 20 against 10 (median 23.4 s against 49.3, lasting kills 15.0/min against 10.4),
# 5 behind 19 against 8 (20.8 s against 34.0; 14.9 against 10.4); an Unraveler's pack 3.0 s against 3.8, 10 behind
# 5.1 against 5.2, a champion one 7.2 against 7.4; the Tomb cut of take 20261022T232713Z-70 43.5 lasting kills/min
# against 43.2 (its elite Unraveler of 335,538 points outlives the 60 s); shamans among the Fallen 12.3 s against 11.6
# (lasting 15.0 either). False: the revivers are monsters like any other, as before.
REVIVERS_FIRST: bool = True
COVER_MARGIN = 3.0  # units past a reviver's raise range that a hostile it can raise still counts (the pack moves)
REVIVER_WEIGHT = 4.0  # a point off a raising reviver: above a line through the plain pack beside it
RAISED_WEIGHT = 0.25  # a point off one a raising reviver covers: it comes back at full life

# AI -> where its Hell parameters hold the raise chance (percent a think) and the raise range (units from the reviver
# to the corpse), what it raises: monstats BaseId values (`bases`) or a flag column (`flag`), and the module text's
# source for each.
RULES: dict[str, dict[str, Any]] = {
    'FallenShaman': {
        'chance': 'aip1(H)',
        'range': 'aip4(H)',
        'bases': ('fallen1', 'fallenshaman1'),
        'raises': 'corpses whose BaseId is fallen1 or fallenshaman1 (other shamans too), never a unique or champion',
        'champions': False,
    },
    'GreaterMummy': {
        'chance': 'aip2(H)',
        'range': 'aip5(H)',
        'flag': 'lUndead',
        'raises': 'corpses of any lUndead monster on its side, champions too, never a unique; it also heals them',
        'champions': True,
    },
    'FetishShaman': {
        'chance': 'aip1(H)',
        'range': 'aip5(H)',
        'close': 'aip3(H)',  # the squared distance to the corpse from which it raises; further off it walks there
        'bases': ('fetish1', 'fetishblow1'),
        'raises': (
            'corpses whose BaseId is fetish1 or fetishblow1; it walks to the corpse and raises from close by '
            '(aip3(H) against the squared distance); with aip2(H) 3 uniques and champions too'
        ),
        'champions': False,  # aip2(H) is not 3 in any Hell row (data/revivers.json): no champion raised
    },
}


@dataclass(frozen=True)
class Reviver:
    """One reviver type of the table: its txt id, name, AI family, what it raises (txt ids), from how far (units) and
    the mean seconds between two raises with a corpse in range (the think delay over the raise chance; the cast's
    own length is in no table)."""

    txt: int
    name: str
    ai: str
    raises: frozenset[int]
    range: float
    seconds: float


# -- the table -------------------------------------------------------------------------------------------------------


def rows(directory: Path, name: str) -> list[dict[str, str]]:
    with (directory / f'{name}.txt').open(encoding='latin-1', newline='') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def number(text: str) -> int | None:
    return int(text) if text.strip().lstrip('-').isdigit() else None


def skills_of(row: dict[str, str]) -> list[str]:
    return [row[f'Skill{n}'] for n in range(1, 9) if row.get(f'Skill{n}')]


def raised_rows(monsters: Sequence[dict[str, str]], rule: Mapping[str, Any]) -> list[dict[str, str]]:
    """The enabled monstats rows a reviver of `rule` raises."""
    if 'bases' in rule:
        kept = [r for r in monsters if r['BaseId'] in rule['bases']]
    else:
        kept = [r for r in monsters if r[rule['flag']] == '1']
    return [r for r in kept if r['enabled'] == '1']


def build(directory: Path = EXCEL) -> dict[str, Any]:
    """The table from the dumped excel files in `directory` (the module text)."""
    monsters = [r for r in rows(directory, 'monstats') if r.get('*hcIdx', '').isdigit()]
    skills = {r['skill']: r for r in rows(directory, 'skills')}
    strings = {
        e['Key']: e['enUS'] for e in json.loads((directory / 'monsters-strings.json').read_text(encoding='utf-8-sig'))
    }
    raising = {name for name, s in skills.items() if s['srvdofunc'] == RESURRECT and s['TargetCorpse'] == '1'}
    raised = {ai: sorted(int(r['*hcIdx']) for r in raised_rows(monsters, rule)) for ai, rule in RULES.items()}
    found = []
    for row in monsters:
        cast = [name for name in skills_of(row) if name in raising]
        rule = RULES.get(row['AI'])
        if row['enabled'] != '1' or not cast or rule is None:
            continue
        chance, think, reach = number(row[rule['chance']]), number(row['aidel(H)']), number(row[rule['range']])
        if not chance or not think or not reach:
            continue
        found.append({
            'txt': int(row['*hcIdx']),
            'id': row['Id'],
            'name': strings.get(row['NameStr'], row['NameStr']),
            'ai': row['AI'],
            'skill': cast[0],
            'raise_range': reach,
            'raise_seconds': round(think * 100 / chance / GAME_RATE, 2),
        })  # fmt: skip
    return {
        'about': (
            'built by inventory_tracking/combat/revivers.py from pricing/raw/game-excel (monstats, skills, '
            'monsters-strings): the monsters whose skill raises a corpse, what each AI family raises (txt ids), '
            'from how far (units) and how often. Do not edit by hand.'
        ),
        'rules': {ai: rule['raises'] for ai, rule in RULES.items()},
        'raised': raised,
        'revivers': found,
    }


@cache
def revivers() -> dict[int, Reviver]:
    """The table's revivers by txt id (data/revivers.json); empty with no file."""
    if not FILE.exists():
        return {}
    data = json.loads(FILE.read_text(encoding='utf-8'))
    families = {ai: frozenset(found) for ai, found in data['raised'].items()}
    return {
        row['txt']: Reviver(
            row['txt'], row['name'], row['ai'], families[row['ai']], float(row['raise_range']), row['raise_seconds']
        )
        for row in data['revivers']
    }


# -- the fight -------------------------------------------------------------------------------------------------------


def raising(bodies: Iterable[tuple[int, int, Point, int]]) -> dict[int, frozenset[int]]:
    """`covers` under REVIVERS_FIRST; empty with it off."""
    return covers(bodies) if REVIVERS_FIRST else {}


def covers(bodies: Iterable[tuple[int, int, Point, int]]) -> dict[int, frozenset[int]]:
    """Of `bodies` (unit, txt, place, rank flags: the live hostiles of a look), each reviver raising: its unit -> the
    units it would raise once dead (of its family, within its range and COVER_MARGIN, not itself, none it spares:
    `spared`). A reviver with none is not raising."""
    table = revivers()
    found = list(bodies)
    out: dict[int, frozenset[int]] = {}
    for unit, txt, at, _ in found:
        reviver = table.get(txt)
        if reviver is None:
            continue
        reach = reviver.range + COVER_MARGIN
        covered = frozenset(
            other
            for other, kind, there, flags in found
            if other != unit and kind in reviver.raises and not spared(reviver, flags) and math.dist(at, there) <= reach
        )
        if covered:
            out[unit] = covered
    return out


def spared(reviver: Reviver, flags: int) -> bool:
    """Whether `reviver` leaves the corpse of a monster of these rank flags lying: a unique's or super unique's always
    (a Herald's minion carries the minion flag and is raised), a champion's unless its family raises champions."""
    if flags & MINION_FLAG:
        return False
    if flags & (UNIQUE_FLAG | SUPER_FLAG):
        return True
    return bool(flags & CHAMPION_FLAG) and not RULES[reviver.ai].get('champions', False)


def weights(bodies: Iterable[tuple[int, int, Point, int]]) -> dict[int, float]:
    """Unit -> what a point off it is worth to the strike's lines (the module text): REVIVER_WEIGHT for a raising
    reviver, RAISED_WEIGHT for one a raising reviver covers (a reviver covered by another is a reviver first); the
    rest are not listed (1)."""
    found = raising(bodies)
    out = {unit: RAISED_WEIGHT for covered in found.values() for unit in covered}
    out.update(dict.fromkeys(found, REVIVER_WEIGHT))
    return out


def main() -> int:
    found = build()
    FILE.write_text(json.dumps(found, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    revivers.cache_clear()
    for row in found['revivers']:
        print(row['txt'], row['id'], row['name'], row['ai'], row['raise_range'], row['raise_seconds'])
    print(f'{FILE}: {len(found["revivers"])} revivers; raised: { ({ai: len(t) for ai, t in found["raised"].items()}) }')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
