"""Diablo's red lightning, priced for a place and a way there: what a decision loop needs to choose a stand the stream
misses (rca/2026-10-13/diablo.md section 5). The rules are sim/diablo.py's (the client's think and the stream as
read in it and checked on the takes); nothing here is fitted to a tactic.

What the stream is, in the terms the price needs: from the 10th frame of his SC mode one missile a frame, 39 in all,
each flying at **where his target stands in the frame it is made**, STREAM_STEP a frame for `missile_life` frames,
through every body; a body within CONTACT of a missile loses `rate` of the missile's points, once in `every`
frames from that missile. So a character that stands still is hit by every missile (two hits each, about 190 points
a cast at this character's resistances); one that leaves the line is missed by every missile already made, and the
next ones reach it only after the flight from Diablo to its new place (a frame per STREAM_STEP units: 17 frames at
15 units, 25 at 22).

Two parts are priced:

- **the stream under way** (`Stream`: his mode is SC and how many frames ago it began, or the missiles in flight):
  its remaining missiles rolled out frame by frame against the character's way (`Way`), each aimed at where the way
  has the character at that missile's birth;
- **casts to come**: his lightning chance per think at the place (sim/diablo.py `weights`: in melee, in sight,
  the distance less size against LIGHTNING_RANGE, the character's fire against lightning resistance) times his
  thinks a second (the weights' mean action length plus `aidel`), times a standing cast's points at that distance.
  A stand beyond LIGHTNING_RANGE or out of his sight prices no future stream at all.

The points are the expected raw points of each kind through `Guard` (a physical pool, taken first) and the
resistances (`stopped`: the share of each kind the character stops), as combat/harm.py takes a blow.
"""

import itertools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache, lru_cache

from inventory_tracking.combat.sim import diablo as rules
from inventory_tracking.combat.sim.casters import CONTACT
from inventory_tracking.combat.threats import Acting, Legs, Lingering, Lying, Part, Threat
from inventory_tracking.levels.geometry import Point


FRAME = 1 / 25  # seconds a game frame
TXT = 243  # monstats `diablo`
MODE = 7  # monmode.txt SC: the mode of his lightning (his row's Sk1mode), as the client reads it of the unit
WALKS = 25.0  # units a second: two places of a way farther apart than this in their time are a jump between them
AIMED = 3.0  # units: a missile whose line passes this near the character was made at it (his target is it)


@dataclass(frozen=True)
class Stream:
    """His lightning cast as a look sees it: where he stands, how many frames ago his SC mode began (the client's
    mode and the frame it was first seen in it), and the missiles 172 already in flight: (where, heading in radians).
    `age` None: he is not casting it."""

    at: Point
    age: int | None = None
    flying: tuple[tuple[Point, float], ...] = ()


@dataclass(frozen=True)
class Way:
    """Where the character is over the next frames: (place, seconds there), walked straight between the places
    over `moving` seconds each (0: a jump). combat/harm.py's path ((place, dwell, hands), ...) in other words."""

    legs: tuple[tuple[Point, float, float], ...]  # (place, seconds to get there from the last one, seconds there)

    def at(self, frame: int) -> Point:
        t = frame * FRAME
        here = self.legs[0][0]
        for place, moving, dwell in self.legs:
            if t < moving:
                share = t / moving if moving > 0 else 1.0
                return (here[0] + (place[0] - here[0]) * share, here[1] + (place[1] - here[1]) * share)
            t -= moving
            if t < dwell:
                return place
            t -= dwell
            here = place
        return here

    @property
    def frames(self) -> int:
        return math.ceil(sum(moving + dwell for _, moving, dwell in self.legs) / FRAME)

    @classmethod
    def stand(cls, place: Point, seconds: float) -> Way:
        return cls(((place, 0.0, seconds),))

    @classmethod
    def along(cls, legs: Legs) -> Way:
        """The way of a decision loop's path ((place, seconds), ...): the first place stood at for its seconds, each
        next one walked to over its seconds, or jumped to and stood at when it is farther than a walk in that time
        (WALKS: a hop, a teleport)."""
        found = [(legs[0][0], 0.0, legs[0][1])]
        for (before, _), (place, seconds) in itertools.pairwise(legs):
            walked = math.dist(before, place) <= WALKS * seconds
            found.append((place, seconds, 0.0) if walked else (place, 0.0, seconds))
        return cls(tuple(found))


