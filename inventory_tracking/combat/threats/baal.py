"""Baal's acts priced for a place and a way there (combat/threats `Threat`): what a decision loop needs to choose where
to stand against him. The rules are sim/baal.py's (his rows and skills from the tables; how often he does what from
the probe of eight fights; his think is not read, rca/2026-10-14/baal-sim.md). Nothing here is a tactic: the arbiter
compares the prices of the places it is offered.

The model is keyed on his skills (sim/baal.py `casts_baals`: every monstats row that casts Baal Inferno or Baal
Nova: Baal 544, his clone 570, Uber Baal 709), not on a name, and reads his three missile classes off the game:

- **his inferno** (mode SQ, missiles 554): ten missiles over 20 frames, each flying at where his target stands when it
  is made, INFERNO_STEP a frame for 19 frames (21 units), magic, taken each NextDelay 4 frames of contact. Under
  way it is rolled out frame by frame against the character's way (`stream_points`), as Diablo's stream is. Its
  reach is short: a place beyond it is out of every missile still to come, so that is the place offered;
- **his nova** (S3, missiles 555): a ring from where he stood, NOVA_STEP a frame to 38 units, fire, once a body.
  A ring in flight is priced against the way (`ring_points`); it outruns a walk, so no place is offered for it;
- **his cold missiles** (A1, missiles 589): a fan of makers at his target, cold, once a body each (`cold_points`);
- **what is to come**: each act's rate a second (sim/baal.py `rates`) times its points on a character standing at
  the way's last place, for the time the way has left after the act under way. Tentacles rise near the character
  and are monsters of their own once they stand (combat/harm.py prices them as any melee type); the curse takes no
  life and is not priced.

His target is the nearest body (the frame's search, sim/baal.py); a look gives the companions' count, not where they
stand, so an act not yet aimed is taken to be at the character (`AT_CHARACTER`), and one whose missiles fly
elsewhere is priced by its missiles in flight alone.
"""

import math
from collections.abc import Mapping, Sequence
from functools import cache, lru_cache

from inventory_tracking.combat.sim import baal as rules
from inventory_tracking.combat.sim.casters import CONTACT
from inventory_tracking.combat.threats import Acting, Legs, Part, Threat
from inventory_tracking.combat.threats.diablo import AIMED, FRAME, Way


Point = tuple[float, float]
A1, S3, SQ = 4, 10, 14  # monmode.txt: his cold missiles and teleport, his nova and curse, his inferno's sequence
AT_CHARACTER = 1.0  # [inferred] the chance an act not yet aimed is at the character (module text)
OUT = CONTACT + 1.0  # units beyond the inferno's reach a place out of it is offered at
ACROSS = (4.0, 8.0)  # units across the line of his inferno's missiles in flight the places across it are offered at


@cache
def _level() -> int:
    return rules.level_of(rules.INFERNO)


@cache
def _hit(skill: str) -> dict[str, float]:
    """The expected raw points of one hit of `skill`'s missile, by kind (an inferno contact: its share)."""
    found = rules.mean_points(skill, rules.level_of(skill))
    if skill == rules.INFERNO:
        return {kind: points * rules.INFERNO_SHARE for kind, points in found.items()}
    return found


def _whole(skill: str) -> float:
    return sum(_hit(skill).values())


def _split(skill: str, points: float) -> tuple[tuple[str, float], ...]:
    hit = _hit(skill)
    total = sum(hit.values()) or 1.0
    return tuple((kind, points * value / total) for kind, value in hit.items())


def _bodies(way: Way, frames: int) -> list[Point]:
    return [way.at(frame) for frame in range(frames)]


def stream_points(origin: Point, births: Sequence[int], flying: Sequence[tuple[Point, float]], way: Way) -> float:
    """The raw points his inferno takes from a character on `way`: its missiles in flight (`flying`: where, heading;
    their age reckoned from how far they are from him) and those still to be made `births` frames from now, each
    made at where the way has the character then; a body within CONTACT of a missile is taken from once in its
    NextDelay frames."""
    life, step, gap = rules.inferno_life(_level()), rules.INFERNO_STEP, rules.every(rules.INFERNO_MISSILE)
    missiles: list[list[float]] = []
    for at, heading in flying:
        left = life - math.dist(origin, at) / step
        if left > 0:
            missiles.append([at[0], at[1], math.cos(heading), math.sin(heading), left, -1e9])
    if not missiles and not births:
        return 0.0
    horizon = min(way.frames, max((*births, 0)) + life + 1)
    hit, contacts = _whole(rules.INFERNO), 0
    for frame in range(horizon):
        body = way.at(frame)
        if frame in births:
            distance = math.dist(origin, body) or 1.0
            dx, dy = (body[0] - origin[0]) / distance, (body[1] - origin[1]) / distance
            missiles.append([origin[0], origin[1], dx, dy, float(life), -1e9])
        for m in missiles:
            if m[4] <= 0:
                continue
            m[0] += m[2] * step
            m[1] += m[3] * step
            m[4] -= 1
            if math.dist((m[0], m[1]), body) <= CONTACT and frame - m[5] >= gap:
                m[5] = frame
                contacts += 1
    return contacts * hit


