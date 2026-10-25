"""Bolts in flight of the shooters whose AI is not read: each one already let go and headed at the character's way is
one correlated blow, priced where and when it reaches the way (rca/2026-10-23/dominus-burst-findings.md).

The incident, 2026-10-23 04:35:48 (take 20261023T013533Z-119, level 119): a tier 5 Herald pack of Dominus
(monstats `succubuswitch6`, txt 636, AI SuccubusWitch, every member Multiple Shots / Mana Burn / Spectral Hit, stat 25
damagepercent 285) shot volleys of 3 `succubusmiss` bolts (missiles.txt 665, 10 units a second). The character stood
3.1 s at one place while 7 bolts converged; the safety priced the hold at 4 points (the pooled shooter fit: 2.4 % of
shots take life, 127 points a shot) and 4 bolts took 749 + 447 + 505 in 0.17 s (life 2672 -> 971). The player's ruling:
"we must not die or we lose exp and our gear".

- `SHOOTERS`: monster families (monstats BaseId, terror/data/threats.json `family`) -> the missile classes they shoot
  that the look reads (macros/safety.py `Safety.look`, BOLTS_IN_FLIGHT) and this module prices.
- `exposure`: each read bolt flies straight on (owner -> bolt), BOLT_SPEED units a second; one that passes within
  CONTACT of a place of the way while the way is there is one blow of `points` with LANDS, at that time.
- `points`: the shot's raw points by kind: the table blow (monstats A1 at monlvl DM(H)) as physical and the threat
  table's magic multiple as magic, both raised by the larger of the rank/Herald boost and the unit's own stat 25
  (`Hostile.raised`), the most times MARGIN.
- `dodges`: places square to the bolts' way, out of their lane (a dodge: macros/safety.py `Safety.offered`).
- READ_THROWS (rca/2026-10-23/death-canyon-findings.md): every unread type's own missiles (monstats MissA1/MissA2) are
  read and priced so, and `throw_rate` reads from them how often a type throws at the character's place.
"""

import math
from collections.abc import Mapping, Sequence
from functools import cache

from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.pack import along
from inventory_tracking.combat.sim.casters import mind_of
from inventory_tracking.combat.sim.monsters import boost, rank_of
from inventory_tracking.levels.geometry import Point
from inventory_tracking.terror.danger import table as threat_table


# Families whose bolts are read and priced: the succubus witches' `succubusmiss` (missiles.txt 665, fired by the skill
# SuccubusBolt, skills.txt 345, `srvmissile`); the take of 2026-10-23 01:35:33Z showed them.
SHOOTERS: dict[str, frozenset[int]] = {'succubuswitch1': frozenset((665,))}
# READ_THROWS (2026-10-23, the death in the Canyon of the Magi, 14:52:24.7, take 20261023T115109Z-46; the player:
# "we must not die or we lose exp and our gear"): a tier 5 Herald pack of 15 Hell Slingers (txt 376, no read model)
# threw 8-12 javelins a second at the character's place; the pooled shooter fit (2.4 % of shots take life) priced the
# pack at 2.8 life a second while 2014 went in 0.62 s. True: every type with no read AI and no read model has the
# missiles of its monstats attacks (MissA1, MissA2) read in flight, each a blow where it reaches the way (as the
# Dominus' bolts), and its rate at the character read from them (`throw_rate`, combat/harm.py). False: SHOOTERS alone
READ_THROWS = False
# Units a second a bolt flies: missiles.txt Vel 10; the take's frames measure 10.1 (37 -> 26.4 units in 1.0 s). A class
# not measured flies at its missiles.txt Vel (`speed_of`); `pantherjav4` (229, Vel 20) measured 22.9-24.5 over 109
# javelins of take 20261023T115109Z-46.
BOLT_SPEED: dict[int, float] = {665: 10.1, 229: 23.5}
# Units from the character a bolt takes life within: the take's bolts vanished 0.6-1.5 units off its read place; the
# rest for the read lag of a place.
CONTACT = 2.0
# The share of bolts reaching the character that took life in the take (7 of the 10 that vanished within 1.5).
LANDS = 0.7
# On the most of a bolt's points: the take's largest (749) over the table's most at stat 25 = 285 (653).
MARGIN = 1.15
FRAME = 1 / 25