@dataclass(frozen=True)
class Protection:
    """The character's side: the share of each kind it stops (resistances after the cap) and a physical pool."""

    stopped: Mapping[str, float] = field(default_factory=dict)
    pool: float = 0.0


NONE = Protection()  # nothing stopped, no pool


@cache
def _hit() -> dict[str, float]:
    """The expected raw points of one contact of a missile 172 (its mean roll x `rate`), by kind."""
    level = rules.skill_level(TXT, 1)
    share = rules.rate(rules.LIGHTNING_MISSILE)
    return {
        kind: (low + high) / 2 * share for kind, (low, high) in rules.points(rules.LIGHTNING_MISSILE, level).items()
    }


def _through(raw: Mapping[str, float], protection: Protection, pool: float) -> tuple[float, float]:
    """Points left of `raw` after the pool (physical) and the resistances; the pool left."""
    total = 0.0
    for kind, points in raw.items():
        if kind == 'physical' and pool > 0:
            taken = min(pool, points)
            pool -= taken
            points -= taken
        total += points * (1 - protection.stopped.get(kind, 0.0))
    return total, pool


def stream_points(stream: Stream, way: Way, protection: Protection = NONE) -> float:
    """The points the stream under way takes from a character on `way` (0 when he is not casting): its missiles in
    flight and those still to come, each made at its frame aimed at where `way` has the character then."""
    if stream.age is None and not stream.flying:
        return 0.0
    level = rules.skill_level(TXT, 1)
    life = rules.missile_life(level)
    every = rules.every(rules.LIGHTNING_MISSILE)
    step = rules.STREAM_STEP
    # (x, y, dx, dy, frames left, frame of its last hit)
    missiles: list[list[float]] = [
        [at[0], at[1], math.cos(heading), math.sin(heading), float(life), -1e9] for at, heading in stream.flying
    ]
    births: list[int] = []
    if stream.age is not None:
        first = rules.RELEASE['SC']
        made = [k - stream.age for k in range(first, first + rules.STREAM_MISSILES)]
        births = [b for b in made if b >= 0]
        if stream.flying:
            births = [b for b in births if b > 0]  # the missile of this frame is among those seen
        else:
            # Not given the missiles in flight: those made already are taken to have gone at where the character
            # stands now (the way's start), `-b` frames on their way.
            start = way.at(0)
            gap = math.dist(stream.at, start) or 1.0
            dx, dy = (start[0] - stream.at[0]) / gap, (start[1] - stream.at[1]) / gap
            for b in made:
                if b < 0 and -b < life:
                    flown = -b * step
                    missiles.append([stream.at[0] + dx * flown, stream.at[1] + dy * flown, dx, dy, life + b, -1e9])
    hit, pool, total = _hit(), protection.pool, 0.0
    horizon = min(way.frames, max(births, default=0) + life + 1)
    for frame in range(horizon):
        body = way.at(frame)
        if frame in births:
            gap = math.dist(stream.at, body) or 1.0
            missiles.append(
                [stream.at[0], stream.at[1], (body[0] - stream.at[0]) / gap, (body[1] - stream.at[1]) / gap, life, -1e9]
            )
        for m in missiles:
            if m[4] <= 0:
                continue
            m[0] += m[2] * step
            m[1] += m[3] * step
            m[4] -= 1
            if math.dist((m[0], m[1]), body) <= CONTACT and frame - m[5] >= every:
                m[5] = frame
                points, pool = _through(hit, protection, pool)
                total += points
    return total


def standing_cast(distance: float, protection: Protection = NONE) -> float:
    """The points a whole stream takes from a character standing `distance` units from him all through it."""
    if protection == NONE:
        return _standing_raw(round(distance * 2))
    return stream_points(Stream((0.0, 0.0), age=0), Way.stand((distance, 0.0), 4.0), protection)


