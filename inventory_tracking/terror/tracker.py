"""Per-game Herald state from the probe's events, and the Terror Zone card text.

Groups (zones.py) count hostile kills together across their levels, each level weighted by
the game's `zone_completion_weight`, with the game's formula (chance.py): a level's rooms
loaded so far stand for its populated rooms, the hostile monsters seen there for those
spawned. Before a level is entered, its part of the article's group mean (split by weight)
stands for its population. Allies carry stat 172 `alignment` != 0 (summons, the mercenary)
and never count. A Herald and its minions all carry stat 367 `heraldtier` (Black Marsh probe,
2026-10-02); the minions also have the minion flag 0x10 in monster data +0x1A (the Herald had
0x08). Both are hostile monsters like any other to the game's counters. The Herald makes the
next tier one above it (5 stays 5) and stores its group's completion, which the next Herald's
progress counts from.

Terrorized or not: Hell Terror Zones give every plain monster one modifier from
desecratedzones.json's `always_unique_mod_pool`, the same for the whole zone ('manahit' 25 in
Black Marsh, 'fast' 6 in the Lut Gholein sewers, 2026-10-02); outside them plain monsters have
none (monster data +0x20, the first modifier; plain = type flags +0x1A == 0). After the
17:30 UTC rotation, sewer monsters seen anew had none. The last few plain sightings per
Terror Zone decide; a Herald marks its zone when no plain monster was seen.

Leaving the game resets everything; a service started mid-game assumes Tier 1 until it sees
a Herald.
"""

from collections import deque
from dataclasses import dataclass, field

from inventory_tracking.levels.geometry import Pointer
from inventory_tracking.native.layout import DEAD_MODES, TILE_UNITS
from inventory_tracking.osd.level_map import MapPoi
from inventory_tracking.terror.chance import Level, group_completion, odds
from inventory_tracking.terror.zones import GROUPS, HeraldGroup, group_of, group_population


ALIGNMENT_STAT = 172
HERALD_TIER_STAT = 367
MAX_TIER = 5
TYPE_FLAGS = 0x1A  # monster data byte
MINION_FLAG = 0x10
# Type flags of a pack leader, from the probe logs (2026-10-02/03): 0x08 unique (Heralds too),
# 0x0c champion, 0x0a super unique, 0x4c ghostly champion; minions carry 0x10 alone.
LEADER_FLAGS = 0x02 | 0x04 | 0x08
FIRST_MODIFIER = 0x20  # monster data byte: first special modifier (monumod.json id)
# desecratedzones.json rotw/hell always_unique_mod_pool: strong, fast, curse, fire, lightning
# (17), cold, manahit, spectral hit (27), and 28 (d2data, 2026-10-02).
TERROR_MODIFIERS = frozenset((5, 6, 7, 9, 17, 18, 25, 27, 28))
TERROR_VOTES = 6  # plain-monster sightings per Terror Zone that decide


@dataclass
class Count:
    """Hostile monsters of one level, or of a whole group."""

    killed: int = 0  # kills this game: these mobs stay dead
    seen: set[int] = field(default_factory=set)  # unit ids


def stat(event, stat_id) -> int:
    return next((raw for _layer, found, raw in event.get('stats') or () if found == stat_id), 0)


def data_byte(event, offset) -> int | None:
    data = event.get('data_hex') or ''
    return int(data[2 * offset : 2 * offset + 2], 16) if len(data) >= 2 * (offset + 1) else None


def is_minion(event) -> bool:
    """Minion flag from first-sight monster data; unreadable data counts as not a minion."""
    data = event.get('data_hex') or ''
    return len(data) >= 2 * (TYPE_FLAGS + 1) and bool(int(data[2 * TYPE_FLAGS : 2 * TYPE_FLAGS + 2], 16) & MINION_FLAG)


def percent(value: float) -> str:
    """One decimal from 1% up, two below it (a single kill's chance is always small)."""
    return f'{value:.1%}' if value >= 0.01 else f'{value:.2%}'