def classes_of(txt: int) -> frozenset[int]:
    """The missile classes monster type `txt` shoots that this module prices (empty: none): its family's (SHOOTERS),
    and with READ_THROWS its attacks' own (`thrown`) unless its AI is read (combat/harm.py prices those)."""
    row = threat_table().monsters.get(txt)
    found = SHOOTERS.get(row.family, frozenset()) if row is not None else frozenset()
    if READ_THROWS and mind_of(txt) is None:
        found |= thrown(txt)
    return found


@cache
def thrown(txt: int) -> frozenset[int]:
    """The missile classes of type `txt`'s attacks (monstats MissA1, MissA2) that can take life (not
    `harmless_missiles`)."""
    row = tables()['monsters'].get(str(txt), {})
    names = {row.get('MissA1'), row.get('MissA2')} - {None, ''}
    harmless = set(tables()['harmless_missiles'])
    return frozenset(
        int(mid)
        for mid, missile in tables()['missiles'].items()
        if missile.get('Missile') in names and int(mid) not in harmless
    )


def speed_of(kind: int) -> float | None:
    """Units a second a bolt of class `kind` flies: measured (BOLT_SPEED), else its missiles.txt Vel with
    READ_THROWS; None: not priced."""
    found = BOLT_SPEED.get(kind)
    if found is not None or not READ_THROWS:
        return found
    vel = float(tables()['missiles'].get(str(kind), {}).get('Vel') or 0)
    return vel if vel > 0 else None


# READ_THROWS: a throw meets the first body on its line (missiles.txt CollideType 3: units and walls). A live companion
# within COVER units of the line from the thrower to the character's place, nearer the thrower than that place, takes
# it but for COVER_LEAK: take 20261021T161018Z-110 (area 110, 2026-10-21, the merc and two demons 0-1.6 off the
# character) had 340 javelins and imp bolts aimed at the character's place over 290 s and 10 ward breaks and 4 hurts
# from all sources (4 %, against 68 % by the game's to-hit); take 20261023T115109Z-46's bound demon on the character's
# place took every javelin for 6 s (life 128 -> 20) and none reached the character until it fell
COVER = 1.5
COVER_LEAK = 0.1


def covered(cover: Sequence[Point], start: Point, end: Point) -> float:
    """The share of a throw from `start` at `end` no companion takes first: COVER_LEAK when a live one (`cover`) stands
    within COVER of the line and nearer `start` along it than `end` is, else 1."""
    gap = math.dist(start, end)
    if gap <= 0:
        return 1.0
    dx, dy = (end[0] - start[0]) / gap, (end[1] - start[1]) / gap
    for spot in cover:
        along = (spot[0] - start[0]) * dx + (spot[1] - start[1]) * dy
        off = abs((spot[0] - start[0]) * dy - (spot[1] - start[1]) * dx)
        if 0.0 < along < gap and off <= COVER:
            return COVER_LEAK
    return 1.0


def cover_at(cover: Sequence[Point], start: Point, place: Point) -> tuple[Point, ...]:
    """The companions' places (`cover`, the look's at `start`) when the character stands at `place`: as they are at
    `start`; elsewhere the ones a jump takes along (combat/pack.py `along`: within TAKEN_ALONG of `start`, every one
    with ALONG_ALL) come along, as far off the character and to the same side
    (a Teleport lands an ally within 10 within 3 of the character, rca/2026-10-21/herald-gloam-findings.md §3), the
    others are left where they stand."""
    if place == start:
        return tuple(cover)
    dx, dy = place[0] - start[0], place[1] - start[1]
    return tuple((c[0] + dx, c[1] + dy) if along(start, c) else c for c in cover)


def place_at(legs: Sequence[tuple[Point, float]], seconds: float) -> Point:
    """Where the way of `legs` ((place, dwell), in order) is `seconds` into it (its last place past its end)."""
    began = 0.0
    for place, dwell in legs:
        if seconds <= began + dwell:
            return place
        began += dwell
    return legs[-1][0]


