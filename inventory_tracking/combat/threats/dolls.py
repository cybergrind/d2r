"""Exploding monsters: the undead fetishes' death blast and how the run keeps out of it
(rca/2026-10-21/dolls-tz-findings.md, F0-F3).

The player, 2026-10-21 ~13:35: "it looks like we're too reckless when engaging with dolls in terrorized zone"; for the
queue: "start implementation for ready to build items without questions"; and before: "we must not die or we lose exp
and our gear", a valuable in the read is taken, never left in the game. The study: 59% of the life lost in 53 Act 3
doll takes is the death blast of Undead Stygian Dolls (~430 a doll, 256-1042, within ~4.5 units); they run in at ~15.5
units a second (~22 under Extra Fast) and die on arrival; every blast came 0.08-2.1 s after a hop that landed 7-16 units
from a live doll (pickup hops "the fight first", group goals, "clearing the way", retreats, firing spots).

- F0 `EXPLODING`: monstats.txt `deathDmg` (game data, combat/data/exploding.json, `build`), never a memory read.
- F1 DOLL_GUARD: a side drop (potion, gold, valuable) with a live doll within GUARD_NEAR of it or the character is not
  gone to; its dolls are fought from LAND_UNITS off first, then it is picked up (macros/goals.py `goal_of`,
  `in_the_way`, `first_fight`).
- F2 DOLL_LAND: no jump lands within LAND_UNITS of a live doll (FAST_FACTOR more under Extra Fast), the doll where it
  stands or where its run-in has it at the landing (`barring`; macros/safety.py `Pricing.move_price`, `approach`).
- F3 DOLL_FIRST: dolls in reach and not yet on the character are struck first (`first_struck`; macros/hunt.py
  `Hunter.choose`).

`RUNNERS` are the exploding types the rules are for: the undead fetishes (monstats AI `Fetish`), which run in and die
in one cast. The other exploding types (siege beasts, the Baal clone, the siege windows) keep the old corpse bar alone
(combat/harm.py `corpse_radius`): their run-in and blast were not measured.
"""

import csv
import json
import math
import sys
from collections.abc import Callable, Iterable, Mapping
from functools import cache
from pathlib import Path
from typing import Any

from inventory_tracking.combat.pack import Member, densest
from inventory_tracking.levels.geometry import Point


DATA = Path(__file__).parent.parent / 'data' / 'exploding.json'
# The installed game's monstats.txt (pricing/raw is git-ignored; `build` bundles what the rules read)
MONSTATS = Path(__file__).parents[3] / 'pricing' / 'raw' / 'game-excel' / 'monstats.txt'