class ZoneTracker:
    def __init__(self):
        self.reset()

    def reset(self):
        self.areas: dict[int, Count] = {}
        self.level_rooms: dict[int, int] = {}  # area -> Room2 count of the level
        self.heralds: list[tuple[int, str]] = []
        self.herald_units: set[int] = set()
        self.allies: set[int] = set()
        self.zones: set[str] = set()  # Terror Zones where a Herald appeared this game
        self.visited: dict[int, set[tuple]] = {}  # area -> bounds of rooms ever loaded
        self.loaded: dict[int, int] = {}  # area -> rooms ever loaded, as the probe counts them
        self.positions: dict[int, tuple[int, int, int]] = {}  # hostile unit id -> (area, x, y), alive
        self.leaders: set[int] = set()  # unique, champion and super unique monsters (not minions)
        self.votes: dict[str, deque[bool]] = {}  # Terror Zone -> recent plain sightings: forced modifier?
        self.live_heralds: dict[int, tuple[int, int, int, int]] = {}  # unit id -> (tier, area, x, y), alive
        self.offsets: dict[str, float] = {}  # group -> completion % when its last Herald appeared

    @property
    def next_tier(self) -> int:
        return min(MAX_TIER, max((tier for tier, _ in self.heralds), default=0) + 1)

    def area_count(self, area: int) -> Count:
        return self.areas.setdefault(area, Count())

    def count(self, name: str) -> Count:
        """A group's totals over its levels."""
        counts = [self.area_count(area) for group in GROUPS if group.name == name for area in group.areas]
        seen = set().union(*(count.seen for count in counts))
        return Count(sum(c.killed for c in counts), seen)

    def levels(self, group: HeraldGroup) -> list[Level]:
        result = []
        for area, weight in zip(group.areas, group.weights, strict=True):
            count, rooms = self.area_count(area), self.level_rooms.get(area)
            prior = group_population(group, rooms) * weight / sum(group.weights)
            populated = max(len(self.visited.get(area, ())), self.loaded.get(area, 0))
            result.append(Level(weight, count.killed, len(count.seen), populated, rooms, prior))
        return result

    def apply(self, events):
        for event in events:
            kind = event['event']
            if kind == 'left_game':
                self.reset()
            elif kind == 'seen':
                self.saw(event)
            elif kind == 'area':
                if event.get('level_rooms'):
                    self.level_rooms[event['area']] = event['level_rooms']
            elif kind == 'rooms':
                self.visited.setdefault(event['area'], set()).update(tuple(b) for b in event.get('bounds', ()))
                self.loaded[event['area']] = max(self.loaded.get(event['area'], 0), event.get('loaded_ever', 0))
            elif kind == 'died':
                group = group_of(event['area'])
                unit_id = event['unit_id']
                self.live_heralds.pop(unit_id, None)
                self.positions.pop(unit_id, None)
                if group and unit_id not in self.allies:
                    self.area_count(event['area']).killed += 1

    def saw(self, event):
        unit_id, group = event['unit_id'], group_of(event['area'])
        if stat(event, ALIGNMENT_STAT):
            self.allies.add(unit_id)
            return
        if group and data_byte(event, TYPE_FLAGS) == 0 and not stat(event, HERALD_TIER_STAT):
            modifier = data_byte(event, FIRST_MODIFIER)
            votes = self.votes.setdefault(group.zone, deque(maxlen=TERROR_VOTES))
            votes.append(modifier in TERROR_MODIFIERS)
        if 'x' in event and event.get('mode') not in DEAD_MODES:  # a corpse seen first is nothing left to kill
            self.positions[unit_id] = (event['area'], event['x'], event['y'])
            if (data_byte(event, TYPE_FLAGS) or 0) & LEADER_FLAGS and not is_minion(event):
                self.leaders.add(unit_id)
        tier = stat(event, HERALD_TIER_STAT)
        if tier:
            self.herald_units.add(unit_id)
            if group and not is_minion(event):
                if event.get('mode') not in DEAD_MODES and 'x' in event:
                    self.live_heralds[unit_id] = (tier, event['area'], event['x'], event['y'])
                self.heralds.append((tier, group.name))
                self.offsets[group.name] = group_completion(self.levels(group))
                self.zones.add(group.zone)
        if group:
            self.area_count(event['area']).seen.add(unit_id)

    def track(self, monsters):
        """Follow live monsters: `monsters` are the units present this pass (terror/monsters.py)."""
        for monster in monsters:
            if monster.unit_id in self.positions:
                area = self.positions[monster.unit_id][0]
                self.positions[monster.unit_id] = (monster.area or area, monster.x, monster.y)
            if monster.unit_id in self.live_heralds:
                tier, area, _x, _y = self.live_heralds[monster.unit_id]
                self.live_heralds[monster.unit_id] = (tier, monster.area or area, monster.x, monster.y)

    def herald_marks(self, area: int) -> list[tuple[int, int, int]]:
        """(tier, x, y) in world units of the Heralds alive in `area`, at their last seen position."""
        return [(tier, x, y) for tier, where, x, y in self.live_heralds.values() if where == area]

    def herald_dots(self, area: int) -> list[MapPoi]:
        return [
            MapPoi(f'Herald T{tier}', 'herald', x / TILE_UNITS, y / TILE_UNITS)
            for tier, x, y in self.herald_marks(area)
        ]

    def map_dots(self, area: int) -> list[MapPoi]:
        """A dot per hostile monster alive in `area` at its last seen position, in tiles: plain
        mobs (minions too), then pack leaders (unique, champion, super unique), then Heralds,
        the drawing order. A dot per monster rather than a tinted room (user, 2026-10-03: big
        rooms hid where the pack was)."""
        mobs, leaders = [], []
        for unit_id, (where, x, y) in self.positions.items():
            if where == area and unit_id not in self.live_heralds:
                if unit_id in self.leaders:
                    leaders.append(MapPoi('unique', 'leader', x / TILE_UNITS, y / TILE_UNITS))
                else:
                    mobs.append(MapPoi('monster', 'mob', x / TILE_UNITS, y / TILE_UNITS))
        return [*mobs, *leaders, *self.herald_dots(area)]

    def visited_rooms(self, area: int) -> set[tuple]:
        """Bounds of the rooms ever loaded in `area`: the map dims the others."""
        return self.visited.get(area, set())

    def terrorized(self, area: int) -> bool | None:
        """The area's Terror Zone by its plain monsters' forced modifier (most of the last few),
        else True once a Herald appeared there this game; None before any evidence."""
        group = group_of(area)
        if group is None:
            return None
        votes = self.votes.get(group.zone)
        if votes:
            return sum(votes) * 2 > len(votes)
        return True if group.zone in self.zones else None

    def lines(self, area: int, *, terrorized: bool | None, position: tuple[int, int] | None = None) -> list[str]:
        group = group_of(area)
        if group is None or terrorized is False:
            return []
        levels = self.levels(group)
        offset = self.offsets.get(group.name, 0.0)
        result = odds(self.next_tier, levels, current=group.areas.index(area), offset=offset)
        killed = sum(level.killed for level in levels)
        seen = ', '.join(f'T{tier}' for tier, _ in self.heralds) or 'none'
        pointers = []
        if position is not None:
            for tier, x, y in self.herald_marks(area):
                pointer = Pointer(f'Herald T{tier} alive', None, x - position[0], y - position[1])
                pointers.append(f'{pointer.arrow}  {pointer.label}: {pointer.compass}')
        lines = [
            f'Terror · {group.name}' + ('' if terrorized else ' (unconfirmed)'),
            *pointers,
            f'Next Herald: Tier {result.tier} · {seen} seen this game',
            f'Killed {killed} / {killed + result.remaining} · {result.remaining} left',
        ]
        # Whole percents round down so a progress never shows a breakpoint not yet passed.
        progress = f'Progress {int(result.completion)}% · breakpoint {round(result.breakpoint)}%'
        if result.kills_to_breakpoint is None:
            lines.append(f'{progress} out of reach: {result.remaining} left give {int(result.reachable)}%')
            return lines
        if result.kills_to_breakpoint:
            # The first kill that can spawn a Herald, counting from the next one.
            lines.append(f'{progress} in {result.kills_to_breakpoint + 1} kills')
            return lines
        lines.append(f'{progress} reached')
        lines.append(f'Next kill {result.next_kill:.2%} · all {result.remaining} left {percent(result.over_remaining)}')
        return lines
