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

In every difficulty the client's own list of the levels terrorized now comes first (monsters.py
`terror_levels`, the probe's `terror_levels` event): Normal and Nightmare force no modifier, so there
it is the only sign (plan.md, 2026-10-12).

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
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.game.layout import (
    ALIGNMENT_STAT,
    CHAMPION_FLAG,
    HERALD_TIER_STAT,
    LEADER_FLAGS,
    MINION_FLAG,
    MODIFIERS,
    SUPER_FLAG,
    TYPE_FLAGS,
)
from inventory_tracking.levels.geometry import Pointer
from inventory_tracking.levels.map_card import MapPoi
from inventory_tracking.native.layout import DEAD_MODES, TILE_UNITS, TOWN_IDS
from inventory_tracking.terror import elites
from inventory_tracking.terror.bosses import BOSSES
from inventory_tracking.terror.chance import Level, group_completion, odds
from inventory_tracking.terror.danger import Pack, Unit, packs, table
from inventory_tracking.terror.zones import GROUPS, HeraldGroup, group_of, group_population


MAX_TIER = 5
# Monster data u16: a super unique's superuniques.txt hcIdx (probe logs to 2026-10-06: 36-38 on the
# seal bosses, 61-65 on Baal's waves, 52 on Pindleskin).
SUPER_ID = 0x2A
# Monsters of their own that a route fights, by the name the routes give them (routes/check.py
# ACT_BOSSES): terror/bosses.py's ids, and Blood Raven (monstats.txt `bloodraven`, hcIdx 267, d2data
# 2026-10-12). A boss that is also a super unique is named by its superuniques.txt row, with or
# without the super unique flag on its unit (the Summoner carries the unique flag only).
SLAIN_BOSSES = {**BOSSES, 250: 'The Summoner', 526: 'Nihlathak Boss', 267: 'Blood Raven'}
FIRST_MODIFIER = MODIFIERS.start  # monster data byte: first special modifier (monumod.json id)
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
# The act 5 siege works that are monsters: barricadedoor1/2, prisondoor, barricadewall1/2 (monstats.txt
# of the installed game, 2026-10-11: AI Idle, neverCount 1, no experience). They stand still, strike
# nothing and are no kill of a Terror Zone; Frigid Highlands, 02:40 on 2026-10-11 (user: "too focused on
# killing doors"): 15 of them died to lines aimed at them, a door line read "worth 26787" (a unit
# without a life row is given the area's base points). Kept with the allies: not counted, not remembered.
BARRICADES = frozenset((432, 433, 434, 524, 525))
# The client drops live monsters about 8-24 tiles away; nearer than this (world units) it holds
# them (probe log 2026-10-05: 3 of 1233 live monsters vanished closer).
HELD_RANGE = 40
TERROR_VOTES = 6  # plain-monster sightings per Terror Zone that decide
LEVEL_SEED, LEVEL_SEED_SIZE = 0x1E4, 8  # level struct bytes: the same in a rejoined game
STORED_GAMES = 8  # games kept in the store, the latest last
SAVE_SECONDS = 5.0  # between saves while playing; leaving a game and a Herald always save
# The boss book (the player, 2026-10-22: "we need to kill all bosses, no exceptions to that"; "make sure that all
# state is backed by files on filesystem and survives restarts/reloads. <game-id>-<level> as key"): where each boss of a
# game lives, the unit taken for it, whether it was seen and how it is known, by '<game-id>-<level>' (macros/
# bossledger.py `game_key`: the game's name and the player's unit id), in the store's 'bosses' beside its 'games';
# written atomically on every change, read back at the service's start, entries older than BOOK_SECONDS dropped. Which
# were killed is `slain` (one record of it). macros/bossledger.py `BossLedger` is the macros' view of it
BOOK_SECONDS = 24 * 3600.0
BOOK_MOVE = 15.0  # world units a boss seen moves before its place is written again
# BOOK_KILLS (2026-10-22, game cyberg65, rca/2026-10-22/walled-boss-findings.md): Ancient Kaa the Soulless died at
# 19:56:19 (take 20261022T165515Z-67, unit 1834794757 at life 0) and was in `slain`; the service's restart at 22:06:05
# in the Worldstone Chamber, a level the stored game did not hold yet, began a fresh game state ("game rejoined; Heralds
# seen []") whose save later replaced the old one, and every kill before it was gone: at 23:09 the ledger sent the run
# to Kaa's last place, stood 16 s there and kept the Canyon of the Magi worked for him. True: a boss's kill is written
# in this game's book too ('killed', by '<game-id>-<level>', the key that survived), and `killed` is `slain` with the
# book's kills. False: `slain` alone, as before
BOOK_KILLS = True
# The cause of that loss, and what BOOK_KILLS leaves (2026-10-22, rca/2026-10-22/boss-alive-findings.md, the same game:
# 37 of its 40 bosses killed by 23:15, Duriel at 19:59:56, his life 0, mode 0 then 12, a `died` event in take
# 20261022T165949Z-73). The fresh state of 22:06:05 was a stored part of the game holding the Worldstone Chamber's seed
# alone, saved by the old service in its last second (why its state had reset is not in its logs: its event of entering
# the Chamber was never written; a seed read twice differently resets it, `entered`); the new service rejoined it,
# then entered the Worldstone Keep and the Fortress, levels the stored game of acts 1-4 held with the same seeds, and
# its first save dropped that game as "what was stored of it before" (`save`). And `boss_game` names whatever game the
# macros last began: after a game change, before the agenda begins the new one (a KP_1 run with the loop off never
# does), the old game's book was this one's.
# SEED_JOIN True: a stored game holding a level of this one with its seed is a part of it, merged in (`join`) when that
# level is entered and before every save, never dropped. False: the first match taken, the others dropped, as before
SEED_JOIN = True
# BOOK_FRESH True: the probe writes kills and sightings into the book, and `killed` reads its kills, only while the book
# is named for this state's game: from `boss_game` until the state resets (a game left, another game's seed), when the
# macros name it again. False: whatever game was named last, as before
BOOK_FRESH = True
# BOOK_SIGHT True: a boss of the book seen alive by the probe (its super unique name, or its own monster class:
# SLAIN_BOSSES) is written `seen`, with its unit and place: a route's boss has no spot of its own in the book, so the
# ledger's `sight` never took one (Duriel, the Countess, Radament...), and a boss never seen is what tzloop.py
# BOSS_UNSEEN judges. False: seen by the ledger's binding near a spot only, as before
BOOK_SIGHT = True
# BOOK_RECALL True: when the macros name the game (`boss_game`), the probe's logs of it since it began (the game's
# record's 'began', midgame.py; the PROBE_LOG of each session folder beside the store, written after it began) are read
# into the book (`recall`): each kill and sighting the book does not hold yet, from where the last read stopped, so
# kills lost with a game state, made before the game was named or before BOOK_KILLS, are the game's own reads again.
# The game's record holds the game's start; a game id is one game (bossledger.py `game_key`). False: the book holds
# what was written live only
BOOK_RECALL = True
PROBE_LOG = 'terror-probe.jsonl'  # the probe's events of a session (probe.py `write`), a folder beside the store each
# The game's record (2026-10-22, rca/2026-10-22/restart-zone-findings.md; the player: "no copies, no stale records"):
# one per game, by the same '<game-id>' (macros/bossledger.py `game_key`), in the store's 'records' beside 'bosses': the
# parts its owners write (macros/midgame.py `keep`: the loop's and the agenda's; macros/sightings.py: the valuables
# remembered), each written atomically when it changed, read back at the service's start; RECORD_SECONDS old, none.
# A service restart (planned or not) takes the game up from it (midgame.py `take_up`)
RECORD_SECONDS = 4 * 3600.0
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
    found = bytes.fromhex(data[2 * MODIFIERS.start : 2 * MODIFIERS.stop])
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