@lru_cache(maxsize=512)
def _standing_raw(halves: int) -> float:
    """A standing cast's raw points at `halves` half units (a decision loop asks it at every look)."""
    return stream_points(Stream((0.0, 0.0), age=0), Way.stand((halves / 2, 0.0), 4.0), NONE)


def _action_frames(index: int) -> int:
    """Frames one action of his keeps him from his next think (sim/diablo.py's modes plus `aidel` 12)."""
    delay = int(float((rules.row(TXT) or {}).get('aidel(H)') or 15))
    if index == rules.IDLE:
        return rules.IDLE_FRAMES
    slot = rules.SLOTS.get(index)
    if slot is not None:
        mode = (rules.row(TXT) or {}).get(f'Sk{slot}mode', 'S1')
        return rules.MODE_FRAMES.get(mode, 20) + delay
    mode = {rules.SWING: 'A1', rules.SMASH: 'A2', rules.POSE: 'S4'}.get(index)
    return (rules.MODE_FRAMES[mode] if mode else 0) + delay


def lightning_rate(sight: rules.Sight) -> float:
    """His lightning casts a second while what he weighs is `sight`: the chance of the action at a think over the
    mean frames an action takes."""
    found = rules.weights(sight)
    total = sum(found)
    if total <= 0 or not found[rules.LIGHTNING]:
        return 0.0
    mean = sum(w * _action_frames(i) for i, w in enumerate(found)) / total
    return found[rules.LIGHTNING] / total * 25 / mean


def sight_at(
    diablo: Point, place: Point, *, seen: bool = True, companions: int = 2, resists: Mapping[str, float] | None = None
) -> rules.Sight:
    """What his think weighs of a character at `place` (sim/diablo.py `Sight`); the home point is not priced."""
    resists = resists or rules.CHARACTER_RESISTS
    return rules.Sight(
        melee=math.dist(diablo, place) <= rules.REACH,
        seen=seen,
        away=rules.less_size(diablo, place),
        fire=resists.get('fire', 0.0),
        lightning=resists.get('lightning', 0.0),
        candidates=1 + companions,
    )


def future_points(
    diablo: Point,
    place: Point,
    seconds: float,
    protection: Protection = NONE,
    *,
    seen: bool = True,
    companions: int = 2,
    resists: Mapping[str, float] | None = None,
) -> float:
    """The expected points of the casts he begins during `seconds` at a character standing at `place`: his rate there
    times a standing cast's points, for the casts whose missiles reach it within the time (the first lands RELEASE
    plus the flight after the cast's start)."""
    rate = lightning_rate(sight_at(diablo, place, seen=seen, companions=companions, resists=resists))
    if rate <= 0:
        return 0.0
    lead = (rules.RELEASE['SC'] + math.dist(diablo, place) / rules.STREAM_STEP) * FRAME
    return rate * max(0.0, seconds - lead) * standing_cast(math.dist(diablo, place), protection)


def price(
    stream: Stream,
    way: Way,
    protection: Protection = NONE,
    *,
    seen: bool = True,
    companions: int = 2,
    resists: Mapping[str, float] | None = None,
) -> float:
    """The lightning's expected points over `way`: the stream under way, then the casts to come at its last place
    for the time left after that stream is over."""
    now = stream_points(stream, way, protection)
    place = way.legs[-1][0]
    left = way.frames * FRAME
    if stream.age is not None:
        left -= max(0, rules.MODE_FRAMES['SC'] - stream.age) * FRAME
    later = future_points(
        stream.at, place, max(left, 0.0), protection, seen=seen, companions=companions, resists=resists
    )
    return now + later