def ring_points(centre: Point, radius: float, way: Way) -> float:
    """The raw points a nova ring of `radius` now, spreading from `centre`, takes from a character on `way`: once,
    when the ring passes within CONTACT of it before it reaches its end."""
    reach = rules.nova_reach()
    for frame in range(way.frames):
        r = radius + rules.NOVA_STEP * frame
        if r > reach + CONTACT:
            return 0.0
        if abs(math.dist(centre, way.at(frame)) - r) <= CONTACT:
            return _whole(rules.NOVA)
    return 0.0


def cold_points(origin: Point, flying: Sequence[tuple[Point, float]], way: Way) -> float:
    """The raw points his cold missiles in flight take from a character on `way`: each once, when it passes within
    CONTACT before its life is over."""
    life, step = rules.cold_life(), rules.cold_step()
    hits = 0
    for at, heading in flying:
        left = int(life - math.dist(origin, at) / step)
        dx, dy = math.cos(heading) * step, math.sin(heading) * step
        for frame in range(min(left, way.frames)):
            body = way.at(frame)
            if math.dist((at[0] + dx * (frame + 1), at[1] + dy * (frame + 1)), body) <= CONTACT:
                hits += 1
                break
    return hits * _whole(rules.COLD)


def cold_fan(origin: Point, way: Way, release: int = 0) -> float:
    """The raw points a fan of cold missiles let go `release` frames from now at where the way has the character
    then takes from it."""
    body = way.at(release)
    toward = math.atan2(body[1] - origin[1], body[0] - origin[0])
    flying = [(origin, heading) for heading in rules.cold_headings(toward)]
    shifted = Way(((way.at(release), 0.0, max(way.frames - release, 1) * FRAME),)) if release else way
    return cold_points(origin, flying, shifted)


@lru_cache(maxsize=512)
def _standing(halves: int) -> tuple[float, float, float]:
    """A whole cast of each of inferno, nova and cold on a character standing `halves` half units from him: raw
    points (a decision loop asks at every look)."""
    distance = halves / 2
    way = Way.stand((distance, 0.0), 3.0)
    inferno = stream_points((0.0, 0.0), rules.inferno_births(0), (), way)
    nova = _whole(rules.NOVA) if distance <= rules.nova_reach() + CONTACT else 0.0
    cold = cold_fan((0.0, 0.0), way)
    return inferno, nova, cold


def standing(distance: float) -> dict[str, float]:
    """Raw points a whole cast of each of his missile acts takes from a character standing `distance` units off."""
    inferno, nova, cold = _standing(round(distance * 2))
    return {'inferno': inferno, 'nova': nova, 'cold': cold}


def _aimed_at(origin: Point, flying: Sequence[tuple[Point, float]], here: Point) -> float | None:
    """The heading of the newest of `flying` when its line passes the character; None otherwise."""
    if not flying:
        return None
    newest, heading = min(flying, key=lambda flight: math.dist(origin, flight[0]))
    dx, dy = here[0] - newest[0], here[1] - newest[1]
    ahead = dx * math.cos(heading) + dy * math.sin(heading)
    off = abs(dy * math.cos(heading) - dx * math.sin(heading))
    return None if ahead < -CONTACT or off > AIMED else heading


def _kind(acting: Acting, missile: int) -> tuple[tuple[Point, float], ...]:
    """His missiles in flight of class `missile` (all of them when the look did not say their classes)."""
    if not acting.kinds:
        return acting.flying if missile == rules.INFERNO_MISSILE else ()
    return tuple(flight for flight, kind in zip(acting.flying, acting.kinds, strict=False) if kind == missile)


def _rings(acting: Acting) -> list[float]:
    """The radii of his nova rings in flight: the missiles of a ring stand at one distance from him."""
    radii = sorted(math.dist(acting.at, at) for at, _ in _kind(acting, rules.NOVA_MISSILE))
    found: list[float] = []
    for r in radii:
        if not found or r - found[-1] > 2 * CONTACT:
            found.append(r)
    return found


