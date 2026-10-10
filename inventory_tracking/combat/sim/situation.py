"""A situation cut from a take (combat/plan.md stage 4): the character's recorded positions, the
monsters' recorded paths (open loop: they move as they did, whatever the simulated damage), the
companions' recorded paths (the mercenary and the pets, whose damage the engine models as a rate),
the recorded casts with their focal points, and the recorded kills to compare with.
"""

import bisect
import gzip
import json
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from inventory_tracking.combat.mechanics.damage import DAMAGE
from inventory_tracking.combat.mechanics.echoing_strike import focal_point
from inventory_tracking.combat.mechanics.hits import hostiles_by_frame, pointer_focal
from inventory_tracking.combat.mechanics.tables import monster_points, points_of
from inventory_tracking.combat.mechanics.validate import full_casts
from inventory_tracking.combat.policy import walls
from inventory_tracking.combat.takes import LIFE_SCALE, Take, ground_under_pointer, monsters_of, player_of
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.model import Ground, Walkable
from inventory_tracking.macros.routines import BODY_LIFT


Point = tuple[float, float]
STRIKE_BUTTON = 3  # the right mouse button holds Echoing Strike (the takes' manifests: right_skill 388)


@dataclass
class MonsterTrack:
    unit: int
    txt: int
    points: float  # life points at full health (the mean of the type's range)
    path: dict[int, Point] = field(default_factory=dict)  # frame -> recorded position while alive and hostile
    life_at_start: float = 1.0  # fraction of the points when the situation starts
    recorded_death: int | None = None  # frame of the recorded kill event, if any
    elite: bool = False  # a unique, champion or super unique (the type flags)

    @property
    def first(self) -> int:
        return min(self.path)

    @property
    def last(self) -> int:
        return max(self.path)


@dataclass
class CompanionTrack:
    unit: int
    txt: int
    path: dict[int, Point] = field(default_factory=dict)  # frame -> recorded position while alive


@dataclass
class Cast:
    frame: int  # the blades' first frame
    pointer: Point | None  # the ground under the pointer POINTER_LAG frames earlier (what a policy knows)
    fitted: Point  # the focal point fitted from the recorded blades


@dataclass
class Situation:
    start: int
    end: int
    area: int
    aspect: float
    player: dict[int, Point]
    monsters: dict[int, MonsterTrack]
    casts: list[Cast]
    recorded_damage: float  # points of recorded life drops on hostiles within the window
    companions: dict[int, CompanionTrack] = field(default_factory=dict)
    unknown_types: int = 0  # monsters without a monstats row, given the area level's points at 100%
    marks: list[tuple[int, int]] = field(default_factory=list)  # (frame, monster unit) of each Death Mark cast
    modes: dict[int, int] = field(default_factory=dict)  # frame -> the character's recorded mode (running, casting...)
    presses: list[tuple[int, bool]] = field(default_factory=list)  # (frame, down) of the strike button
    pointer: dict[int, Point] = field(default_factory=dict)  # frame -> the ground under the recorded pointer
    ground: Ground | None = None  # the level's walkable grids (level.json beside the take), when the guide had them
    doors: dict[int, tuple[Door, ...]] = field(default_factory=dict)  # frame -> the door units seen then
    drops: dict[int, list[tuple[int, float]]] = field(default_factory=dict)  # monster unit -> [(frame, points lost)]

    def __post_init__(self) -> None:
        self.player_frames = sorted(self.player)

    def blocked_at(self, frame: int) -> Callable[[Point], bool] | None:
        """Whether a point is a wall for a blade at `frame` (policy.walls: the flight layer, unread
        cells, the doors closed then); None without walls or doors."""
        return walls(self.ground, self.doors.get(frame, ()))

    def player_at(self, frame: int) -> Point:
        """The character's recorded position at `frame`, else the last one before it."""
        if frame in self.player:
            return self.player[frame]
        index = bisect.bisect_right(self.player_frames, frame)
        return self.player[self.player_frames[max(index - 1, 0)]]

    @property
    def seconds(self) -> float:
        return (self.end - self.start) / 25.0


def load_ground(take: Take) -> Ground | None:
    """The walkable grids the recorder copied beside the take (level.json, gzipped in a trimmed take), if any."""
    path = take.directory / 'level.json'
    packed = take.directory / 'level.json.gz'
    if path.exists():
        level = json.loads(path.read_text())
    elif packed.exists():
        with gzip.open(packed, 'rt', encoding='utf-8') as handle:
            level = json.load(handle)
    else:
        return None
    grids = tuple(Walkable(**grid) for grid in level.get('ground', ()))
    return Ground(grids) if grids else None


def mark_key_code(take: Take) -> int | None:
    """The key code of Death Mark's key in the take's manifest (data/damage.json `death_mark.key`)."""
    wanted = json.loads(DAMAGE.read_text()).get('death_mark', {}).get('key', 'd')
    for code, name in take.manifest.get('keys', {}).items():
        if name == wanted:
            return int(code)
    return None