def escapes(diablo: Point, here: Point, steps: Sequence[float] = (4.0, 8.0), aim: float | None = None) -> list[Point]:
    """Places the stream's geometry offers: across the line from him to the character (`aim`: the line his missiles
    in flight go along, in radians), either side, `steps` units off it at the same distance from him (where the
    missiles in flight do not pass)."""
    dx, dy = here[0] - diablo[0], here[1] - diablo[1]
    gap = math.hypot(dx, dy) or 1.0
    angle = math.atan2(dy, dx) if aim is None else aim
    found = []
    for step in steps:
        for side in (1, -1):
            # Round him by `step` units of arc: the same distance (the strike's reach kept), off the line.
            turn = angle + side * step / gap
            found.append((diablo[0] + gap * math.cos(turn), diablo[1] + gap * math.sin(turn)))
    return found


# -- the decision loop's model (combat/threats `Threat`: combat/harm.py prices it, macros/safety.py offers its escapes)


def _shares() -> dict[str, float]:
    """Each kind's share of a missile's raw points (`_hit`): a price in points is split by these."""
    hit = _hit()
    total = sum(hit.values()) or 1.0
    return {kind: points / total for kind, points in hit.items()}


def _split(points: float) -> tuple[tuple[str, float], ...]:
    return tuple((kind, points * share) for kind, share in _shares().items())


def _stream(acting: Acting, here: Point) -> tuple[Stream, float]:
    """The stream under way as the look shows it, and the chance its missiles still to come are made at the
    character. His SC mode's age is the frames since the look first saw him in it, or, when his missiles are in
    flight, the frames since the first was made (the farthest has flown that far), whichever is more. When the
    newest missile's line passes the character he aims at it: the rest of the cast comes at it. When it passes
    elsewhere he aims at another (a companion): only the missiles in flight are priced. With none yet (the first
    ten frames) the target is not known: his share of thinks on the character (sim/diablo.py CHARACTER_SHARE)."""
    if acting.mode != MODE:
        return Stream(acting.at, None, acting.flying), 1.0
    age = acting.frames
    if acting.flying:
        flown = max(math.dist(acting.at, at) for at, _ in acting.flying) / rules.STREAM_STEP
        age = max(age, rules.RELEASE['SC'] + math.floor(flown))
        if _aim(acting, here) is None:
            return Stream(acting.at, None, acting.flying), 1.0
        return Stream(acting.at, age, acting.flying), 1.0
    return Stream(acting.at, age, ()), rules.CHARACTER_SHARE


def _aim(acting: Acting, here: Point) -> float | None:
    """The heading of his newest missile in flight when its line passes the character (he aims at it); None with
    none in flight, or when it passes elsewhere (he aims at another)."""
    if not acting.flying:
        return None
    newest, heading = min(acting.flying, key=lambda flight: math.dist(acting.at, flight[0]))
    dx, dy = here[0] - newest[0], here[1] - newest[1]
    ahead = dx * math.cos(heading) + dy * math.sin(heading)
    off = abs(dy * math.cos(heading) - dx * math.sin(heading))
    return None if ahead < -CONTACT or off > AIMED else heading


def exposure(
    acting: Acting,
    legs: Legs,
    *,
    seen: bool = True,
    companions: int = 2,
    resists: Mapping[str, float] | None = None,
) -> tuple[Part, ...]:
    """His lightning over the character's `legs`, in raw points: the stream under way (one event: the missiles in
    flight and those still to come of this cast, rolled out against the way) and the casts to come at the way's
    last place for the time left after it (`casts` an expected count, a standing cast's points each; his chance to
    aim at the character). His wall is priced where it lies (`WALL`, below), his melee and ring not at all. Tried
    and left out
    (rca/2026-10-13/diablo.md "Hooked in"): pricing the stream to its end rather than over the common span; in the
    arena it took more lightning (the step a stream's start then looks useless, and the strike gap allows one step).
    """
    way = Way.along(legs)
    stream, chance = _stream(acting, legs[0][0])
    total = way.frames * FRAME
    found: list[Part] = []
    now = stream_points(stream, way)
    if now > 0:
        found.append(Part(1.0, _split(now), 0.0, total, chance))
    place = legs[-1][0]
    left = total
    if stream.age is not None:
        left -= max(0, rules.MODE_FRAMES['SC'] - stream.age) * FRAME
    rate = lightning_rate(sight_at(acting.at, place, seen=seen, companions=companions, resists=resists))
    distance = math.dist(acting.at, place)
    lead = (rules.RELEASE['SC'] + distance / rules.STREAM_STEP) * FRAME
    casts = rate * max(0.0, left - lead)
    if casts > 0:
        found.append(Part(casts, _split(standing_cast(distance)), total - left + lead, total, rules.CHARACTER_SHARE))
    return tuple(found)