def ally(event) -> bool:
    """A monster first seen as an ally (alignment stat: a summon, the mercenary) or a siege work (BARRICADES):
    never counted, never remembered. Shared with the HUD's own walk of the monster table (hud/live.py)."""
    return bool(stat(event, ALIGNMENT_STAT)) or event.get('txt_id') in BARRICADES


def counted(event) -> bool:
    """A hostile the tracker counts and marks: not an ally, nor a unit that never dies (UNKILLABLE)."""
    return not ally(event) and event.get('txt_id') not in UNKILLABLE


def leading(event) -> bool:
    """A pack leader (unique, champion, super unique), not a minion: a 'leader' dot rather than a 'mob' one."""
    return bool((data_byte(event, TYPE_FLAGS) or 0) & LEADER_FLAGS) and not is_minion(event)


def percent(value: float) -> str:
    """One decimal from 1% up, two below it (a single kill's chance is always small)."""
    return f'{value:.1%}' if value >= 0.01 else f'{value:.2%}'


class ZoneTracker:
    def __init__(self, store: Path | None = None, *, clock=time.monotonic, wall=time.time):
        self.store, self.clock, self.wall = store, clock, wall
        self.saved_at = -math.inf
        self.left: dict[int, str] = {}  # the levels of the game just left, until the next level is entered
        # The boss book (BOOK_SECONDS): '<game-id>-<level>' -> boss name -> its record; the game it is written for
        self.book: dict[str, dict[str, dict]] = self.stored_book()
        self.book_game: str | None = None
        # Whether the macros named `book_game` since this state last reset (a game left, another game's seed): the
        # probe's kills go into the book, and `killed` reads it, only then (another game's book is never this one's)
        self.book_fresh = False
        # The probe's logs read into the book (`recall`): game -> log -> bytes read; game -> the read's own tracker
        self.recalled: dict[str, dict[str, int]] = {}
        self.recall_reads: dict[str, ZoneTracker] = {}
        # One writer of the store and the book at a time (the probe's thread, the macros'); re-entered by `write`
        self.lock = threading.RLock()
        self.records: dict[str, dict] = self.stored_records()
        self.reset()

    def reset(self):
        self.game_levels: dict[int, str] = {}  # area -> level seed (hex): what this game is known by
        self.slain: frozenset[str] = frozenset()  # the super uniques and bosses killed this game, by name
        self.book_fresh = False  # the book's game named again by the macros before the probe writes into it
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
        # The tracker's thread writes it while the macro's reads it: readers iterate a copy, `tuple(....items())`
        # (07:55:09 on 2026-10-21: "dictionary changed size during iteration" in `remembered` ended a level run)
        self.positions: dict[int, tuple[int, int, int]] = {}  # hostile unit id -> (area, x, y), alive
        self.leaders: set[int] = set()  # unique, champion and super unique monsters (not minions)
        # hostile unit id -> (txt id, modifiers, aura) as first seen: what makes a pack deadly (danger.py)
        self.traits: dict[int, tuple[int, tuple[int, ...], tuple[int, int] | None]] = {}
        self.ranks: dict[int, tuple[int, int]] = {}  # hostile unit id -> (type flags, Herald tier) as first seen
        self.bands: dict[int, dict[int, str]] = {}  # area -> unit id -> its pack's band on the last pass
        self.player_states: frozenset[int] = frozenset()  # states.txt ids on the player, as last read
        # leader's unit id -> (area, kind, txt id, x, y, name) as first seen: the level's elite groups (elites.py)
        self.elites: dict[int, tuple[int, str, int, int, int, str | None]] = {}
        self.layouts: dict[int, tuple] = {}  # area -> its rooms (levels/model.py Room), from the level guide
        self.lost: dict[int, tuple[int, int | None]] = {}  # unit id -> (area, Herald tier): not where remembered
        self.paths: dict[int, int] = {}  # unit id -> dynamic path address, units in the last walk only
        self.units: dict[int, int] = {}  # unit id -> unit record address, units in the last walk only
        self.dead: dict[int, int] = {}  # hostile unit id -> area, killed at least once this game
        self.modifiers: dict[str, deque[int]] = {}  # Terror Zone -> recent forced modifiers of plain monsters
        self.votes: dict[str, deque[bool]] = {}  # Terror Zone -> recent plain sightings: forced modifier?
        self.terror_levels: frozenset[int] | None = None  # the levels the client holds as terrorized; None: unread
        self.disputed: set[str] = set()  # Terror Zones whose monsters said yes against that list, warned of once
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
        heralds, slain = len(self.heralds), len(self.slain)
        for event in events:
            kind = event['event']
            if kind == 'left_game':
                self.save()
                self.left = dict(self.game_levels) or self.left
                self.reset()
            elif kind == 'seen':
                self.saw(event)
                named = SLAIN_BOSSES.get(event.get('txt_id'))
                if BOOK_KILLS and named is None and counted(event) and (data_byte(event, TYPE_FLAGS) or 0) & SUPER_FLAG:
                    named = super_name(event)  # a super unique's corpse is one killed this game as a boss's is
                if named and event.get('mode') in DEAD_MODES:
                    # A boss first seen already dead was killed this game before this service read it (a restart):
                    # the route's fight stage is over. Andariel's after a restart stood 45 s at her mark and the loop
                    # left the game (12:42:19, 13:58:36 on 2026-10-18)
                    self.slain = self.slain | {named}
                    self.book_kill(event.get('area'), named, event.get('unit_id'))
                elif BOOK_SIGHT and BOOK_KILLS and self.book_named():
                    self.sight_noted(self.book_game, event, self.named(event))
            elif kind == 'terror_levels':
                self.terror_levels = frozenset(event['levels'])
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
                    named = self.named(event)
                    if named:
                        self.slain = self.slain | {named}
                    self.book_kill(event.get('area'), named, unit_id)  # unnamed: a unit the ledger took for a boss

        # A boss kill saves at once: a restart before the next periodic save forgot Andariel's death (2026-10-18)
        if events and (
            len(self.heralds) != heralds or len(self.slain) != slain or self.clock() - self.saved_at >= SAVE_SECONDS
        ):
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
        new = area not in self.game_levels
        self.game_levels[area] = seed
        left, self.left = self.left, {}
        if self.restored:
            if new and SEED_JOIN:
                self.join()  # the 22:06 part of cyberg65, then the Keep's and the Fortress's seeds of the game
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
        if SEED_JOIN:
            self.join(games)

    def join(self, games: list[dict] | None = None) -> None:
        """SEED_JOIN: each stored game holding a level of this one with its seed, and a level this one does not hold,
        is a part of this game: its levels and its state merged in (`restore`), said."""
        mine = {str(area): seed for area, seed in self.game_levels.items()}
        for game in games if games is not None else self.stored_games():
            theirs = game['levels']
            if not mine.items() & theirs.items() or theirs.keys() <= mine.keys():
                continue
            try:
                self.restore(game['state'], merge=True)
            except (KeyError, TypeError, ValueError) as exc:
                LOG.warning('Terror tracker: a stored part of this game unreadable: %s', exc)
                continue
            added = sorted(int(area) for area in theirs.keys() - mine.keys())
            self.game_levels = {int(area): seed for area, seed in theirs.items()} | self.game_levels
            mine = {str(area): seed for area, seed in self.game_levels.items()}
            LOG.info('Terror tracker: a stored part of this game joined: levels %s; Heralds seen %s', added,
                     self.heralds)  # fmt: skip

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
            'slain': sorted(self.slain),
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
        # Absent in games stored before 2026-10-18: a named elite that is among the dead was slain. Andariel's kill,
        # lost in a restart, left the route standing at her mark (13:56, 14:00).
        try:
            slain = {str(name) for name in state['slain']}
        except KeyError, TypeError:
            slain = set()
        slain |= {
            named
            for unit_id, (_, _, txt_id, _, _, name) in found.items()
            if unit_id in dead and (named := name or SLAIN_BOSSES.get(txt_id))
        }
        if not merge:
            self.slain = frozenset()
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
        for zone, values in votes.items():
            self.votes.setdefault(zone, deque(maxlen=TERROR_VOTES)).extend(values)
        for zone, values in modifiers.items():
            self.modifiers.setdefault(zone, deque(maxlen=TERROR_VOTES)).extend(values)
        self.offsets |= offsets
        self.elites = found | self.elites  # as first seen
        self.slain = self.slain | slain

    def save(self):
        """Keep this game in the store, in place of what was stored of it before."""
        self.saved_at = self.clock()
        if self.store is None or not self.game_levels:
            return
        stored = self.stored_games()
        if SEED_JOIN:
            self.join(stored)  # a part of this game is merged in, never dropped as "what was stored of it before"
        mine = {str(area): seed for area, seed in self.game_levels.items()}
        others = [g for g in stored if not any(mine.get(a) == seed for a, seed in g['levels'].items())]
        self.write({'games': [*others, {'levels': mine, 'state': self.state()}][-STORED_GAMES:], 'bosses': self.book})

    def write(self, data: dict) -> None:
        """The store written atomically (a file beside it, then renamed over it): `data`'s keys in place of the file's,
        the others kept."""
        if self.store is None:
            return
        with self.lock:
            try:
                held = json.loads(self.store.read_text(encoding='utf-8'))
                held = held if isinstance(held, dict) else {}
            except OSError, ValueError:
                held = {}
            held |= data
            part = self.store.with_name(f'{self.store.name}.part')
            try:
                part.write_text(json.dumps(held, separators=(',', ':')), encoding='utf-8')
                os.replace(part, self.store)
            except OSError as exc:
                LOG.warning('Terror tracker: games not saved to %s: %s', self.store, exc)

    def stored_records(self) -> dict[str, dict]:
        """The games' records as stored (RECORD_SECONDS), the latest STORED_GAMES."""
        if self.store is None:
            return {}
        try:
            held = json.loads(self.store.read_text(encoding='utf-8')).get('records', {})
        except OSError, ValueError, AttributeError:
            return {}
        if not isinstance(held, dict):
            return {}
        now = self.wall()
        return {
            str(key): entry
            for key, entry in held.items()
            if isinstance(entry, dict)
            and isinstance(entry.get('at'), (int, float))
            and now - float(entry['at']) <= RECORD_SECONDS
        }

    def record(self, key: str | None) -> dict:
        """Game `key`'s record (RECORD_SECONDS): its parts and 'at', the wall clock it was last written; {} for none."""
        entry = self.records.get(key) if key is not None else None
        if not isinstance(entry, dict) or self.wall() - float(entry.get('at', 0.0)) > RECORD_SECONDS:
            return {}
        return dict(entry)

    def record_note(self, key: str, part: str, value: dict) -> bool:
        """`value` as game `key`'s `part`, written at once when it changed; whether it did."""
        value = json.loads(json.dumps(value))  # as the store holds it: lists, string keys
        entry = self.records.get(key)
        if isinstance(entry, dict) and entry.get(part) == value:
            return False
        entry = {**(entry if isinstance(entry, dict) else {}), part: value, 'at': self.wall()}
        others = sorted((each for each in self.records.items() if each[0] != key), key=lambda each: each[1]['at'])
        self.records = dict([*others[-(STORED_GAMES - 1) :], (key, entry)])
        self.write({'records': self.records})
        return True

    def stored_book(self) -> dict[str, dict[str, dict]]:
        """The boss book as stored, entries older than BOOK_SECONDS dropped."""
        if self.store is None:
            return {}
        try:
            book = json.loads(self.store.read_text(encoding='utf-8')).get('bosses', {})
        except OSError, ValueError, AttributeError:
            return {}
        now = self.wall()
        kept: dict[str, dict[str, dict]] = {}
        for key, records in book.items() if isinstance(book, dict) else ():
            if not isinstance(records, dict):
                continue
            fresh = {
                str(name): record
                for name, record in records.items()
                if isinstance(record, dict) and now - float(record.get('at', 0.0)) <= BOOK_SECONDS
            }
            if fresh:
                kept[str(key)] = fresh
        return kept

    def boss_game(self, game: str | None) -> None:
        """The game the boss book is written for (macros/bossledger.py `game_key`), None: none. Named anew (another
        game, or this state reset since: BOOK_FRESH), the probe's logs of it are read into it (BOOK_RECALL)."""
        with self.lock:
            named = game is not None and (game != self.book_game or not self.book_fresh)
            self.book_game, self.book_fresh = game, game is not None
        if named and BOOK_RECALL and game is not None:
            self.recall(game)

    def book_named(self) -> bool:
        """Whether the probe writes into the book and `killed` reads it (BOOK_FRESH): a game named for this state."""
        return self.book_game is not None and (self.book_fresh or not BOOK_FRESH)

    def boss_note(
        self,
        area: int,
        name: str,
        *,
        place: tuple[float, float] | None = None,
        unit: int | None = None,
        seen: bool = False,
        by: str = '',
        tried: bool = False,
        killed: bool = False,
        gone: str | None = None,
    ) -> bool:
        """Boss `name` of level `area` in this game's book (`boss_game`): its place, the unit taken for it, seen, how
        known, the recoveries kept for it (`tried`: one more, macros/running/recovery.py BOSS_RECOVERY), its kill
        (`killed`, BOOK_KILLS), why it is not to be found (`gone`: macros/bossledger.py `BossLedger.absent`; '' clears
        it); written at once when that changed (a place only once it moved BOOK_MOVE). Whether it changed."""
        return self.note(
            self.book_game, area, name, place=place, unit=unit, seen=seen, by=by, tried=tried, killed=killed, gone=gone
        )

    def note(
        self,
        game: str | None,
        area: int,
        name: str,
        *,
        place: tuple[float, float] | None = None,
        unit: int | None = None,
        seen: bool = False,
        by: str = '',
        tried: bool = False,
        killed: bool = False,
        gone: str | None = None,
    ) -> bool:
        """`boss_note` in game `game`'s book (None: none): the probe's own writes (`kill_noted`, `sight_noted`) name the
        game they read."""
        if game is None:
            return False
        with self.lock:  # the probe's thread and the macros' both write it
            records = self.book.setdefault(f'{game}-{area}', {})
            stored = records.get(name)
            fresh = stored is None
            record: dict[str, object] = (
                dict(stored) if stored is not None else {'place': None, 'unit': None, 'seen': False, 'by': by}
            )
            changed = fresh
            if place is not None:
                old = record.get('place')
                if not isinstance(old, list) or len(old) != 2 or math.dist(old, place) >= BOOK_MOVE:
                    record['place'], changed = [round(place[0], 1), round(place[1], 1)], True
            if unit is not None and record.get('unit') != unit:
                record['unit'], changed = unit, True
            if seen and not record.get('seen'):
                record['seen'], changed = True, True
            if tried:
                count = record.get('tries')
                record['tries'], changed = (count if isinstance(count, int) else 0) + 1, True
            if killed and not record.get('killed'):
                record['killed'], changed = True, True
            if gone is not None and str(record.get('gone') or '') != gone:
                record['gone'], changed = gone, True
            if not changed:
                return False
            record['at'] = self.wall()
            records[name] = record
            self.write({'bosses': self.book})
            return True

    def boss_book(self) -> list[tuple[int, str, dict]]:
        """(level, name, record) of this game's book (`boss_game`)."""
        return self.game_book(self.book_game)

    def game_book(self, game: str | None) -> list[tuple[int, str, dict]]:
        """(level, name, record) of game `game`'s book (None: none)."""
        if game is None:
            return []
        prefix = f'{game}-'
        with self.lock:  # a copy: the probe's thread writes it while the macros' reads it
            return [
                (int(key[len(prefix) :]), name, record)
                for key, records in self.book.items()
                if key.startswith(prefix) and key[len(prefix) :].isdigit()
                for name, record in records.items()
            ]

    def named(self, event) -> str | None:
        """The boss or super unique an event's unit is (its superuniques.txt name as first seen, else its own monster
        class: SLAIN_BOSSES), None for any other."""
        return (self.elites.get(event.get('unit_id')) or (None,) * 6)[5] or SLAIN_BOSSES.get(event.get('txt_id'))

    def kill_noted(self, game: str | None, area: int, name: str | None, unit: object = None) -> bool:
        """BOOK_KILLS: the kill of boss `name` (None: the one of game `game`'s book whose unit `unit` is, the ledger's
        binding) on level `area`, written in its record (on its own level when the book names it on another; made on
        `area` when it has none). Whether that changed the book."""
        unit = unit if isinstance(unit, int) and not isinstance(unit, bool) else None
        with self.lock:
            records = self.game_book(game)
            if name is None:
                bound = (boss for _, boss, record in records if unit is not None and record.get('unit') == unit)
                name = next(bound, None)
                if name is None:
                    return False
            levels = [level for level, boss, _ in records if boss == name]
            level = area if area in levels or not levels else levels[0]
            return self.note(game, level, name, killed=True)

    def sight_noted(self, game: str | None, event, name: str | None) -> bool:
        """BOOK_SIGHT: boss `name` (of the event's level in game `game`'s book) seen alive by the probe's `event`:
        `seen`, its unit and place, a gone one owed again (bossledger.py BOSS_ABSENT). Whether that changed the
        book."""
        area = event.get('area')
        if name is None or not isinstance(area, int) or event.get('mode') in DEAD_MODES:
            return False
        with self.lock:
            mine = (record for level, boss, record in self.game_book(game) if (level, boss) == (area, name))
            record = next(mine, None)
            if record is None or record.get('killed'):
                return False
            x, y = event.get('x') or 0, event.get('y') or 0
            unit = event.get('unit_id')
            return self.note(
                game, area, name, place=(float(x), float(y)) if x or y else None,
                unit=unit if isinstance(unit, int) else None, seen=True, gone='' if record.get('gone') else None,
            )  # fmt: skip

    def recall(self, game: str) -> None:
        """BOOK_RECALL: the probe's logs of game `game` since it began (its record's 'began') read into its book from
        where the last read stopped: each kill (`kill_noted`) and sighting (`sight_noted`) the book lacks; said when it
        changed the book. The logs are the PROBE_LOG of each session folder beside the store written since."""
        began = (self.record(game).get('loop') or {}).get('began') if self.store is not None else None
        if self.store is None or not isinstance(began, (int, float)) or isinstance(began, bool):
            return
        since = datetime.fromtimestamp(float(began), UTC).isoformat()[:19]
        marks = self.recalled.setdefault(game, {})
        reads = self.recall_reads.setdefault(game, ZoneTracker())  # its own state: the names its units are
        kills = sights = 0
        for log in sorted(self.store.parent.glob(f'*/{PROBE_LOG}')):
            try:
                if log.stat().st_mtime < float(began):
                    continue
                with log.open('rb') as file:
                    file.seek(marks.get(str(log), 0))
                    data = file.read()
            except OSError:
                continue
            whole = data.rfind(b'\n') + 1  # a line being written is read the next time
            marks[str(log)] = marks.get(str(log), 0) + whole
            for line in data[:whole].splitlines():
                head = line[:90]  # '{"at":"<stamp>","event":"died",...': read only kills and sightings whole
                if b'"died"' not in head and b'"seen"' not in head:
                    continue
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(event, dict) or str(event.get('at', ''))[:19] < since:
                    continue
                before = reads.slain
                reads.apply([event])
                area = event.get('area')
                if not isinstance(area, int):
                    continue
                if event['event'] == 'died' or event.get('mode') in DEAD_MODES:
                    names = sorted(reads.slain - before) or ([None] if event['event'] == 'died' else [])
                    kills += sum(self.kill_noted(game, area, name, event.get('unit_id')) for name in names)
                else:
                    sights += self.sight_noted(game, event, reads.named(event))
        if kills or sights:
            LOG.info("Terror tracker: the probe's logs of game %s since %s UTC read into its book: %d kills, "
                     '%d sightings', game, since, kills, sights)  # fmt: skip

    def saw(self, event):
        unit_id, group = event['unit_id'], group_of(event['area'])
        if ally(event):
            self.allies.add(unit_id)
            return
        if not counted(event):
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
            if leading(event):
                self.leaders.add(unit_id)
                if not stat(event, HERALD_TIER_STAT) and event.get('txt_id') is not None:
                    kind = 'super' if flags & SUPER_FLAG else 'champion' if flags & CHAMPION_FLAG else 'unique'
                    name = super_name(event) if kind == 'super' else None
                    self.elites[unit_id] = (event['area'], kind, event['txt_id'], event['x'], event['y'], name)
            if event.get('txt_id') is not None:
                self.traits[unit_id] = (event['txt_id'], modifiers(event), aura(event))
                self.ranks[unit_id] = (flags, stat(event, HERALD_TIER_STAT))
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
        self.paths = {monster.unit_id: monster.path_at for monster in monsters if monster.path_at}
        self.units = {monster.unit_id: monster.unit_at for monster in monsters if monster.unit_at}
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
            MapPoi(
                f'Herald T{tier}',
                'herald',
                x / TILE_UNITS,
                y / TILE_UNITS,
                self.paths.get(unit_id, 0),
                self.units.get(unit_id, 0),
                unit_id,
            )
            for unit_id, (tier, where, x, y) in self.live_heralds.items()
            if where == area
        ]

    def packs(self, area: int) -> list[Pack]:
        """The packs of hostile monsters alive in `area`, the most dangerous first (danger.py)."""
        units = []
        for unit_id, (where, x, y) in tuple(self.positions.items()):
            if where == area and unit_id in self.traits:
                txt_id, found, carried = self.traits[unit_id]
                flags, tier = self.ranks.get(unit_id, (0, 0))
                units.append(Unit(unit_id, txt_id, x, y, found, carried, AURA_MODIFIER in found, flags, tier))
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
        with self.lock:  # a copy: the probe's thread writes it while the macros' reads it
            seen = tuple(self.elites.items())
        sightings = [
            elites.Sighting(unit_id, kind, txt_id, x, y, name, unit_id in self.dead and unit_id not in self.positions)
            for unit_id, (where, kind, txt_id, x, y, name) in seen
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
        for unit_id, (where, x, y) in tuple(self.positions.items()):
            if where == area and unit_id not in self.live_heralds:
                kind = bands.get(unit_id) or 'mob'
                if unit_id in self.leaders:  # told apart from its pack whatever the band (user, 2026-10-06)
                    kind = 'elite' if kind == 'danger' else 'leader'
                label = 'unique' if unit_id in self.leaders else 'monster'
                # The HUD follows every one between cards, its position and whether it lives (hud/live.py):
                # rca/2026-10-14/run-1916-hud-findings.md §2, fix 1.
                path, unit = self.paths.get(unit_id, 0), self.units.get(unit_id, 0)
                dots[kind].append(MapPoi(label, kind, x / TILE_UNITS, y / TILE_UNITS, path, unit, unit_id))
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

    def supers(self, area: int) -> list[tuple[float, float]]:
        """Where each super unique seen in `area` this game was last seen, dead or alive, world units.
        And each boss (terror/bosses.py): the Summoner carries the unique flag only (his record on
        2026-10-11, 15:51: type flags 0x08), and the macro request beside his corpse found "0 super
        uniques seen on level 74"."""
        with self.lock:  # a copy: the probe's thread writes it while the macros' reads it (20:46:46 on 2026-10-24)
            seen = tuple(self.elites.values())
        return [
            (float(x), float(y))
            for where, kind, txt_id, x, y, _ in seen
            if where == area and (kind == 'super' or txt_id in BOSSES)
        ]

    def book_kill(self, area: object, name: str | None, unit: object = None) -> None:
        """BOOK_KILLS: boss `name`'s kill on level `area` (None: the boss of the book whose unit `unit` is) written in
        this game's book (no game named for this state, BOOK_FRESH: nothing; `recall` reads it from the log later)."""
        if BOOK_KILLS and isinstance(area, int) and self.book_named():
            self.kill_noted(self.book_game, area, name, unit)

    def killed(self) -> frozenset[str]:
        """The super uniques (by their superuniques.txt name) and bosses killed this game: what a
        route's `fight` stage waits for (routes/progress.py). Read from the macro's thread. BOOK_KILLS: with the
        kills of this game's book, which a lost game state does not take with it (BOOK_FRESH: the book of the game
        named for this state only)."""
        if not BOOK_KILLS or not self.book_named():
            return self.slain
        return self.slain | {name for _, name, record in self.boss_book() if record.get('killed')}

    def remembered(self, area: int) -> list[tuple[int, float, float, bool]]:
        """(unit id, x, y, leader) of the hostile monsters alive in `area` at their last seen position,
        world units: what the hunt teleports toward when none is in reach (macros/hunt.py)."""
        return [
            (unit_id, float(x), float(y), unit_id in self.leaders)
            for unit_id, (where, x, y) in tuple(self.positions.items())
            if where == area and unit_id not in self.allies
        ]

    def hostiles(self, area: int) -> list[tuple[int, int, int, float, float]]:
        """(unit id, txt id, type flags, x, y) of the hostile monsters alive in `area` at their last seen position,
        world units, those first seen with their data: what the level card's goal finds a boss among
        (macros/card_goal.py)."""
        return [
            (unit_id, self.traits[unit_id][0], self.ranks.get(unit_id, (0, 0))[0], float(x), float(y))
            for unit_id, (where, x, y) in tuple(self.positions.items())
            if where == area and unit_id not in self.allies and unit_id in self.traits
        ]

    def visited_rooms(self, area: int) -> set[tuple]:
        """Bounds of the rooms of `area` the player was in or next to: the map dims the others."""
        return self.explored.get(area, set())

    def terrorized(self, area: int) -> bool | None:
        """Whether the area is terrorized now: by the client's own list of terrorized levels when
        it was read and names any (every difficulty), else by its plain monsters' forced modifier
        (most of the last few, Hell only), else True once a Herald appeared there this game; None
        before any evidence. Plain monsters with the modifier outvote a list without the area."""
        group = group_of(area)
        if group is None:
            return None
        votes = self.votes.get(group.zone)
        voted = sum(votes) * 2 > len(votes) if votes else None
        if self.terror_levels:
            listed = area in self.terror_levels
            if voted and not listed and group.zone not in self.disputed:
                self.disputed.add(group.zone)
                LOG.warning(
                    'Terror tracker: the monsters of level %d carry a Terror Zone modifier and the client lists %s',
                    area, sorted(self.terror_levels),
                )  # fmt: skip
            return listed or bool(voted)
        if voted is not None:
            return voted
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
        votes = self.votes.get(group.zone)
        if terrorized and self.terror_levels and area in self.terror_levels and votes and not any(votes):
            # The client lists the level and its plain monsters carry no forced modifier: a Terror Zone
            # below Hell, which has no Heralds (desecratedzones.json: max_herald_tiers 0 there).
            return [f'Terror · {group.name}', 'No Heralds below Hell']
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