def death_marks(take: Take, frames, hostiles, aspect: float, radius: float = 4.0) -> list[tuple[int, int]]:
    """(frame, monster unit) per press of Death Mark's key: the live hostile nearest the unit drawn under
    the pointer (its body, BODY_LIFT above its feet) within `radius`, if any."""
    code = mark_key_code(take)
    if code is None:
        return []
    by_n = {f['n']: f for f in frames}
    frame_of = {f['t']: f['n'] for f in take.frames}
    found: list[tuple[int, int]] = []
    for event in take.events:
        if event['event'] != 'keys' or code not in event.get('down', ()):
            continue
        n = frame_of.get(event['t'])
        if n is None or n not in by_n:
            continue
        feet = ground_under_pointer(by_n[n], aspect, BODY_LIFT)
        if feet is None:
            continue
        near = [(math.dist(feet, where), int(unit)) for unit, where in hostiles.get(n, {}).items()]
        if near and min(near)[0] <= radius:
            found.append((n, min(near)[1]))
    return found


def cut(take: Take, start: int | None = None, end: int | None = None, area: int | None = None) -> Situation:
    """The situation between frame numbers `start` and `end` (the whole take by default); `area`
    defaults to the take's."""
    frames = [f for f in take.frames if (start is None or f['n'] >= start) and (end is None or f['n'] <= end)]
    if not frames:
        raise ValueError('no frames in the window')
    area = int(take.manifest.get('area', 108)) if area is None else area
    start, end = frames[0]['n'], frames[-1]['n']
    rect = next((f['rect'] for f in take.frames if f.get('rect')), [0, 0, 2560, 1418])
    aspect = rect[2] / rect[3]
    by_n = {f['n']: f for f in take.frames}
    players = {f['n']: found for f in frames if (found := player_of(f)) is not None}
    player = {n: found.at for n, found in players.items()}
    modes = {n: found.mode for n, found in players.items()}
    pointer = {f['n']: ground for f in frames if (ground := ground_under_pointer(f, aspect)) is not None}
    hostiles = hostiles_by_frame(frames)
    monsters: dict[int, MonsterTrack] = {}
    companions: dict[int, CompanionTrack] = {}
    unknown = 0
    for f in frames:
        for m in monsters_of(f):
            if m.companion:
                companions.setdefault(m.unit, CompanionTrack(m.unit, m.txt)).path[f['n']] = m.at
            if m.hostile:
                track = monsters.get(m.unit)
                if track is None:
                    unknown += monster_points(m.txt, area) is None
                    track = MonsterTrack(m.unit, m.txt, points_of(m.txt, area), life_at_start=m.life_share)
                    track.elite = m.elite
                    monsters[m.unit] = track
                track.path[f['n']] = m.at
    frame_of = {f['t']: f['n'] for f in take.frames}
    damage = 0.0
    drops: dict[int, list[tuple[int, float]]] = {}
    for event in take.events:
        n = frame_of.get(event['t'])
        if n is None or not start <= n <= end:
            continue
        if event['event'] == 'kill' and event['unit'] in monsters:
            monsters[event['unit']].recorded_death = n
        elif event['event'] == 'hit' and event['unit'] in monsters:
            lost = (event['life'][0] - event['life'][1]) / LIFE_SCALE * monsters[event['unit']].points
            damage += lost
            drops.setdefault(event['unit'], []).append((n, lost))
    txt_ids = {m['unit_id']: m['txt_id'] for m in take.missiles} or None
    casts = []
    for n, blades in full_casts(take.frames, txt_ids, least_frames=1):
        if start <= n <= end and n in players:
            casts.append(Cast(n, pointer_focal(by_n, n, aspect), focal_point(blades)))
    marks = death_marks(take, frames, hostiles, aspect)
    ground = load_ground(take)
    doors = {
        f['n']: tuple(Door(d[0], d[1], d[2], float(d[3]), float(d[4])) for d in f['d']) for f in frames if f.get('d')
    }
    presses = [
        (frame_of[e['t']], bool(e['down']))
        for e in take.events
        if e['event'] == 'button'
        and e['button'] == STRIKE_BUTTON
        and e['t'] in frame_of
        and start <= frame_of[e['t']] <= end
    ]
    return Situation(
        start, end, area, aspect, player, monsters, casts, damage, companions, unknown, marks, modes, presses, pointer,
        ground, doors, drops,
    )  # fmt: skip


def describe(situation: Situation) -> dict[str, Any]:
    return {
        'frames': [situation.start, situation.end],
        'seconds': round(situation.seconds, 1),
        'monsters': len(situation.monsters),
        'recorded_kills': sum(1 for t in situation.monsters.values() if t.recorded_death is not None),
        'casts': len(situation.casts),
        'companions': sorted({t.txt for t in situation.companions.values()}),
        'unknown_types': situation.unknown_types,
        'death_marks': len(situation.marks),
        'walls': situation.ground is not None and len(situation.ground) > 0,
        'door_frames': len(situation.doors),
        'recorded_damage_points': round(situation.recorded_damage),
    }