# F1 (2026-10-21): pickups wait for the dolls near them. False: a potion's guards within goals.py GUARD_NEAR are the
# fight first, other drops are gone to whatever is near, as before.
DOLL_GUARD = True
GUARD_NEAR = 20.0  # units from the drop or the character (findings §7 F1: 88% of the blast life came within 20)
# F2 (2026-10-21): no jump lands near a live doll. False: only the corpse bar at the final place (harm.py), as before.
# Off since 2026-10-21 ~14:55 after its first live session (20261021T113933Z-f2b0c698, from 14:39:33): Durance of Hate
# Level 2 not done after 6+ min (about 3.5 before), kills 30-53 a minute against 75-80, "dolls: N landings near a live
# doll left out" 140+ times and the PATIENCE lift several times. The player, 14:50: "it looks like we're struggling
# with dolls: we're not engaging them and keep teleporting around without actuall kills".
DOLL_LAND = False
LAND_UNITS = 16.0  # findings §4: a doll needs ~1.0 s to cross 16 units; the first cast after a landing came ~0.5 s
EXTRA_FAST = 6  # monumod id of Extra Fast (terror/tracker.py MODIFIER_NAMES): the Terror Zone's effect on a monster
FAST_FACTOR = 1.25  # LAND_UNITS 20 under Extra Fast (findings §4: >= 20; dolls ran 21.9 against 15.3-16.2)
RUN_SPEED = 15.5  # units a second a doll runs in (frames of three Durance 2 takes)
FAST_SPEED = 21.9  # the same under Extra Fast (the 13:30 take)
# The character within this of a live doll: an escape (a retreat, a dodge) landing near another doll is barred only
# when an escape that lands clear of every doll is priced too; else the escapes stand as before (the brief: "the
# existing escape logic wins").
CLOSE_UNITS = 6.0
# Seconds the asked move may stay barred by dolls with nothing in reach before the bar is lifted for it (the corpse
# bar stays): idle dolls behind a wall would hold the run for ever ("the loop never stands").
PATIENCE = 4.0
# F3 (2026-10-21): dolls in reach are struck first. False: the line worth the most, as before. Off since 2026-10-21
# ~14:45, before it went live: the threat scene `dolls_running_in` (standing, no safety) took 390 for 1098, but the
# arena's four-pack example (the pursuit loop, 12 seeds) took 142 a play (101 of doll blasts) against 61 (0): the line
# laid through a doll further off also kills the dolls already near the character. Keeping off until no doll is within
# 11-14 of the character did no better in both (rca/2026-10-21/dolls-tz-findings.md F3).
DOLL_FIRST = False
BLAST_UNITS = 4.5  # findings §2: 57 of 62 blasts of 250+ came within 4.5; one already this near is not "first"
LANDED = 'a live doll is near the landing'  # the bar's reason (harm.py `Harm.barred`)
# DOLL_BAIT (2026-10-21): Death Mark on a doll so the demons it sends draw the dolls and take their blasts
# (builds/warlock/mark.py `target`, `why_not`). The player, 14:50: "regarding the dolls: we could use death mark to
# teleport our daemon even throught the walls to take the aggro"; 14:58: "yes, we just need our daemon to take the aggro
# from dolls and then we could easily walk into any room". The doll marked: of the live dolls within BAIT_NEAR, those
# BAIT_MIN or more off (one nearer comes on anyway), the one nearest the disc of mark.MARK_PACK that covers the most
# dolls (combat/pack.py `densest`); none while a mark may last on one. OFF: in the arena (12 seeds, the pursuit loop, a
# Defiler out) it took fewer kills a minute in every variant (two doll packs: 239 -> 147; the four-pack example 84 ->
# 66) and lowered the blast life only in some (two doll packs 270 -> 68; four packs 0 -> 34; a pack window of 10-20:
# 270 -> 304): the rule set for the switch (no worse kills a minute, lower blasts) is not met. With the way in below
# (~15:40, the same arena): two doll packs 271 taken / 270 blast / 239 kills a minute -> 151 / 68 / 132 (a mark again
# at once after each doll's death: 9 a play), 82 / 0 / 148-157 with no mark again within 3-6 s; the four-pack example
# 77 / 0 / 84 -> 332-348 / 236 / 51-53 (the way in walks into the other packs). Still off.
DOLL_BAIT = False
BAIT_NEAR = 30.0
BAIT_MIN = 10.0
# Then the character goes in (the player, 14:58: "and then we could easily walk into any room"): with dolls held by a
# demon (within HELD_UNITS of one that stands combat/pack.py DEMON_APART off the character, and nearer it than the
# character), a move to BAIT_STAND from the held dolls' middle on the character's side, preferred by the arbiter
# (macros/pursuit.py, BAIT_SAID) while not vetoed, BAIT_HOPS a held pack at most; none once the character stands within
# BAIT_STAND + BAIT_SLACK of it (it strikes from there)
HELD_UNITS = 8.0  # builds/warlock/mark.py MARK_PACK: the pack a mark turns
BAIT_STAND = 12.0  # units from the held dolls' middle: the blades' line (20+) reaches the pack, the blasts (4.5) do not
BAIT_SLACK = 3.0
BAIT_HOPS = 3
BAIT_SAID = 'dolls held by the demon: going in to strike them'
FIGHTER = 'Fetish'  # monstats AI of the undead fetishes (RUNNERS)


