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

A revived monster (Fallen Shamans raise their Fallen: same unit id, 2026-10-03 logs) is one
kill however often it dies (user, 2026-10-03), and gets its map dot back while alive.

Leaving the game resets everything; a service started mid-game assumes Tier 1 until it sees
a Herald, unless the game is one it knows: the state is saved per server game and taken up
again when that game is entered (user, 2026-10-06: the game client restarted and the same game
rejoined showed Tier 1). A game is known by its levels' seeds: the level struct the probe reads
on entering a level has 8 random bytes at +0x1E4 which are the same whenever the same game is
entered and differ between games (probe logs to 2026-10-06: 516 area/seed pairs, shared only
across rejoins and service restarts; the Act/ActMisc seed hashes of levels/research.py read as
constants on this build). Unit ids are taken to stay the same in a rejoined game.
"""

import json
import math
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.levels.geometry import Pointer
from inventory_tracking.native.layout import DEAD_MODES, TILE_UNITS, TOWN_IDS
from inventory_tracking.osd.level_map import MapPoi
from inventory_tracking.terror import elites
from inventory_tracking.terror.chance import Level, group_completion, odds
from inventory_tracking.terror.danger import Pack, Unit, packs, table
from inventory_tracking.terror.zones import GROUPS, HeraldGroup, group_of, group_population


ALIGNMENT_STAT = 172
HERALD_TIER_STAT = 367
MAX_TIER = 5
TYPE_FLAGS = 0x1A  # monster data byte
MINION_FLAG = 0x10
# Type flags of a pack leader, from the probe logs (2026-10-02/03): 0x08 unique (Heralds too),
# 0x0c champion, 0x0a super unique, 0x4c ghostly champion; minions carry 0x10 alone.
LEADER_FLAGS = 0x02 | 0x04 | 0x08
SUPER_FLAG, CHAMPION_FLAG = 0x02, 0x04
# Monster data u16: a super unique's superuniques.txt hcIdx (probe logs to 2026-10-06: 36-38 on the
# seal bosses, 61-65 on Baal's waves, 52 on Pindleskin).
SUPER_ID = 0x2A
FIRST_MODIFIER = 0x20  # monster data byte: first special modifier (monumod.json id)
MODIFIER_SLOTS = 9  # modifier bytes from there on; 0 = none (uniques show 3 in Hell, minions 2)
AURA_MODIFIER = 30  # aura enchanted: the monster's aura is its own
# itemstatcost.txt `modifierlist_skill` / `modifierlist_level`: the aura a monster carries, its own
# or one it stands in (all 1,223 aura-enchanted uniques of the probe logs to 2026-10-06 have them).
AURA_SKILL_STAT, AURA_LEVEL_STAT = 350, 351
# desecratedzones.json rotw/hell always_unique_mod_pool: strong, fast, curse, fire, lightning
# (17), cold, manahit, spectral hit (27), and 28 (d2data, 2026-10-02).
TERROR_MODIFIERS = frozenset((5, 6, 7, 9, 17, 18, 25, 27, 28))
# monstats.json rows without `killable` (d2data, 2026-10-05): townsfolk, critters, traps and
# scenery units such as the Compelling Orb (366), which carries the unique flag and never dies.
UNKILLABLE = frozenset((
    34, 35, 36, 37, 106, 107, 108, 109, 146, 147, 148, 149, 150, 153, 154, 155, 159, 175, 176, 177, 178, 179, 185,
    195, 196, 197, 198, 199, 200, 201, 202, 204, 205, 210, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 244,
    245, 246, 251, 252, 253, 254, 255, 257, 264, 265, 294, 296, 297, 326, 327, 328, 329, 330, 332, 355, 366, 367,
    368, 369, 401, 405, 406, 408, 414, 450, 451, 452, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 527,
    537, 538, 539, 543, 545, 556, 559, 567, 568, 569, 574, 734, 737,
))  # fmt: skip
# The client drops live monsters about 8-24 tiles away; nearer than this (world units) it holds
# them (probe log 2026-10-05: 3 of 1233 live monsters vanished closer).
HELD_RANGE = 40
TERROR_VOTES = 6  # plain-monster sightings per Terror Zone that decide
LEVEL_SEED, LEVEL_SEED_SIZE = 0x1E4, 8  # level struct bytes: the same in a rejoined game
STORED_GAMES = 8  # games kept in the store, the latest last
SAVE_SECONDS = 5.0  # between saves while playing; leaving a game and a Herald always save
# The game's names of those modifiers (monumod.json ids, d2data 2026-10-06): the zone's own line
# under 'Terrorized: <level>' in the game's top-right text.
MODIFIER_NAMES = {
    5: 'Extra Strong',
    6: 'Extra Fast',
    7: 'Cursed',
    9: 'Fire Enchanted',
    17: 'Lightning Enchanted',
    18: 'Cold Enchanted',
    25: 'Mana Burn',
    27: 'Spectral Hit',
    28: 'Stone Skin',
}
# 'Terrorized: 95' at character level 93 (user's screenshot, 2026-10-06): the classic rule,
# character level + 2 up to 96 in Hell. The area's own level as a floor is not applied here.
TERROR_LEVEL_BONUS, TERROR_LEVEL_CAP = 2, 96


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


def modifiers(event) -> tuple[int, ...]:
    data = event.get('data_hex') or ''
    found = bytes.fromhex(data[2 * FIRST_MODIFIER : 2 * (FIRST_MODIFIER + MODIFIER_SLOTS)])
    return tuple(modifier for modifier in found if modifier)


def aura(event) -> tuple[int, int] | None:
    """(skill, level) of the aura a monster showed on first sight; other skills in that stat are none."""
    skill = stat(event, AURA_SKILL_STAT)
    return (skill, stat(event, AURA_LEVEL_STAT) or 1) if skill in table().auras else None


def super_name(event) -> str | None:
    data = event.get('data_hex') or ''
    if len(data) < 2 * (SUPER_ID + 2):
        return None
    found = int.from_bytes(bytes.fromhex(data[2 * SUPER_ID : 2 * SUPER_ID + 4]), 'little')
    return elites.table().supers.get(found)


def is_minion(event) -> bool:
    """Minion flag from first-sight monster data; unreadable data counts as not a minion."""
    data = event.get('data_hex') or ''
    return len(data) >= 2 * (TYPE_FLAGS + 1) and bool(int(data[2 * TYPE_FLAGS : 2 * TYPE_FLAGS + 2], 16) & MINION_FLAG)


def percent(value: float) -> str:
    """One decimal from 1% up, two below it (a single kill's chance is always small)."""
    return f'{value:.1%}' if value >= 0.01 else f'{value:.2%}'


class ZoneTracker:
    def __init__(self, store: Path | None = None, *, clock=time.monotonic):
        self.store, self.clock = store, clock
        self.saved_at = -math.inf
        self.left: dict[int, str] = {}  # the levels of the game just left, until the next level is entered
        self.reset()

    def reset(self):
        self.game_levels: dict[int, str] = {}  # area -> level seed (hex): what this game is known by
        self.restored = False
        self.areas: dict[int, Count] = {}
        self.level_rooms: dict[int, int] = {}  # area -> Room2 count of the level
        self.heralds: list[tuple[int, str]] = []
        self.herald_units: set[int] = set()
        self.allies: set[int] = set()
        self.zones: set[str] = set()  # Terror Zones where a Herald appeared this game
        self.visited: dict[int, set[tuple]] = {}  # area -> bounds of rooms ever loaded
        # area -> bounds of the rooms the player was in or next to: where monsters would have shown
        self.explored: dict[int, set[tuple]] = {}
        self.loaded: dict[int, int] = {}  # area -> rooms ever loaded, as the probe counts them
        self.positions: dict[int, tuple[int, int, int]] = {}  # hostile unit id -> (area, x, y), alive
        self.leaders: set[int] = set()  # unique, champion and super unique monsters (not minions)
        # hostile unit id -> (txt id, modifiers, aura) as first seen: what makes a pack deadly (danger.py)
        self.traits: dict[int, tuple[int, tuple[int, ...], tuple[int, int] | None]] = {}
        self.bands: dict[int, dict[int, str]] = {}  # area -> unit id -> its pack's band on the last pass
        self.player_states: frozenset[int] = frozenset()  # states.txt ids on the player, as last read
        # leader's unit id -> (area, kind, txt id, x, y, name) as first seen: the level's elite groups (elites.py)
        self.elites: dict[int, tuple[int, str, int, int, int, str | None]] = {}
        self.layouts: dict[int, tuple] = {}  # area -> its rooms (levels/model.py Room), from the level guide
        self.lost: dict[int, tuple[int, int | None]] = {}  # unit id -> (area, Herald tier): not where remembered
        self.paths: dict[int, int] = {}  # unit id -> dynamic path address, units in the last walk only
        self.dead: dict[int, int] = {}  # hostile unit id -> area, killed at least once this game
        self.modifiers: dict[str, deque[int]] = {}  # Terror Zone -> recent forced modifiers of plain monsters
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
        heralds = len(self.heralds)
        for event in events:
            kind = event['event']
            if kind == 'left_game':
                self.save()
                self.left = dict(self.game_levels) or self.left
                self.reset()
            elif kind == 'seen':
                self.saw(event)
            elif kind == 'area':
                self.entered(event['area'], event.get('level_hex') or '')
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
                self.paths.pop(unit_id, None)
                self.lost.pop(unit_id, None)
                if group and unit_id not in self.allies and unit_id not in self.dead:
                    self.area_count(event['area']).killed += 1
                if unit_id not in self.allies:
                    self.dead.setdefault(unit_id, event['area'])

        if events and (len(self.heralds) != heralds or self.clock() - self.saved_at >= SAVE_SECONDS):
            self.save()

    def level_read(self, area: int, level_rooms: int | None, level_hex: str):
        """The probe read the level's struct, on entry or after a failed first try."""
        if level_rooms:
            self.level_rooms[area] = level_rooms
        self.entered(area, level_hex)

    def entered(self, area: int, level_hex: str):
        """Take the level's seed as this game's mark; a game known by it continues where it was left."""
        seed = level_hex[2 * LEVEL_SEED : 2 * (LEVEL_SEED + LEVEL_SEED_SIZE)]
        if len(seed) != 2 * LEVEL_SEED_SIZE or not int(seed, 16):
            return
        if self.game_levels.get(area, seed) != seed:  # another game, entered without the leaving being seen
            self.save()
            self.reset()
        self.game_levels[area] = seed
        left, self.left = self.left, {}
        if self.restored:
            return
        games = self.stored_games()
        game = next((g for g in reversed(games) if g['levels'].get(str(area)) == seed), None)
        if game is None and area not in TOWN_IDS and area not in left:
            # A game starts in a town: a level out of town right after "leaving" is the game that was
            # left, behind a loading screen (a waypoint's reads as the menu, probe logs 2026-10-06).
            shared = {str(known): known_seed for known, known_seed in left.items()}.items()
            game = next((g for g in reversed(games) if shared & g['levels'].items()), None)
        if game is None:
            return
        levels, since = self.game_levels, self.state()
        try:
            self.restore(game['state'])
            self.restore(since, merge=True)  # counted before a level of the stored game was entered
        except (KeyError, TypeError, ValueError) as exc:
            LOG.warning('Terror tracker: stored game unreadable: %s', exc)
            self.reset()
        self.game_levels = {int(k): v for k, v in game['levels'].items()} | levels
        self.restored = True
        LOG.info('Terror tracker: game rejoined; Heralds seen %s', self.heralds)

    def stored_games(self) -> list[dict]:
        if self.store is None:
            return []
        try:
            games = json.loads(self.store.read_text(encoding='utf-8'))['games']
            return [game for game in games if isinstance(game.get('levels'), dict) and 'state' in game]
        except OSError, ValueError, KeyError, TypeError, AttributeError:
            return []

    def state(self) -> dict:
        """What a rejoined game continues with; live positions are found again by the probe."""
        return {
            'areas': {area: [count.killed, sorted(count.seen)] for area, count in self.areas.items()},
            'level_rooms': self.level_rooms,
            'heralds': self.heralds,
            'herald_units': sorted(self.herald_units),
            'allies': sorted(self.allies),
            'zones': sorted(self.zones),
            'visited': {area: sorted(rooms) for area, rooms in self.visited.items()},
            'explored': {area: sorted(rooms) for area, rooms in self.explored.items()},
            'loaded': self.loaded,
            'dead': self.dead,
            'votes': {zone: list(votes) for zone, votes in self.votes.items()},
            'modifiers': {zone: list(mods) for zone, mods in self.modifiers.items()},
            'offsets': self.offsets,
            'elites': {unit_id: list(first) for unit_id, first in self.elites.items()},
        }

    def restore(self, state: dict, *, merge: bool = False):
        """Take a stored game's state; with `merge`, add it to what is held (the same game, in two parts)."""
        areas = {int(area): Count(int(killed), set(seen)) for area, (killed, seen) in state['areas'].items()}
        level_rooms = {int(area): int(rooms) for area, rooms in state['level_rooms'].items()}
        heralds = [(int(tier), str(name)) for tier, name in state['heralds']]
        visited = {int(area): {tuple(room) for room in rooms} for area, rooms in state['visited'].items()}
        # Absent in games stored before 2026-10-06: their map starts unshaded.
        explored = {int(area): {tuple(room) for room in rooms} for area, rooms in state.get('explored', {}).items()}
        loaded = {int(area): int(count) for area, count in state['loaded'].items()}
        dead = {int(unit_id): int(area) for unit_id, area in state['dead'].items()}
        votes = {zone: list(votes) for zone, votes in state['votes'].items()}
        modifiers = {zone: list(mods) for zone, mods in state['modifiers'].items()}
        offsets = {str(name): float(offset) for name, offset in state['offsets'].items()}
        # Absent in games stored before 2026-10-06.
        found = {
            int(unit_id): (int(area), str(kind), int(txt_id), int(x), int(y), name)
            for unit_id, (area, kind, txt_id, x, y, name) in state.get('elites', {}).items()
        }
        if not merge:
            self.areas, self.level_rooms, self.heralds, self.loaded, self.dead = {}, {}, [], {}, {}
            self.herald_units, self.allies, self.zones = set(), set(), set()
            self.visited, self.explored, self.votes, self.modifiers, self.offsets, self.elites = {}, {}, {}, {}, {}, {}
        for area, count in areas.items():
            mine = self.area_count(area)
            mine.killed += count.killed
            mine.seen |= count.seen
        self.level_rooms |= level_rooms
        self.heralds += [herald for herald in heralds if herald not in self.heralds]
        self.herald_units |= set(state['herald_units'])
        self.allies |= set(state['allies'])
        self.zones |= set(state['zones'])
        for mine, theirs in ((self.visited, visited), (self.explored, explored)):
            for area, rooms in theirs.items():
                mine.setdefault(area, set()).update(rooms)
        for area, count in loaded.items():
            self.loaded[area] = max(self.loaded.get(area, 0), count)
        self.dead = dead | self.dead
        for mine, theirs in ((self.votes, votes), (self.modifiers, modifiers)):
            for zone, values in theirs.items():
                mine.setdefault(zone, deque(maxlen=TERROR_VOTES)).extend(values)
        self.offsets |= offsets
        self.elites = found | self.elites  # as first seen

    def save(self):
        """Keep this game in the store, in place of what was stored of it before."""
        self.saved_at = self.clock()
        if self.store is None or not self.game_levels:
            return
        mine = {str(area): seed for area, seed in self.game_levels.items()}
        others = [g for g in self.stored_games() if not any(mine.get(a) == seed for a, seed in g['levels'].items())]
        games = [*others, {'levels': mine, 'state': self.state()}][-STORED_GAMES:]
        try:
            self.store.write_text(json.dumps({'games': games}, separators=(',', ':')), encoding='utf-8')
        except OSError as exc:
            LOG.warning('Terror tracker: games not saved to %s: %s', self.store, exc)

    def saw(self, event):
        unit_id, group = event['unit_id'], group_of(event['area'])
        if stat(event, ALIGNMENT_STAT):
            self.allies.add(unit_id)
            return
        if event.get('txt_id') in UNKILLABLE:
            return
        if group and data_byte(event, TYPE_FLAGS) == 0 and not stat(event, HERALD_TIER_STAT):
            modifier = data_byte(event, FIRST_MODIFIER)
            votes = self.votes.setdefault(group.zone, deque(maxlen=TERROR_VOTES))
            votes.append(modifier in TERROR_MODIFIERS)
            if modifier in TERROR_MODIFIERS:
                self.modifiers.setdefault(group.zone, deque(maxlen=TERROR_VOTES)).append(modifier)
        if 'x' in event and event.get('mode') not in DEAD_MODES:  # a corpse seen first is nothing left to kill
            # (0, 0) is a unit whose path is not filled in yet; track() places it once it has a position.
            self.positions[unit_id] = (event['area'], event['x'], event['y'])
            if not (event['x'] or event['y']):
                self.lost[unit_id] = (self.positions.pop(unit_id)[0], None)
            flags = data_byte(event, TYPE_FLAGS) or 0
            if flags & LEADER_FLAGS and not is_minion(event):
                self.leaders.add(unit_id)
                if not stat(event, HERALD_TIER_STAT) and event.get('txt_id') is not None:
                    kind = 'super' if flags & SUPER_FLAG else 'champion' if flags & CHAMPION_FLAG else 'unique'
                    name = super_name(event) if kind == 'super' else None
                    self.elites[unit_id] = (event['area'], kind, event['txt_id'], event['x'], event['y'], name)
            if event.get('txt_id') is not None:
                self.traits[unit_id] = (event['txt_id'], modifiers(event), aura(event))
        tier = stat(event, HERALD_TIER_STAT)
        if tier:
            known = unit_id in self.herald_units  # seen before the game was rejoined
            self.herald_units.add(unit_id)
            if group and not is_minion(event):
                if event.get('mode') not in DEAD_MODES and 'x' in event:
                    self.live_heralds[unit_id] = (tier, event['area'], event['x'], event['y'])
                if not known:
                    self.heralds.append((tier, group.name))
                    self.offsets[group.name] = group_completion(self.levels(group))
                    self.zones.add(group.zone)
        if group:
            self.area_count(event['area']).seen.add(unit_id)

    def track(self, monsters, location=None, complete=True, states=None):
        """Follow live monsters: `monsters` are the units present this pass (terror/monsters.py),
        `location` the player's, `complete` whether the walk reached every unit, `states` the
        states on the player (curses, chill: they raise every pack, danger.py)."""
        self.player_states = states or frozenset()
        # Only units the client holds now: one that left its range keeps its dot, but the game frees
        # its path and reuses the memory for other units, missiles included (RCA 2026-10-05).
        self.paths = {monster.unit_id: monster.path for monster in monsters if monster.path}
        if location is not None:
            self.explore(location)
        for monster in monsters:
            if not (monster.x or monster.y):
                continue  # no position yet
            alive = monster.mode not in DEAD_MODES
            if alive and monster.unit_id in self.lost:
                area, tier = self.lost.pop(monster.unit_id)
                self.positions[monster.unit_id] = (monster.area or area, monster.x, monster.y)
                first = self.elites.get(monster.unit_id)
                if first and not (first[3] or first[4]):  # first seen before its path was filled in
                    self.elites[monster.unit_id] = (first[0], first[1], first[2], monster.x, monster.y, first[5])
                if tier is not None:
                    self.live_heralds[monster.unit_id] = (tier, monster.area or area, monster.x, monster.y)
            revived = monster.unit_id in self.dead and monster.unit_id not in self.positions
            if revived and alive:
                self.positions[monster.unit_id] = (monster.area or self.dead[monster.unit_id], monster.x, monster.y)
            if monster.unit_id in self.positions:
                area = self.positions[monster.unit_id][0]
                self.positions[monster.unit_id] = (monster.area or area, monster.x, monster.y)
            if monster.unit_id in self.live_heralds:
                tier, area, _x, _y = self.live_heralds[monster.unit_id]
                self.live_heralds[monster.unit_id] = (tier, monster.area or area, monster.x, monster.y)
        if location is None or not complete:
            return
        # A remembered monster the client would hold if it were still there: it moved or died unseen.
        present = {monster.unit_id for monster in monsters}
        for unit_id, (area, x, y) in list(self.positions.items()):
            near = math.hypot(x - location.x, y - location.y) <= HELD_RANGE
            if unit_id not in present and area == location.area_id and near:
                del self.positions[unit_id]
                herald = self.live_heralds.pop(unit_id, None)
                self.lost[unit_id] = (area, herald[0] if herald else None)

    def herald_marks(self, area: int) -> list[tuple[int, int, int]]:
        """(tier, x, y) in world units of the Heralds alive in `area`, at their last seen position."""
        return [(tier, x, y) for tier, where, x, y in self.live_heralds.values() if where == area]

    def herald_dots(self, area: int) -> list[MapPoi]:
        return [
            MapPoi(f'Herald T{tier}', 'herald', x / TILE_UNITS, y / TILE_UNITS, self.paths.get(unit_id, 0))
            for unit_id, (tier, where, x, y) in self.live_heralds.items()
            if where == area
        ]

    def packs(self, area: int) -> list[Pack]:
        """The packs of hostile monsters alive in `area`, the most dangerous first (danger.py)."""
        units = []
        for unit_id, (where, x, y) in self.positions.items():
            if where == area and unit_id in self.traits:
                txt_id, found, carried = self.traits[unit_id]
                units.append(Unit(unit_id, txt_id, x, y, found, carried, AURA_MODIFIER in found))
        found = packs(
            units, held=self.bands.get(area), player=self.player_states
        )  # a marked pack keeps its mark near the line
        self.bands[area] = {unit_id: pack.band for pack in found if pack.band for unit_id in pack.members}
        return found

    def level_layout(self, area: int, rooms):
        """The level guide read the level's rooms: their pieces name its fixed elite groups."""
        self.layouts[area] = tuple(rooms)

    def elite_line(self, area: int, rooms=None) -> str | None:
        """'Elites: 3 killed · 2 alive of 7-9 · fixed: 1 killed of 3' for `area`. Its rooms (the
        ones the level guide read, unless given) name the level's fixed groups (elites.py)."""
        rooms = self.layouts.get(area, ()) if rooms is None else rooms
        sightings = [
            elites.Sighting(unit_id, kind, txt_id, x, y, name, unit_id in self.dead and unit_id not in self.positions)
            for unit_id, (where, kind, txt_id, x, y, name) in self.elites.items()
            if where == area
        ]
        return elites.line(elites.tally(area, rooms, sightings))

    def map_dots(self, area: int, *, danger: bool = True) -> list[MapPoi]:
        """A dot per hostile monster alive in `area` at its last seen position, in tiles: plain
        mobs (minions too), then pack leaders (unique, champion, super unique), then Heralds,
        the drawing order. A dot per monster rather than a tinted room (user, 2026-10-03: big
        rooms hid where the pack was). With `danger`, every monster of a pack to be careful with
        is a 'caution' dot and of a deadly one a 'danger' dot; a leader stays a 'leader' dot, or
        an 'elite' one in a deadly pack (user, 2026-10-06), and a deadly pack adds a 'pack' point
        at its centre, named by what makes it deadly."""
        found = [pack for pack in self.packs(area) if pack.band] if danger else []
        bands = {
            unit_id: 'danger' if pack.band == 'deadly' else 'caution' for pack in found for unit_id in pack.members
        }
        dots: dict[str, list[MapPoi]] = {'mob': [], 'caution': [], 'leader': [], 'danger': [], 'elite': []}
        for unit_id, (where, x, y) in self.positions.items():
            if where == area and unit_id not in self.live_heralds:
                kind = bands.get(unit_id) or 'mob'
                if unit_id in self.leaders:  # told apart from its pack whatever the band (user, 2026-10-06)
                    kind = 'elite' if kind == 'danger' else 'leader'
                label = 'unique' if unit_id in self.leaders else 'monster'
                # The HUD follows the marked ones between passes (hud/live.py).
                path = self.paths.get(unit_id, 0) if kind in ('leader', 'danger', 'elite') else 0
                dots[kind].append(MapPoi(label, kind, x / TILE_UNITS, y / TILE_UNITS, path))
        deadly = [pack for pack in found if pack.band == 'deadly']
        centres = [MapPoi(pack.label, 'pack', pack.x / TILE_UNITS, pack.y / TILE_UNITS) for pack in deadly]
        return [
            *dots['mob'],
            *dots['caution'],
            *dots['leader'],
            *dots['danger'],
            *dots['elite'],
            *centres,
            *self.herald_dots(area),
        ]

    def danger_lines(self, area: int, position: tuple[int, int] | None = None, *, shown: int = 2) -> list[str]:
        """A row per deadly pack in `area`, the nearest first: what it is, why, and which way."""
        found = [pack for pack in self.packs(area) if pack.band == 'deadly']
        if position is None:
            return [f'⚠ {pack.label}' for pack in found[:shown]]
        pointers = sorted(
            (Pointer(pack.label, None, pack.x - position[0], pack.y - position[1]) for pack in found),
            key=lambda pointer: pointer.distance,
        )
        return [f'{pointer.arrow}  ⚠ {pointer.label}: {pointer.compass}' for pointer in pointers[:shown]]

    def explore(self, location):
        """Mark the player's room and the rooms touching it, corners too: the client shows the
        monsters of those rooms only, though it loads rooms further out."""
        x, y = location.x / TILE_UNITS, location.y / TILE_UNITS
        loaded = self.visited.get(location.area_id, ())
        for rx, ry, width, height in loaded:
            if rx <= x < rx + width and ry <= y < ry + height:
                near = {
                    room
                    for room in loaded
                    if room[0] <= rx + width
                    and rx <= room[0] + room[2]
                    and room[1] <= ry + height
                    and ry <= room[1] + room[3]
                }
                self.explored.setdefault(location.area_id, set()).update(near)
                return

    def remembered(self, area: int) -> list[tuple[int, float, float, bool]]:
        """(unit id, x, y, leader) of the hostile monsters alive in `area` at their last seen position,
        world units: what the hunt teleports toward when none is in reach (macros/hunt.py)."""
        return [
            (unit_id, float(x), float(y), unit_id in self.leaders)
            for unit_id, (where, x, y) in self.positions.items()
            if where == area and unit_id not in self.allies
        ]

    def visited_rooms(self, area: int) -> set[tuple]:
        """Bounds of the rooms of `area` the player was in or next to: the map dims the others."""
        return self.explored.get(area, set())

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

    def zone_modifier(self, area: int) -> str | None:
        """The game's name of the modifier every plain monster of the area's Terror Zone carries."""
        group = group_of(area)
        recent = self.modifiers.get(group.zone) if group else None
        return MODIFIER_NAMES[max(set(recent), key=recent.count)] if recent else None

    def lines(
        self,
        area: int,
        *,
        terrorized: bool | None,
        position: tuple[int, int] | None = None,
        player_level: int | None = None,
    ) -> list[str]:
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
        # What the game prints where the card sits: 'Terrorized: <level>' and the zone's modifier.
        modifier = self.zone_modifier(area)
        level = min(player_level + TERROR_LEVEL_BONUS, TERROR_LEVEL_CAP) if terrorized and player_level else None
        zone = ' · '.join(part for part in (f'Level {level}' if level else None, modifier) if part)
        lines = [
            f'Terror · {group.name}' + ('' if terrorized else ' (unconfirmed)'),
            *([zone] if zone else []),
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