def exposure(
    acting: Acting,
    legs: Legs,
    *,
    seen: bool = True,
    companions: int = 2,
    resists: Mapping[str, float] | None = None,
) -> tuple[Part, ...]:
    """His acts over the character's `legs`, in raw points: the act under way (an inferno rolled out against the way,
    a nova ring and cold missiles in flight, a nova or a fan about to be let go) and the casts to come at the way's
    last place for the time left after it. `seen`, `companions` and `resists` are not weighed: his think is not read
    (sim/baal.py), so neither his sight nor whom he favours is known beyond the nearest."""
    way = Way.along(legs)
    total = way.frames * FRAME
    here = legs[0][0]
    found: list[Part] = []
    busy = 0.0  # seconds of the way the act under way holds him
    # -- the inferno: missiles in flight, and those still to be made while he is in its sequence
    flying = _kind(acting, rules.INFERNO_MISSILE)
    births: list[int] = []
    chance = 1.0
    if acting.mode == SQ:
        births = [b - acting.frames for b in rules.inferno_births(0) if b - acting.frames > 0]
        if flying and _aimed_at(acting.at, flying, here) is None:
            births = []  # they fly at another: those to come follow it
        elif not flying:
            chance = AT_CHARACTER
        busy = max(0, rules.MODE_FRAMES['SQ'] - acting.frames) * FRAME
    now = stream_points(acting.at, births, flying, way)
    if now > 0:
        found.append(Part(1.0, _split(rules.INFERNO, now), 0.0, total, chance))
    # -- nova rings and cold missiles in flight
    for radius in _rings(acting):
        points = ring_points(acting.at, radius, way)
        if points > 0:
            found.append(Part(1.0, _split(rules.NOVA, points), 0.0, total, 1.0))
    cold = cold_points(acting.at, _kind(acting, rules.COLD_MAKER), way)
    if cold > 0:
        found.append(Part(1.0, _split(rules.COLD, cold), 0.0, total, 1.0))
    # -- a nova or a fan about to be let go
    if acting.mode == S3 and acting.frames < rules.RELEASE['S3'] and not _rings(acting):
        release = rules.RELEASE['S3'] - acting.frames
        if math.dist(acting.at, way.at(release)) <= rules.nova_reach() + CONTACT:
            points = ring_points(acting.at, -rules.NOVA_STEP * release, way)
            if points > 0:
                found.append(Part(1.0, _split(rules.NOVA, points), 0.0, total, 1 - rules.CURSE_SHARE))
        busy = max(0, rules.MODE_FRAMES['S3'] - acting.frames) * FRAME
    if acting.mode == A1 and acting.frames < rules.RELEASE['A1'] and not _kind(acting, rules.COLD_MAKER):
        points = cold_fan(acting.at, way, rules.RELEASE['A1'] - acting.frames)
        if points > 0:
            found.append(Part(1.0, _split(rules.COLD, points), 0.0, total, AT_CHARACTER * (1 - rules.TELEPORT_SHARE)))
        busy = max(0, rules.MODE_FRAMES['A1'] - acting.frames) * FRAME
    # -- the casts to come at the last place
    place = legs[-1][0]
    distance = math.dist(acting.at, place)
    left = max(total - busy - rules.DELAY * FRAME, 0.0)
    rates, whole = rules.rates(), standing(distance)
    for act, skill in (('inferno', rules.INFERNO), ('nova', rules.NOVA), ('cold', rules.COLD)):
        casts = rates[act] * left
        if casts > 0 and whole[act] > 0:
            found.append(Part(casts, _split(skill, whole[act]), total - left, total, AT_CHARACTER))
    return tuple(found)


def offered(acting: Acting, here: Point) -> tuple[tuple[Point, str], ...]:
    """Places out of his inferno while it is under way and the character within its reach: on the line from him
    through the character just beyond the reach (out of every missile still to come: each lives 19 frames), then,
    while its missiles fly at the character, across their line (out of those in flight). Nothing for his nova (it
    outruns a walk) or his cold missiles."""
    flying = _kind(acting, rules.INFERNO_MISSILE)
    if acting.mode != SQ and not flying:
        return ()
    gap = math.dist(acting.at, here)
    reach = rules.inferno_reach(_level())
    if gap > reach + CONTACT or gap < 1e-6:
        return ()
    heading = _aimed_at(acting.at, flying, here)
    if flying and heading is None:
        return ()  # they fly at another
    found: list[tuple[Point, str]] = []
    out = reach + OUT
    toward = math.atan2(here[1] - acting.at[1], here[0] - acting.at[0])
    place = (acting.at[0] + out * math.cos(toward), acting.at[1] + out * math.sin(toward))
    found.append((place, "out of Baal's inferno"))
    if heading is not None:
        for step in ACROSS:
            for side in (1, -1):
                turn = heading + side * step / gap
                place = (acting.at[0] + gap * math.cos(turn), acting.at[1] + gap * math.sin(turn))
                found.append((place, "across Baal's inferno"))
    return tuple(found)


THREAT = Threat(frozenset({rules.INFERNO_MISSILE, rules.NOVA_MISSILE, rules.COLD_MAKER}), exposure, offered)


def threat_of(txt: int) -> Threat | None:
    """His model for a monstats row that casts his skills (sim/baal.py `casts_baals`); None otherwise."""
    return THREAT if rules.casts_baals(txt) else None