def offered(acting: Acting, here: Point) -> tuple[tuple[Point, str], ...]:
    """The across-the-line places (`escapes`) while his missiles fly at the character: across the line of the newest
    (the stream's aim). None before a missile flies, nor while they fly at another: each missile goes at where his
    target stands when it is made, so a step before the stream is under way only moves where it arrives (the games of
    00:25 and 06:05 on 2026-10-14: four steps at his cast's start, each followed by a hit at the new place;
    rca/2026-10-14/run-0305-findings.md §5.2)."""
    heading = _aim(acting, here)
    if heading is None:
        return ()
    return tuple((place, "across Diablo's lightning") for place in escapes(acting.at, here, aim=heading))


# -- his fire wall: what lies on the ground after the cast, and after his death (combat/threats `Lingering`) ---------
# The game of 06:05 on 2026-10-14 (rca/2026-10-14/run-0305-findings.md §5.6): ten makers 179 one second before he died,
# 422 flames 180 for three seconds after; the loot walk to his Amulet went through them (266 life, the mercenary 96 %
# to 43 %), and the 02:19 game's to his Hel Rune the same (261, the mercenary to 17 %). His rules are sim/diablo.py's:
# a maker goes WALL_STEP a frame for WALL_LIFE frames from where he stood and leaves a flame where it is each frame;
# a flame stands FLAME_LIFE frames and takes `rate` of its points from every body within CONTACT each frame.


@cache
def _flame() -> dict[str, float]:
    """The expected raw points one flame 180 takes in a frame of contact (its mean roll x `rate`), by kind."""
    level = rules.skill_level(TXT, rules.SLOTS[rules.WALL])
    share = rules.rate(rules.WALL_FLAME)
    return {kind: (low + high) / 2 * share for kind, (low, high) in rules.points(rules.WALL_FLAME, level).items()}


def wall_read(missile: int, at: Point, caster: Point | None, seen: float) -> Lying:
    """A missile of his wall as a look reads it. A maker leaves him straight (sim/diablo.py `wall_headings`): its way
    is the line from where he stood, and its age the frames that line took at WALL_STEP a frame (or the frames it has
    been read, whichever is more). A flame stands: its age is the frames it has been read (0 when new: as if made
    now, the longest it can last). A maker with no caster known is priced as a flame where it is."""
    frames = round(seen / FRAME)
    if missile == rules.WALL_MAKER and caster is not None:
        gap = math.dist(caster, at)
        if gap > 1e-6:
            heading = math.atan2(at[1] - caster[1], at[0] - caster[0])
            return Lying(missile, at, heading, max(frames, round(gap / rules.WALL_STEP)))
    return Lying(missile, at, None, frames)


def _flames(lying: Sequence[Lying]) -> list[tuple[float, float, int, int]]:
    """Every flame that stands within the next frames: (x, y, its first frame, the frame it is gone), from frame 0 of
    the look: those read, and those the makers read will leave on their way."""
    found: list[tuple[float, float, int, int]] = []
    for item in lying:
        if item.missile == rules.WALL_MAKER and item.heading is not None:
            dx, dy = math.cos(item.heading) * rules.WALL_STEP, math.sin(item.heading) * rules.WALL_STEP
            for k in range(max(rules.WALL_LIFE - item.age, 0)):
                found.append((item.at[0] + dx * k, item.at[1] + dy * k, k, k + rules.FLAME_LIFE))
        else:
            left = rules.FLAME_LIFE - (item.age if item.missile == rules.WALL_FLAME else 0)
            if left > 0:
                found.append((item.at[0], item.at[1], 0, left))
    return found