def build(source: Path = MONSTATS, out: Path = DATA) -> dict[str, dict[str, Any]]:
    """Bundle monstats.txt's rows with `deathDmg` (their `*hcIdx`, Id, AI, Velocity, Run) as
    combat/data/exploding.json."""
    with source.open(encoding='utf-8', errors='replace', newline='') as handle:
        rows = list(csv.DictReader(handle, delimiter='\t'))
    found = {
        row['*hcIdx']: {
            'id': row['Id'],
            'ai': row['AI'],
            'velocity': int(row['Velocity'] or 0),
            'run': int(row['Run'] or 0),
            'death_damage': int(row['deathDmg']),
        }
        for row in rows
        if row.get('deathDmg') not in (None, '', '0')
    }
    data = {'source': 'monstats.txt deathDmg (installed game, pricing/raw/game-excel)', 'monsters': found}
    out.write_text(json.dumps(data, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    return found


@cache
def rows() -> dict[int, dict[str, Any]]:
    """The exploding types by class (`*hcIdx`)."""
    return {int(txt): row for txt, row in json.loads(DATA.read_text(encoding='utf-8'))['monsters'].items()}


@cache
def exploding() -> frozenset[int]:
    """Every type whose corpse explodes (monstats `deathDmg`)."""
    return frozenset(rows())


@cache
def runners() -> frozenset[int]:
    """The exploding types that run in (the undead fetishes, AI FIGHTER)."""
    return frozenset(txt for txt, row in rows().items() if row['ai'] == FIGHTER)


def runner(txt: int) -> bool:
    return txt in runners()


def herald_doll(monster: Any) -> bool:
    """A Terror Zone Herald that is a running doll (`RUNNERS`): its tier (stat 367) with the unique flag, as
    builds/warlock/mark.py `herald` tells a Herald (macros/cta.py DOLL_HERALD_FIRST, builds/warlock/mark.py
    DOLL_HERALD_FIRST)."""
    txt = getattr(monster, 'txt_id', None)
    txt = getattr(monster, 'txt', None) if txt is None else txt  # a read Monster's `txt_id`, a priced Hostile's `txt`
    return (
        txt is not None
        and runner(txt)
        and bool(getattr(monster, 'tier', 0))
        and bool(getattr(monster, 'leader', False))
    )


def place_of(m: Any) -> Point:
    """A hostile's place: `at` (combat/harm.py `Hostile`) or `x`, `y` (game/records.py `Monster`)."""
    return m.at if hasattr(m, 'at') else (m.x, m.y)


def txt_of(m: Any) -> int:
    return m.txt if hasattr(m, 'txt') else m.txt_id


def live_runners(hostiles: Iterable[Any]) -> list[Any]:
    """The live RUNNERS among `hostiles` (a dead or dying mode is not alive: monmode 0, 12)."""
    return [m for m in hostiles if runner(txt_of(m)) and getattr(m, 'mode', 1) not in (0, 12)]


def fast(m: Any) -> bool:
    return EXTRA_FAST in tuple(getattr(m, 'modifiers', ()) or ())


def land_units(m: Any) -> float:
    """How near a landing a doll bars: LAND_UNITS, FAST_FACTOR more under Extra Fast."""
    return LAND_UNITS * (FAST_FACTOR if fast(m) else 1.0)


def run_in(m: Any, toward: Point, seconds: float) -> Point:
    """Where a doll's run-in has it after `seconds` running at `toward` (RUN_SPEED, FAST_SPEED under Extra Fast),
    stopped at BLAST_UNITS from it."""
    at = place_of(m)
    gap = math.dist(at, toward)
    travel = min(max(0.0, gap - BLAST_UNITS), (FAST_SPEED if fast(m) else RUN_SPEED) * max(0.0, seconds))
    if gap <= 1e-9 or travel <= 0:
        return at
    share = travel / gap
    return (at[0] + (toward[0] - at[0]) * share, at[1] + (toward[1] - at[1]) * share)


def barring(here: Point, spot: Point, hostiles: Iterable[Any], seconds: float) -> tuple[float, float] | None:
    """The live doll nearest to barring a landing at `spot` made from `here` in `seconds`: (its gap, the gap it bars
    within), the gap the least of where it stands and where its run-in at the character has it at the landing; None
    when none is within its `land_units`."""
    found = None
    for m in live_runners(hostiles):
        gap = min(math.dist(place_of(m), spot), math.dist(run_in(m, here, seconds), spot))
        bar = land_units(m)
        if gap < bar and (found is None or gap - bar < found[0] - found[1]):
            found = (gap, bar)
    return found


def close(here: Point, hostiles: Iterable[Any]) -> bool:
    """A live doll within CLOSE_UNITS of the character."""
    return any(math.dist(place_of(m), here) < CLOSE_UNITS for m in live_runners(hostiles))


def guards(place: Point, here: Point, hostiles: Iterable[Any]) -> list[Any]:
    """The live dolls within GUARD_NEAR of a drop at `place` or of the character (F1, DOLL_GUARD)."""
    if not DOLL_GUARD:
        return []
    return [
        m
        for m in live_runners(hostiles)
        if min(math.dist(place_of(m), place), math.dist(place_of(m), here)) <= GUARD_NEAR
    ]


def bait_target(
    here: Point, hostiles: Iterable[Any], cover: float, lasts: Callable[[Any], bool], tries: Callable[[Any], int]
) -> Any | None:
    """DOLL_BAIT's doll (see the switch): None when off, with no doll within BAIT_NEAR or none BAIT_MIN off, or while
    `lasts` says a mark may last on one. `cover`: the mark's pack radius; `tries`: its keys on a doll that did not
    take (fewest first)."""
    if not DOLL_BAIT:
        return None
    found = [m for m in live_runners(hostiles) if math.dist(here, place_of(m)) <= BAIT_NEAR]
    if not found or any(lasts(m) for m in found):
        return None
    far = [m for m in found if math.dist(here, place_of(m)) >= BAIT_MIN]
    if not far:
        return None
    spot = densest([Member(getattr(m, 'unit_id', 0), place_of(m)) for m in found], cover)
    return min(far, key=lambda m: (tries(m), math.dist(spot, place_of(m))))


def held_pack(here: Point, hostiles: Iterable[Any], holders: Iterable[Point]) -> tuple[Point, int] | None:
    """The live dolls a demon holds: within HELD_UNITS of one of `holders` (combat/pack.py `holders`) and nearer it
    than the character. (Their middle, the lowest unit of them as the pack's key); None when none is held."""
    demons = list(holders)
    held = [
        m
        for m in live_runners(hostiles)
        if any(
            math.dist(place_of(m), d) <= HELD_UNITS and math.dist(place_of(m), d) < math.dist(place_of(m), here)
            for d in demons
        )
    ]
    if not held:
        return None
    middle = (sum(place_of(m)[0] for m in held) / len(held), sum(place_of(m)[1] for m in held) / len(held))
    return middle, min(getattr(m, 'unit', getattr(m, 'unit_id', 0)) for m in held)


def bait_stand(here: Point, middle: Point) -> Point | None:
    """Where the character strikes a held pack from: BAIT_STAND from its middle toward the character; None when it
    stands within BAIT_STAND + BAIT_SLACK of it already."""
    away = math.dist(here, middle)
    if away <= BAIT_STAND + BAIT_SLACK:
        return None
    share = BAIT_STAND / away
    return (middle[0] + (here[0] - middle[0]) * share, middle[1] + (here[1] - middle[1]) * share)


def first_struck(here: Point, hostiles: Mapping[int, Any], reachable: Iterable[int]) -> list[int]:
    """F3 (DOLL_FIRST): the live dolls of `reachable` not yet within BLAST_UNITS of the character, nearest first; they
    die before they arrive. Empty when off or none."""
    if not DOLL_FIRST:
        return []
    found = []
    for unit in reachable:
        foe = hostiles.get(unit)
        if foe is not None and runner(txt_of(foe)) and math.dist(here, place_of(foe)) > BLAST_UNITS:
            found.append((math.dist(here, place_of(foe)), unit))
    return [unit for _, unit in sorted(found)]


if __name__ == '__main__':
    if sys.argv[1:] != ['build']:
        sys.exit('usage: python -m inventory_tracking.combat.threats.dolls build')
    print(f'{len(build())} exploding types -> {DATA}')