def throw_count(
    bolts: Sequence[tuple[int, Point, float]],
    speed: float,
    shooters: Mapping[int, Point],
    places: Sequence[Point],
    reach: float,
) -> tuple[int, float]:
    """One look's reading of a type's throws at the character (READ_THROWS): (its bolts in flight, (owner, where,
    heading), `speed` units a second, from a shooter within `reach` whose lane comes at one of `places`, the
    character's now and at the last look; the seconds a throw of each of those shooters stays in flight to the nearest
    place). In a steady fight the bolts in flight are the rate times their flight: the rate is the sum of the first
    over the sum of the second across looks (macros/safety.py `Safety.throws_read`), not one look's ratio (a near
    shooter's one bolt over its 0.1 s flight reads 10 a second)."""
    gaps = {unit: min(math.dist(at, place) for place in places) for unit, at in shooters.items()}
    near = {unit for unit, gap in gaps.items() if gap <= reach}
    coming = sum(
        1 for owner, at, heading in bolts if owner in near and any(heading_at(at, heading, p, speed) for p in places)
    )
    return coming, sum(gaps[unit] for unit in near) / speed


def points(txt: int, level: int | None, flags: int, mods: Sequence[int], tier: int, raised: float) -> tuple:
    """A bolt's raw points as ((kind, least, most), ...) (the module text)."""
    row = tables()['monsters'].get(str(txt), {})
    level = level or int(float(row.get('Level(H)') or 1))
    base = float(tables()['monlvl'].get(str(level), {}).get('DM(H)', 0)) / 100
    factor = max(boost(rank_of(flags), mods, tier), raised)
    least, most = float(row.get('A1MinD(H)') or 0), float(row.get('A1MaxD(H)') or 0)
    threat = threat_table().monsters.get(txt)
    magic = threat.magic * 100 if threat is not None else 0.0
    parts = []
    if most > 0:
        parts.append(('physical', base * least * factor, base * most * factor * MARGIN))
    if magic > 0:
        parts.append(('magic', base * magic / 2 * factor, base * magic * factor * MARGIN))
    return tuple(parts)


def arrival(at: Point, heading: float, speed: float, place: Point) -> tuple[float, float]:
    """(seconds until a bolt at `at` flying `heading` is nearest `place`, how near it passes); negative: passed."""
    dx, dy = math.cos(heading), math.sin(heading)
    rx, ry = place[0] - at[0], place[1] - at[1]
    along = rx * dx + ry * dy
    return along / speed, abs(rx * dy - ry * dx)


def hit_time(at: Point, heading: float, speed: float, legs: Sequence[tuple[Point, float]]) -> float | None:
    """The seconds into `legs` ((place, dwell), in order) the bolt reaches the place the way is at then, None if it
    passes them all (the module text)."""
    began = 0.0
    slack = CONTACT / speed
    for place, dwell in legs:
        seconds, off = arrival(at, heading, speed, place)
        if off <= CONTACT and seconds >= -slack and began - slack <= seconds <= began + dwell + slack:
            return max(seconds, began, 0.0)
        began += dwell
    return None


def heading_at(at: Point, heading: float, place: Point, speed: float) -> bool:
    """Whether a bolt is coming at `place` (its lane within CONTACT, not yet past)."""
    seconds, off = arrival(at, heading, speed, place)
    return off <= CONTACT and seconds >= -CONTACT / speed


def dodges(bolts: Sequence[tuple[Point, float]], here: Point, steps: Sequence[float] = (5.0, 8.0)) -> list[Point]:
    """Places square to the mean way of the bolts coming at `here` ((where, heading)), `steps` units to either side."""
    coming = [heading for at, heading in bolts if heading_at(at, heading, here, 10.0)]
    if not coming:
        return []
    x = sum(math.cos(h) for h in coming)
    y = sum(math.sin(h) for h in coming)
    if math.hypot(x, y) < 1e-6:
        return []
    mean = math.atan2(y, x)
    found = []
    for step in steps:
        for side in (1, -1):
            turn = mean + side * math.pi / 2
            found.append((here[0] + step * math.cos(turn), here[1] + step * math.sin(turn)))
    return found