def wall_points(lying: Sequence[Lying], way: Way) -> float:
    """The raw points (all kinds, `_flame`'s shares) his wall's flames take from a character on `way`: each frame,
    every flame standing within CONTACT of it."""
    flames = _flames(lying)
    if not flames:
        return 0.0
    bodies = [way.at(frame) for frame in range(way.frames)]
    if not bodies:
        return 0.0
    low_x, high_x = min(b[0] for b in bodies) - CONTACT, max(b[0] for b in bodies) + CONTACT
    low_y, high_y = min(b[1] for b in bodies) - CONTACT, max(b[1] for b in bodies) + CONTACT
    near = [f for f in flames if low_x <= f[0] <= high_x and low_y <= f[1] <= high_y and f[2] < len(bodies)]
    if not near:
        return 0.0
    contacts = 0
    reach = CONTACT * CONTACT
    for frame, (x, y) in enumerate(bodies):
        for fx, fy, first, gone in near:
            if first <= frame < gone and (fx - x) ** 2 + (fy - y) ** 2 <= reach:
                contacts += 1
    return contacts * sum(_flame().values())


def wall_exposure(lying: tuple[Lying, ...], legs: Legs) -> tuple[Part, ...]:
    """His wall's flames over the character's `legs`: one event, in raw points by kind."""
    way = Way.along(legs)
    total = wall_points(lying, way)
    if total <= 0:
        return ()
    flame = _flame()
    whole = sum(flame.values()) or 1.0
    points = tuple((kind, total * value / whole) for kind, value in flame.items())
    return (Part(1.0, points, 0.0, way.frames * FRAME, 1.0),)


def wall_clears(lying: tuple[Lying, ...]) -> float:
    """Seconds until his wall's flames read, and those its makers read will still leave, are gone."""
    return max((gone for _, _, _, gone in _flames(lying)), default=0) * FRAME


WALL_CLEAR = CONTACT + 1.5  # units beyond the outermost maker's line a place out of the wall is offered at


def wall_escapes(lying: tuple[Lying, ...], here: Point) -> tuple[tuple[Point, str], ...]:
    """Places out of his wall: its makers leave where he stood in a fan (the take of 06:05 on 2026-10-14: -33 to 57
    degrees off the line to the character), so a place as far from him as the character, WALL_CLEAR beyond either
    edge of the fan, is off every line; the nearer edge first. None without a maker whose way is known."""
    makers = [item for item in lying if item.missile == rules.WALL_MAKER and item.heading is not None]
    if not makers:
        return ()
    origins = [
        (
            item.at[0] - math.cos(item.heading) * rules.WALL_STEP * item.age,
            item.at[1] - math.sin(item.heading) * rules.WALL_STEP * item.age,
        )
        for item in makers
        if item.heading is not None
    ]
    origin = (sum(o[0] for o in origins) / len(origins), sum(o[1] for o in origins) / len(origins))
    reach = math.dist(origin, here)
    if reach < 1e-6:
        return ()
    toward = math.atan2(here[1] - origin[1], here[0] - origin[0])
    offs = [math.remainder((item.heading or 0.0) - toward, math.tau) for item in makers]
    margin = WALL_CLEAR / reach
    edges = sorted((min(offs) - margin, max(offs) + margin), key=abs)
    return tuple(
        (
            (origin[0] + reach * math.cos(toward + edge), origin[1] + reach * math.sin(toward + edge)),
            "out of Diablo's fire wall",
        )
        for edge in edges
    )


WALL = Lingering(
    frozenset({rules.WALL_MAKER, rules.WALL_FLAME}),
    (rules.WALL_LIFE + rules.FLAME_LIFE) * FRAME,
    wall_read,
    wall_exposure,
    wall_clears,
    wall_escapes,
)
THREAT = Threat(frozenset({rules.LIGHTNING_MISSILE}), exposure, offered, WALL)


def threat_of(txt: int) -> Threat | None:
    """His model for a class of his AI (monstats `AI` Diablo: 243 `diablo`, 333 `diabloclone`); None otherwise."""
    return THREAT if rules.is_diablo(txt) else None
