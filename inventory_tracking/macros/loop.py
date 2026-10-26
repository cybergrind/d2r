"""The KP_6 loop: plays games of one `Kind` (Lower Kurast chests, Andariel, the terror zone kinds) until toggled off
(routes/lower-kurast-loop-plan.md, routes/andariel-loop-plan.md).

A state machine read from where the character is (`next_leg`): one leg per runner run (runner.py LOOP). An `Abort`
or an overdue game is recovered from by leaving the game (`recover`); only death stops it (the player, 2026-10-18:
"fully prevent us from stopping"). History: macros/history/loop.md.
"""

import json
import math
import time
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from itertools import pairwise
from pathlib import Path
from typing import Any, NamedTuple

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Carried, Pack, World
from inventory_tracking.game.stash import Stash
from inventory_tracking.items.grid import Grid
from inventory_tracking.levels.presets import display_name
from inventory_tracking.loot.api import settle as settle_field
from inventory_tracking.loot.storage import Storage, cells_low, room
from inventory_tracking.macros import midgame
from inventory_tracking.macros.actuator import Abort, Cancelled, Hand
from inventory_tracking.macros.agenda import HERALD, RESUME, SWAP_GOALS, Agenda
from inventory_tracking.macros.charms import (
    GHEEDS_FORTUNE,
    Parked,
    Stats,
    candidates,
    choose,
    gheeds,
    magic_find,
    newcomers,
    park,
)
from inventory_tracking.macros.cube import (
    KEPT,
    SURE_BLOCK,
    loot,
    own_of,
    perfect_of,
)
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.experience import Ledger, Reading, reading
from inventory_tracking.macros.junk import MAGIC
from inventory_tracking.macros.merc import Trips
from inventory_tracking.macros.pickup import SHUNNED
from inventory_tracking.macros.portal import FROM_TOME, PortalSource, portal_source, slot_note, through_portal, to_town
from inventory_tracking.macros.repair import RETRY_GAMES, due, gold, wants, worn_out, worn_text
from inventory_tracking.macros.routines import DEAD, Dead, character_keys, create_next_game, leave_game, prebuff
from inventory_tracking.macros.shop import KEYS_ONE_STACK, KEYS_WANTED, gold_cap, short
from inventory_tracking.macros.stash import RESOURCES
from inventory_tracking.macros.threat import watched_sleep
from inventory_tracking.macros.town import GEMS_A_KIND, TRADE_ROOM, Exit, sold_full, surplus, tops_up
from inventory_tracking.macros.tzroutine import TZ_PLUS
from inventory_tracking.macros.visit import Remembered
from inventory_tracking.macros.volatile import (
    STORE_FILE,
    Cell,
    Volatile,
    empty,
    own_of as players_of,
    picture,
    print_of,
)
from inventory_tracking.macros.waypoint import travel
from inventory_tracking.native.layout import TOWN_IDS
from inventory_tracking.routes.catalog.act2 import TOMBS
from inventory_tracking.routes.model import FIGHT, LOOT, STAND, USE
from inventory_tracking.routes.progress import Progress
from inventory_tracking.terror.bosses import KILLED_AT


__all__ = [
    'ANDARIEL',
    'BAAL',
    'COMING',
    'KINDS',
    'LK',
    'LOWER_KURAST',
    'MERC_TRIPS',
    'TOWN',
    'TRADE_ROOM',
    'TRIPS_A_GAME',
    'TRIPS_A_ZONE_GAME',
    'Coming',
    'Dead',
    'GameId',
    'Kind',
    'LegHands',
    'Loop',
    'coming_kinds',
    'kind_of',
    'new_cells',
    'next_leg',
]

KURAST_DOCKS, LOWER_KURAST, PANDEMONIUM_FORTRESS = 75, 79, 103
ROGUE_ENCAMPMENT, CATACOMBS_2, CATACOMBS_3, CATACOMBS_4 = 1, 35, 36, 37  # levels.txt
# levels.txt (third-parties/d2data/json/levels.json, read 2026-10-25): Harrogath, The Worldstone Keep Level 2 (its
# waypoint, act 5 row 8 of macros/data/waypoints.json) and 3, the Throne of Destruction, The Worldstone Chamber
HARROGATH, WORLDSTONE_KEEP_2, WORLDSTONE_KEEP_3, THRONE, CHAMBER = 109, 129, 130, 131, 132


@dataclass(frozen=True)
class Kind:
    """A kind of the loop's run: `start` its waypoint's level, `levels` the run's, `home` its act's town, `keys` what
    Jamella tops keys up to (macros/shop.py)."""

    key: str
    name: str
    start: int
    levels: frozenset[int]
    home: int
    keys: int = KEYS_ONE_STACK
    # The measure the kind is tuned by (the player, 2026-10-19: "every loop has it's own metric, that it must optimize")
    metric: str = ''
    # Seconds before the watchdog leaves its game (`overdue`); None: GAME_SECONDS
    game_seconds: float | None = None
    # Where the kinds differ: the code asks these, never the kind itself
    agenda: bool = False  # its legs are the agenda's goals (macros/tzloop.py), not `next_leg`'s
    trips: bool = False  # no room for a valuable: a trip to town and back by its own legs (macros/stops.py)
    # No room: the room package (agenda.py `room_package`) between its legs, as the agenda kinds' (tzloop.py `packaged`)
    packaged: bool = False
    swaps_gheeds: bool = False  # the Gheed's swap (macros/charms.py)
    boss: str | None = None  # whose drops may still be landing at PICK_UP (`KILLED_AT`)
    # The HUD's mode word (runner.py `run_badge`; the player, 2026-10-19: "ATT, BUFF, LK, AND (andariel), BAAL, DIAB,
    # MEPH": BAAL built 2026-10-25, DIAB and MEPH for kinds to come)
    word: str = ''
    fortress_ends_game: bool = False  # leaving its level for the Fortress ends the game (`done`)
    full_clear: bool = False  # every hostile, every room: the Herald hunt (macros/tzloop.py `full_clear`)
    # The boss's own level: the loot leg waits for his drops there only (`DROPS_LAND`), not on a level before it (the
    # Throne's loot after Lister for Baal); None: on any level of the kind
    lair: int | None = None
    # Its shard's act played alone (macros/acts/engine.py `ActScript.alone`): the script's alone steps, then the game's
    # end; no rest of the act, no rotation, no other act's shard (tzroutine.py `itinerary`, actloop.py `alone`). The
    # Act 2 TZ leveling kind's (`ACT2_TZ`, 2026-10-25)
    alone: bool = False


LK = Kind(
    'lk', 'Lower Kurast', LOWER_KURAST, frozenset((LOWER_KURAST,)), KURAST_DOCKS, KEYS_WANTED, 'chests opened an hour',
    word='LK', fortress_ends_game=True, packaged=True,
)  # fmt: skip
# `packaged` (2026-10-19): Lower Kurast dropped an item to identify, then stopped; now the cube, then a trip (the
# player: "move to cube, if no space after that - go to town and do town routine")
# Andariel (routes/andariel-loop-plan.md): Catacombs 2 by waypoint, down to Level 4, her fight, loot, Save and Exit
ANDARIEL = Kind(
    'andariel',
    'Andariel',
    CATACOMBS_2,
    frozenset((CATACOMBS_2, CATACOMBS_3, CATACOMBS_4)),
    ROGUE_ENCAMPMENT,
    metric='Andariel kills an hour',
    trips=True,
    swaps_gheeds=True,
    boss='Andariel',
    word='AND',
)
# Baal (the player, 2026-10-25 ~12:17: "build a baal runner, very similar to andariel runner"; 2026-10-22: "we need to
# kill all bosses, no exceptions to that -> they can give a very valuable drops, especially baal's statue"): the
# Worldstone Keep 2 by waypoint, down to the Throne, its five waves (macros/hunting/throne.py), the portal once Baal
# left his throne, his fight in the Worldstone Chamber, the loot, Save and Exit. Town trips and the Gheed's swap as
# Andariel's, from Harrogath. The route is the catalogue's 'Baal' (routes/catalog/act5.py), the shard act 5 script's
# first trip (macros/acts/act5.py)
# BAAL_GAME_SECONDS (estimate, 2026-10-25): the act 5 shard game at 23:10-23:16 on 2026-10-24 took 105 s for the
# waves, ~15 s for Baal's walk into the portal and 24 s from the Chamber to his kill; the Keep's two levels rushed and
# the waypoint ~60 s: ~4 min a game, twice that before the watchdog leaves it
BAAL_GAME_SECONDS = 480.0
BAAL = Kind(
    'baal',
    'Baal',
    WORLDSTONE_KEEP_2,
    frozenset((WORLDSTONE_KEEP_2, WORLDSTONE_KEEP_3, THRONE, CHAMBER)),
    HARROGATH,
    metric='Baal kills an hour',
    game_seconds=BAAL_GAME_SECONDS,
    trips=True,
    swaps_gheeds=True,
    boss='Baal',
    word='BAAL',
    lair=CHAMBER,
)
KINDS = {kind.key: kind for kind in (LK, ANDARIEL, BAAL)}
# The terror zone kinds (macros/goals-plan.md): goals from the agenda (tzloop.py), offered only with tzloop.ENABLED
FIELD = frozenset(range(137)) - {ROGUE_ENCAMPMENT, 40, KURAST_DOCKS, PANDEMONIUM_FORTRESS, 109}
TZ_GAME_SECONDS = 1200.0
# The HUD's word is TZ+ while TZ+ is TZ leveling's behaviour (macros/tzroutine.py TZ_PLUS; the player, 2026-10-20
# ~18:50: "TZ+ is default TZ mode from now")
# The metric (the player, 2026-10-21 ~21:18: "the main metric xp/hour! elites/hour!"): games.py and elites.py say both
TZ = Kind(
    'tz', 'TZ leveling', 0, FIELD, PANDEMONIUM_FORTRESS, metric='experience and elite kills an hour',
    game_seconds=TZ_GAME_SECONDS,
    agenda=True, packaged=True, swaps_gheeds=True, word='TZ+' if TZ_PLUS else 'TZ',
)  # fmt: skip
# `swaps_gheeds` (2026-10-19): a Herald's Gheed's in Spider Forest fell to the room rules, then stopped the loop
# The Herald hunt's measure is not ruled yet (goals-plan.md open question 8)
TZ_CLEAR = replace(
    TZ, key='tzclear', name='Full clear TZ', metric='Herald and elite kills an hour', full_clear=True, word='TZC'
)
# The shard act loops (macros/actloop.py; routes/act-terrorize-plan.md): an act terrorized by its Worldstone Shard in
# the Fortress, played in its script's order (macros/acts/act<N>.py: the boss first), TZ+ on every level. The player,
# 2026-10-20 ~19:25: "yes, let's do act 4 mode ... shard act 4 as an entry"; ~22:50: "could you implement shards run
# for every act". The coordinator's answers, accepted: a game cap of 2700 s for now (measured), elite and Herald kills
# an hour, statues reported apart. Each offered only with actloop.ENABLED and its script ready
ACT_GAME_SECONDS = 2700.0
# Per act where the whole act takes longer: act 1's 37 levels are ~3200-3400 s by the stays of the takes (the act 1
# agent's estimate, 2026-10-20); at 2700 the cap would cut every game at the Crypt (the player, 2026-10-20 ~21:30:
# "make sure, that we're farming until it's done")
ACT_SECONDS = {1: 3900.0, 3: 3600.0, 5: 3600.0}  # acts 3 and 5: 15 and 11 trips


def act_kind(act: int) -> Kind:
    """The shard act kind of act `act` (1-5): key `act<N>`, "Shard: Act N", HUD word `ACT<N>`."""
    return replace(
        TZ, key=f'act{act}', name=f'Shard: Act {act}', metric='elite and Herald kills an hour',
        game_seconds=ACT_SECONDS.get(act, ACT_GAME_SECONDS), word=f'ACT{act}',
    )  # fmt: skip


ACT_KINDS = {kind.key: kind for kind in map(act_kind, range(1, 6))}
ACT4 = ACT_KINDS['act4']
# Act 2 TZ leveling (2026-10-25). The player, ~17:15: "act 2 tz leveling: use worlstone shard for act 2 / go all canyon
# of the magi + all tals rasha tombs (small + kaa + duriel) / go full arcane sanctuary (+kill summoner)"; ~17:47:
# "current run is TZ leveling, and I want to have separate Act 2 TZ Leveling with tal rasha's and arcane sanctuary". A
# kind of its own beside "Shard: Act 2" (its whole act, as before) and TZ leveling (as before): the Eastern shard
# (actloop.py ACTS), then act 2's alone steps (macros/acts/act2.py TZ_LEVELING_STEPS: the Canyon of the Magi and its
# seven tombs, Duriel's Lair from the true tomb, the Arcane Sanctuary toured whole and the Summoner), then Save and
# Exit. Its cap is the act 2 game's. Offered last (`loop_kinds`: "you must not touch any existing entries", the player,
# 2026-10-25) while act 2's script has alone steps
ACT2_TZ = replace(
    act_kind(2), key='act2tz', name='Act 2 TZ leveling', metric='experience and elite kills an hour', word='A2TZ',
    alone=True,
)  # fmt: skip
ALONE_KINDS = {ACT2_TZ.key: ACT2_TZ}
# The experience lines too (`look_at_experience`)
TZ_KINDS = frozenset((TZ.key, TZ_CLEAR.key, *ACT_KINDS, *ALONE_KINDS))


def loop_kinds() -> dict[str, Kind]:
    """The kinds the player may choose (KP_6 three times, restart.py --kind); TZ kinds only with tzloop.ENABLED, a
    shard act kind only with actloop.ENABLED as well and its act's script ready (macros/acts/); an alone kind (Act 2
    TZ leveling) last, while its act's script has alone steps: the existing entries' order unchanged (the player,
    2026-10-25: "you must not touch any existing entries")."""
    from inventory_tracking.macros import actloop, acts, tzloop  # late: tzloop imports this module

    tz = {TZ.key: TZ, TZ_CLEAR.key: TZ_CLEAR} if tzloop.ENABLED else {}
    on = tzloop.ENABLED and actloop.ENABLED
    act = {key: kind for key, kind in ACT_KINDS.items() if on and acts.ready(actloop.act_of(kind))}
    lone = {key: kind for key, kind in ALONE_KINDS.items() if on and acts.alone(actloop.act_of(kind))}
    return {**KINDS, **tz, **act, **lone}


@dataclass(frozen=True)
class Coming:
    """A kind announced but not built yet: the KP_6 picker shows it, not choosable, until `loop_kinds` offers a kind
    whose key is `key` or starts with it (macros/kindpick.py)."""

    key: str
    name: str
    word: str
    metric: str


# The player, 2026-10-20 ~19:25: "probably we need to pop some kind of dialogue to chose the mode on 3 clicks: shard act
# 4 as an entry". Announced kinds besides the act kinds (each act kind not offered is announced by itself)
COMING: tuple[Coming, ...] = ()


def coming_kinds(offered: Iterable[str] | None = None) -> tuple[Coming, ...]:
    """The announced kinds no kind of `offered` (keys; `loop_kinds()` by default) stands for yet: COMING, then each
    act kind not offered (its script not ready, or actloop.ENABLED off)."""
    keys = tuple(loop_kinds() if offered is None else offered)
    acts = tuple(Coming(kind.key, kind.name, kind.word, kind.metric) for kind in ACT_KINDS.values())
    return tuple(coming for coming in (*COMING, *acts) if not any(key.startswith(coming.key) for key in keys))


def kind_of(area: int | None) -> Kind | None:
    """The kind whose levels or town `area` is; None for the shared Fortress, the lobby, elsewhere."""
    return next((kind for kind in KINDS.values() if area in kind.levels or area == kind.home), None)


# The legs, as the HUD says them.
NEXT_GAME = 'next game'
# The town visit (macros/visit.py `visit`): each stop once, only with something to do (the player, 2026-10-18: "we
# visit the stash only ONE time, no running back and forward")
TOWN = 'town visit'
TO_THE_CHESTS = 'to Lower Kurast'
CHESTS = 'the chests'
PICK_UP = 'what is left'
PORTAL = 'Town Portal'
TO_THE_FORTRESS = 'to Pandemonium Fortress'
LEAVE = 'Save and Exit'
TO_THE_CATACOMBS = 'to the Catacombs'  # Andariel's legs: the waypoint to Catacombs Level 2
DOWN = 'down the Catacombs'  # Levels 2 and 3: the level run to the stairs, then through
FIGHT_ANDARIEL = 'Andariel'  # the level run on Level 4: her fight
# A trip to town for room (`Loop.trip`): portal, the Fortress's session, back by the Encampment and the portal
TRIP = 'to town for room'
TO_THE_ENCAMPMENT = 'to the Rogue Encampment'
THROUGH_PORTAL = 'back through the portal'
# Baal's legs (`baal_leg`, 2026-10-25): the waypoint to the Worldstone Keep Level 2; Levels 2 and 3 as the Catacombs'
# (the level run to the stairs, rushed, then through); on the Throne the level run, fighting, for its route stages (the
# stand, the hall, the five waves to Lister: macros/hunting/throne.py `wave_goal`); the portal to the Chamber once Baal
# left his throne (the way on: running/legs.py `throne_shut`, teleport.py `baal_gone`); in the Chamber his fight
TO_THE_KEEP = 'to the Worldstone Keep'
DOWN_THE_KEEP = 'down the Worldstone Keep'
FIGHT_THRONE = "the Throne's waves"
TO_THE_CHAMBER = 'into the Worldstone Chamber'
FIGHT_BAAL = 'Baal'
TO_HARROGATH = 'to Harrogath'  # a trip's and the Gheed's swap's way back from the Fortress (TO_THE_ENCAMPMENT's)
# A spare Northern Worldstone Shard used on act 5 before the waypoint, once a game (actloop.py NORTHERN_FOR_BAAL; the
# player, 2026-10-25 ~12:50: "keep northern shards +1, if we can - use before running baal")
BAAL_SHARD = 'a Northern shard for act 5'
# The kinds' towns the Fortress's way back goes to (`gheeds_leg`, `boss_town_leg`)
HOME_LEGS = {ROGUE_ENCAMPMENT: TO_THE_ENCAMPMENT, HARROGATH: TO_HARROGATH}
# A game's prebuff in these towns may fail and is cast again on the kind's first level (`next_game`, DOWN's
# `prebuff_once`): the Encampment's start NPCs refuse Consume (routines.py TOWN_NPCS); Harrogath's start is not played
# by the loop yet (2026-10-25), so a refusal there must not cost a Baal game either
PREBUFF_LATER = {ROGUE_ENCAMPMENT: 'Catacombs 2', HARROGATH: 'the Worldstone Keep 2'}
# The Gheed's swap (macros/charms.py; the player, 2026-10-18: "put our own gheed into SHARED tab; go back and pick new
# one; go to town, identify; check what is better")
SWAP_OUT = "Gheed's Fortune away"
GHEED_STASH = "Gheed's Fortune onto a shared page"
SWAP_BACK = "Gheed's Fortunes to compare"
GHEED_CHOOSE = "the better Gheed's Fortune"
# The terror zone kinds' swap leg back in the level (tzloop.py, agenda.py `gheeds_package`, 2026-10-19)
GHEED_PICK = "the new Gheed's Fortune"
# `Loop.gheed`, the swap's stage
OUT, PICK, CHOOSE, RETURN = 'out', 'pick', 'choose', 'return'
# Trips for room a game (`Loop.may_trip`; the player, 2026-10-18: "one game can do several trips to the town"), each
# after one that made room. Three: two were needed once in 173 cycles (2026-10-18); a trip is ~37 s
TRIPS_A_GAME = 3
# The terror zone kinds' (`Kind.packaged`): their games run 40+ min over several acts, and three trips ran out at
# 19:02:56 on 2026-10-21 (a Large Charm on the ground, the loop stopped; the player: "it is just a time to visit the
# town, but it seems that this part of the logic is broken"). Each still only after one that made room
TRIPS_A_ZONE_GAME = 8
# A zone kind's game trips for room while the last trip made room, past TRIPS_A_ZONE_GAME (2026-10-22 21:32: cyberg65,
# a shard game of several acts 2.6 h long, stopped on its 9th need with a set Occult Codex on the ground, though trip 8
# went from 4 cells free to 22; the player: "one game can do several trips to the town", "use all overflow shards =>
# maybe more acts"). A trip that made nothing still ends the trips. False: TRIPS_A_ZONE_GAME caps them
TRIPS_BY_GAIN = True
# The cube is tried for room again once the inventory changed since its last try (`Loop.cube_tried`): a cube that moved
# nothing leaves the cells as they were, so the next room rule follows. False: once a game
CUBE_PER_NEED = True
# The merc's and the empty belt's trips (macros/merc.py TRIPS_A_GAME, pinned equal by test_loop.py), on top of the
# room's: the zone legs' bounds count them too (2026-10-21, the player: "we have lost merc -> probably better retreat
# to the town and refill hp potions in the belt")
MERC_TRIPS = 4
# How often one leg may be made in one game before the loop gives up on it (default REPEAT).
REPEATS = {PICK_UP: 20, CHESTS: 3, DOWN: 12, FIGHT_ANDARIEL: 3}  # DOWN: the pickups at the stairs too
# The Throne's legs (2026-10-25, unplayed as legs: bounds by the act 5 shard games' Throne): the waves' level run again
# after a trip or a run ended early; the way on a level run while the portal is shut (the hall, Baal's walk), then the
# press, again after a click that did not take
REPEATS |= {DOWN_THE_KEEP: 12, FIGHT_THRONE: 8, TO_THE_CHAMBER: 8, FIGHT_BAAL: 3}
# Each trip and the swap (twice) go to the Fortress and back; once more at an Andariel game's start
REPEATS |= {
    TRIP: TRIPS_A_GAME,
    TO_THE_FORTRESS: 1 + TRIPS_A_GAME + 2,
    TO_THE_ENCAMPMENT: TRIPS_A_GAME + 2,
    TO_HARROGATH: TRIPS_A_GAME + 2,
    THROUGH_PORTAL: TRIPS_A_GAME + 2,
}
# A route begun with the cube full and the loop's inventory cells partly filled starts with the town visit (the player,
# 2026-10-19 21:20: "if at the beginning of route we have full cube at least partially filled inventory - we visit
# town"): at most this many a game, each after something new was picked up (`route_full`)
ROUTE_VISITS = 3
# FOLD_AT_ROOT (2026-10-23, rca/2026-10-23/exp-town-findings.md): a zone kind's root change passes through a town (its
# Town Portal, then the waypoint to the next root), so the town visit is made there (`fold_due`) once the room is under
# FOLD_ROOM cells and the visit would take FOLD_GAIN cells or more away, instead of a `Town Portal for room` trip a few
# minutes later (Town Portal, the waypoints both ways, back through the portal: ~20 s more than the visit itself, and
# the level under way split in two). In cyberg46 (4 h, one game) 11 trips went at 0-7 cells free, 15 room packages in
# all; the replay at FOLD_ROOM 10 folds 7 of them into the root change before: 2.59 -> 2.23 min/h in town for room.
# A higher FOLD_ROOM visits too often (14: 2.64 min/h). False: the visit only when due (`visit_due`), as before
FOLD_AT_ROOT = True
FOLD_ROOM = 10
FOLD_GAIN = 6
# A game's visits: the start's, each trip's, one cut by the player's hand, the routes' own
REPEATS |= {TOWN: 1 + TRIPS_A_ZONE_GAME + 1 + ROUTE_VISITS}
# The terror zone kinds' legs (tzloop.py): each bound a game's worth (~8 excursions of up to 7 levels)
TZ_WAYPOINT, TZ_LEVEL, TZ_LOOT, TZ_PICKUP = 'TZ waypoint', 'TZ level', 'TZ loot', 'TZ pickup'
TZ_NEXT_LEVEL, TZ_PORTAL, TZ_BACK = 'TZ next level', 'TZ Town Portal', 'TZ back through the portal'
# The Gheed's swap: four waypoints and two portals back (agenda.py `gheeds_package`)
# TZ_LEVEL 60: a shard's whole act and the rotation in one game (the player, 2026-10-20 ~21:30: "make sure, that we're
# farming until it's done"; was 40)
# TZ_WAYPOINT 20 + ...: act 3's 16 waypoint trips and the visits after them (the act 3 agent, 2026-10-20; was 12 + ...)
REPEATS |= {TZ_WAYPOINT: 20 + 2 * (TRIPS_A_ZONE_GAME + MERC_TRIPS) + 4, TZ_LEVEL: 60, TZ_LOOT: 20, TZ_PICKUP: 20}
# The Canyon's tour of its seven tombs adds up to three ways on a tomb: the Canyon's run to its entrance, the press
# through, the way back (2026-10-20, tzroutine.py `Excursion.onward`)
TOUR_WAYS = 3 * len(TOMBS)
REPEATS |= {TZ_NEXT_LEVEL: 30 + TOUR_WAYS}
# TZ_PORTAL 20 + ...: a shard's whole act, act 3's 15 trips each ending in a Town Portal (2026-10-20; was 10 + ...)
REPEATS |= {TZ_PORTAL: 20 + TRIPS_A_ZONE_GAME + MERC_TRIPS, TZ_BACK: 1 + TRIPS_A_ZONE_GAME + MERC_TRIPS + 2}
# The merc's and the belt's trip leg (macros/merc.py MERC_TRIP): each of MERC_TRIPS
MERC_TRIP = 'merc trip'
REPEATS |= {MERC_TRIP: MERC_TRIPS}
# The legs one merc or belt trip makes, each a time: the bounds above count MERC_TRIPS of them, a game's trips past it
# (merc.py BELT_TRIPS_BY_GAIN, `Trips.past_cap`) add theirs (`Loop.count`)
MERC_TRIP_LEGS = {MERC_TRIP: 1, TZ_PORTAL: 1, TZ_WAYPOINT: 2, TOWN: 1, TZ_BACK: 1}
# Zone navigation (macros/zonenav.py): every level of an act entered from its parent and climbed out of, each way in
# made up to three times (the run to the door, the press, a run stopped at another door on the way) and each climb
# twice. Act 1 has 37 levels
ZONE_LEVELS = 40
TZ_UP = 'TZ up'  # the climb to the parent level by the way back (zonenav.py UP_LEVEL)
REPEATS |= {TZ_NEXT_LEVEL: max(REPEATS[TZ_NEXT_LEVEL], 3 * ZONE_LEVELS), TZ_UP: 2 * ZONE_LEVELS}
# The town visit at a level's boundary (zonenav.py VISIT): Town Portal and back through it, up to TRIPS_A_GAME more
REPEATS |= {TZ_BACK: REPEATS[TZ_BACK] + TRIPS_A_GAME}
TZ_OUT = 'TZ out of town'  # the walk out of a town into a trip's first level (macros/townexit.py)
REPEATS |= {TZ_OUT: 3}
TZ_SHARD = 'Worldstone Shard'  # the act kind's shard in the Fortress (macros/actloop.py): once a game, a hand again
REPEATS |= {TZ_SHARD: 2}
# The legs bound by one act's worth a game: each act of a shard over the limit played in the game after the kind's
# own adds its bound again (actloop.py OVERFLOW, 2026-10-21: act 5 after act 3 stopped the act harness's walk at
# "TZ Town Portal again and again")
ACT_LEGS = frozenset(
    (TZ_WAYPOINT, TZ_LEVEL, TZ_LOOT, TZ_PICKUP, TZ_NEXT_LEVEL, TZ_PORTAL, TZ_BACK, TZ_UP, TZ_OUT, TOWN)
)
# Beset (`beset`): the level run fights the attacker, then the ground's valuables one a leg (runner.py `_fetch`)
FIGHT_BACK = 'fight back'
PICK_BACK = 'what the fight back left'
REPEATS |= {FIGHT_BACK: 5, PICK_BACK: 20}
# Seconds after her fight's end before her level is left with nothing to pick up: drops land through her death
# animation, the last 1.7 s after the kill (takes 11:39-11:48, 2026-10-18)
DROPS_LAND = 2.0
# The same from her kill as the service saw it (terror/bosses.py KILLED_AT); DROPS_LAND covers a kill it missed
DROPS_AFTER_KILL = 1.9
KILL_FRESH = 120.0  # seconds: a kill older than this is another game's
# Drops picked up at most at a game's end before the guard's read (`Loop.last_look`)
LAST_PICKS = 8
UNREAD = 'unread'  # the guard's word for a ground it could not read (running/valuables.py `_valuable_left`)
REPEAT = 2
GAME_SECONDS = 240.0  # a game longer than this is left (games take 40-75 s, 2026-10-17)
# Added to GAME_SECONDS per trip for room (`overdue`): the trips' p90 (rca/2026-10-18/trips-and-towns-findings.md §2.4)
TRIP_SECONDS = 80.0
# A game that still owes levels or bosses (tzloop.py `owed`) is cut by no progress, not by its clock: a kill, a level
# finished or cleared, a new level entered (`progress_seen`). The player, 2026-10-22: "no save/exits on games with
# worldstone hards spent! you must finish the game correctly"; the 3900 s cap stopped cyberg65 at 20:09 mid full
# clear at 113 kills/min. The longest fruitless run seen is the 4.5 min tomb tour, which killed on the way
NO_PROGRESS_SECONDS = 300.0
# OFF_TIME_NOT_COUNTED (2026-10-25 17:43:37, game cybergg77: the player turned the loop on in a game they had been in
# for minutes with it off, and "no progress for 300 s" stopped it at once, three times): the watchdog's clocks
# (`progress_seen`'s no-progress clock and `overdue`'s game clock) start anew while the loop is off, as the focus wait
# does ("the player's time, not the loop's"). False: they ran on while it was off, as before.
OFF_TIME_NOT_COUNTED = True
LOADING_SECONDS = 10.0  # for a game's character to be read after it shows as in a game
# A stand this long within STILL_UNITS is the loop stuck (the player, 2026-10-17: "we stuck, but didn't detect it in
# time"); the longest good stand is a shop visit, under 15 s
STILL_SECONDS = 45.0
# Under the stall's leave, a recovery first (running/watch.py, hunting/judging.py `recover`): a stand this long asks
# the hunt for a new target (the fight goal and what barred it left alone, a clearing goal passed), once a stand; the
# leave at STILL_SECONDS stays the last resort. Kurast Sewers 1, 17:51:43-17:52:29 on 2026-10-21: 45 s by an elite
# behind a wall, the game left with act 3 and act 5 to go (rca/2026-10-21/no-hits-findings.md §7). None: no recovery.
STILL_RECOVER: float | None = 20.0
STILL_UNITS = 2.0
RECOVERIES = 3
RECOVERY_SECONDS = 600.0
RECOVERY_PAUSE = 30.0  # past RECOVERIES in RECOVERY_SECONDS: a pause before the next leg, not a stop (`recover`)
COOLING_SLICE = 1.0  # seconds: the pause is slept in slices, a cancelled run ends it (`leg`)
# Standing outside a fight and losing BESET_LOSS of max life within BESET_SECONDS is beset (`beset`): the attacker is
# fought back (FIGHT_BACK; the player, 2026-10-19: "we stood still while under attack and almost died"); a hit there
# was 4-8 %
BESET_SECONDS = 4.0
BESET_LOSS = 0.05
# Beset again this soon after fighting back (`beset_again`): the fight cannot be won, the game is left (2026-10-19:
# a level run's fight takes 5-20 s, the loop's next legs a minute)
BESET_AGAIN_SECONDS = 60.0
# 2026-10-24 (rca/2026-10-24/game5-findings.md): 23:30:44-23:31:05 on 2026-10-23, Halls of the Dead Level 2, a tier 5
# Herald pack on the character: 21 'TZ next level' legs in 21 s, each ended or handed on within 0.5 s, attack mode
# flapping off and on, no strike and no move; the merc fell, then the character. A leg made SPIN_LEGS times in a row
# each within SPIN_GAP s of the last, in one level of one game, with a hostile within hunting/base.py SIGHT, is no
# leg: the next is FIGHT_BACK (the attacker fought to its end, then its ground), as a stand beset outside a fight
# (`beset`), when the character's life fell by SPIN_FALL of its maximum from one of those legs' starts to the next:
# the replay of every session of 2026-10-21..24 (probe.log legs, the takes' frames) found 135 such runs of legs by
# timing, level and a hostile in sight (34 sessions: Town Portals held for a fight, Teleport sweeps, pickups) and 4
# with the fall: this death, 18:42:53 and 05:14:42 on 2026-10-23 (the same "no route stage" hand-off, hurt) and one
# pickup run at 14:37:13. False: not gated. Its FIGHT_BACK posts the level run the TZ legs post (running/legs.py
# `fight_back` and `level_run`: PICKUP, rush False, the agenda), so it plays the fight the spinning legs played; the
# spin itself is pursuit.py FIGHT_BEFORE_END's (live). On only with a fight back that holds the fight.
LEG_SPIN = False
SPIN_LEGS = 3
SPIN_GAP = 1.5
SPIN_FALL = 0.05


class GameId(NamedTuple):
    """A game told from the next by its name and the player's unit id (game/records.py `Loot.game`): names come round
    again, unit ids do not. Seed of the per-game record (rca/2026-10-18/arch-loop-orchestration.md Option B)."""

    name: str
    player: int

    def __str__(self) -> str:
        return f'{self.name} (player unit {self.player})'


@dataclass(frozen=True)
class LegHands:
    """What the runner hands a leg (runner.py `_loop_hands`). `take_one()`: one drop or a valuable seen, False with
    neither; `way_on()`: the press through the way on, else the level run to it; `left()`: a valuable still down."""

    level_run: Callable[[], None]
    take_one: Callable[[], bool]
    visit: Callable[[Exit], object] | None = None
    identify: Callable[[tuple[Carried, ...]], object] | None = None
    bring: Callable[[list[Carried]], int] | None = None
    way_on: Callable[[], None] | None = None
    at_way: Callable[[], bool] | None = None  # the character at the way on, where `way_on` presses (legs.py)
    fight: Callable[[], None] | None = None
    fight_back: Callable[[], None] | None = None  # the level run posted against an attacker (FIGHT_BACK)
    life: Callable[[], tuple[int, int] | None] | None = None  # (life, max life) at the last poll (LEG_SPIN)
    left: Callable[[], str | None] | None = None
    sighted: Callable[[int | None], str | None] = lambda area: None
    # The valuables remembered on the ground as (level, label) (macros/sightings.py; zonenav.py FETCH_ELSEWHERE)
    remembered: Callable[[], tuple[tuple[int | None, str], ...]] = lambda: ()
    terrorized: Callable[[int], bool | None] = lambda area: None
    navigate: Callable[[], None] = lambda: None
    walk_out: Callable[[int], None] | None = None  # the walk out of town into level `to` (macros/townexit.py)
    # The character's inventory key (the shard's right click, macros/actloop.py `use_shard`; 21:42:42 on 2026-10-20:
    # "no inventory key read" left two games at once)
    inventory_key: Callable[[], str | None] = lambda: None
    # A beset recovery's portal return (tzloop.py `perform`, `Loop.danger_return`): None to go back, else the line the
    # loop stops in town with (running/recovery.py `back_for_bosses`, macros/safety.py RETURN_GATE)
    back_for_bosses: Callable[[], str | None] = lambda: None
    # Battle Orders on that return's arrival when due or its age not known (running/legs.py `orders_on_arrival`); what
    # was done, said
    orders_on_arrival: Callable[[], str] = lambda: 'no Call to Arms hands'


@dataclass
class Loop:
    """The loop's memory across its legs; game fields hold the game's name."""

    on: bool = False
    kind: Kind = LK
    placed: bool = False  # the kind told by where the first leg finds the character (`kind_of`)
    chosen: bool = False  # chosen by hand or carried over a restart: kept wherever
    pending: Kind | None = None  # chosen while on (runner.py `choose_kind`): the kind from the next game
    games: int = 0
    prebuffed: str | None = None
    # The game whose pushed room package is a beset recovery's (tzloop.py `danger_trip`): its portal return is asked
    # of the safety's gate first (RETURN_GATE), then Battle Orders on the arrival
    danger_return: str | None = None
    done: str | None = None
    made: Counter[tuple[str, str]] = field(default_factory=Counter)
    # The player's inventory items by (class, x, y), read at the first leg in a game; the rest is the loop's (cube.py)
    own: frozenset[tuple[int, int, int]] | None = None
    # The loop's items still carried, kept across KP_6 presses and in `store` (by character) across restarts
    mine: frozenset[tuple[int, int, int]] = frozenset()
    store: Path | None = None
    # `printed`: unit ids whose stats were last learnt (a swap can put a new charm in the same class and cell)
    printed: frozenset[int] | None = None
    character: str | None = None
    # Keys or Town Portal charges under shop.py MIN_STOCK at the last look
    short: bool = False
    # How Town Portal is cast at the last look (portal.py `portal_source`); None: unread since the start
    portal: PortalSource | None = None
    # The game is to be left from wherever the character is (`recover`)
    abandon: bool = False
    fetch_again: str | None = None  # the game a leg was made again for a valuable left with room (runner.py)
    cooling: float = 0.0  # time.monotonic() before which no leg is made (`recover`, RECOVERY_PAUSE)
    lobby_fails: int = 0  # game creations failed in a row (macros/stops.py `first`, cause 'lobby')
    fought: tuple[str, float] | None = None  # (game, run clock) at her level's first loot leg (`DROPS_LAND`)
    # BAAL_SHARD (actloop.py NORTHERN_FOR_BAAL): the game whose shard step was made, and where the last look in town
    # found a Northern for it ('carried', 'stack'; None: none, or the switch off)
    northern: str | None = None
    northern_ready: str | None = None
    # The bosses read dead in a game (routes/progress.py `dead`): name -> the run clock of the first leg that read it
    # (`landing`: DROPS_LAND from it for a kill KILLED_AT did not see), and the game they belong to
    slain: dict[str, float] = field(default_factory=dict)
    slain_game: str | None = None
    recovered: list[float] = field(default_factory=list)
    current: str | None = None  # the leg working or last made (the HUD's NEXT, runner.py `run_badge`)
    # Looks in a stand outside a fight (`beset`): (when, where, life, game)
    hurt: list[tuple[float, tuple[float, float], int, str]] = field(default_factory=list)
    # Beset (runner.py `_loop_stopped`): the game a fight back is due in, the game whose valuables are fetched after
    # it, and (game, when) of the fight back's last leg (`beset_again`)
    beset_due: str | None = None
    fetch_back: str | None = None
    fought_back: tuple[str, float] | None = None
    # The legs' starts (`spinning`): (when, game, level)
    leg_starts: list[tuple[float, str, int, float]] = field(default_factory=list)
    # (game or None for the lobby, since when) (`overdue`)
    seen: tuple[str | None, float] | None = None
    # (game, since when, the progress mark then) (`progress_seen`, NO_PROGRESS_SECONDS)
    progressed: tuple[str | None, float, tuple] | None = None
    # The level card's marks by label, in tiles (levels/guide.py `marks`): a waypoint out of sight
    marks: Callable[[str], tuple[tuple[float, float], ...]] | None = None
    # The stash's one record (game/stash.py; the player, 2026-10-22: "one object that is used everywhere ... no
    # copies, no stale records"): its full stacks are not picked up (`sold_full`). Its runs/alt-d/full-stacks.json copy,
    # read at a start and written only after a visit, left a 97-stack's Eastern Worldstone Shard at 08:59:26
    stash: Stash = field(default_factory=Stash)
    # The staff's Teleport in the loop's moves while the gold pays for it (`teleports`); None: undecided
    teleports: bool | None = None
    wear: str = '?'  # the most worn item's durability at the last look, for the log
    # The last game looked at (`observe`): kept through the lobby and a KP_6 off and on
    game_id: GameId | None = None

    @property
    def sold_full(self) -> frozenset[int]:
        """The full stacks' classes not picked up (town.py `sold_full`): runes and materials, never gems or potions;
        none while the stash is unknown (unknown means take)."""
        return sold_full(self.stash.full())

    # A repair due (repair.py `wants`), and the game count of a visit that raised nothing (RETRY_GAMES)
    repair: bool = False
    repair_failed: int | None = None
    # No room for a valuable: the loop's items into the cube at the next leg, once a game (`room_tried`)
    make_room: bool = False
    # The inventory and cube closed at the loop's first leg: turned on, the game is the loop's (a cancelled cube step
    # left them open at 23:34:19 on 2026-10-19 and the loop read them as the player's hand)
    tidy_panels: bool = False
    room_tried: str | None = None
    # The inventory's free cells when the cube was tried (`cube_try`): the cube is tried again once they changed
    room_free: int | None = None
    # In town at a route's start with the cube full and the loop's items in the inventory (`ROUTE_VISITS`); the loop's
    # carried units a visit left (game, units), and the route visits made (game, count)
    route_full: bool = False
    visit_units: tuple[str, frozenset[int]] | None = None
    route_visits: tuple[str, int] | None = None
    # Then one of the loop's to-identify items dropped for the block (cube.py `drop_for`), once a game (`dropped`)
    drop_room: bool = False
    dropped: str | None = None
    # The trade (`TOWN`): cells free in inventory and cube, anything a visit takes away (`carrying`)
    free: int | None = None
    carrying: bool = False
    # The cells of the loop's carried items the game's last visit did not leave (all of them before one): what a visit
    # now would take away at most (`fold_due`)
    gainable: int = 0
    visiting: str | None = None
    visited: str | None = None
    waiting: bool = False  # for the game window's focus (runner.py): watchdogs pause
    moved: tuple[tuple[float, float], float] | None = None  # where the character last moved to, and when (`still`)
    moved_in: str | None = None  # the game `moved` was read in (`still`: a new game counts afresh)
    moved_kills: int = 0  # the kills counted when `moved` was set (`still`: a stand that kills is no stall)
    still_recovered: float | None = None  # the stand (`moved`'s clock) a recovery was asked in (`recovery_due`)
    counted_in: str | None = None  # where `made` counts (`count`)
    # A trip to town for room (runner.py `_loop_stopped`); `forgiven`: (game, trip number) whose sightings were forgiven
    trip_due: bool = False
    trip: str | None = None
    trips: int = 0
    fortressed: str | None = None
    portal_at: tuple[float, float] | None = None
    returned: str | None = None
    forgiven: tuple[str, int] | None = None
    trip_free: int | None = None
    trip_gained: int | None = None
    # The merc's and the belt's trips in the game (macros/merc.py `Trips`, BELT_TRIPS_BY_GAIN): one object, changed in
    # place, the service's merc watch counting in it (runner.py) and the game's record keeping it (midgame.py)
    merc_trips: Trips = field(default_factory=Trips)
    # The Gheed's swap, once a game: `parked` the player's on a shared page, `gheed` the stage, `fresh` a new one held
    swap_due: bool = False
    swap: str | None = None
    swap_level: int | None = None
    parked: Parked | None = None
    gheed: str | None = None
    swap_units: frozenset[int] = frozenset()
    fresh: bool = False
    # Clears the level run's give-up memory (runner.py `_forget_given_up`), as `SHUNNED` is cleared
    forget: Callable[[], None] | None = None
    # The terror zone kinds' goals (macros/agenda.py), afresh each game (`Agenda.begin`)
    agenda: Agenda = field(default_factory=Agenda)
    idle: int = 0  # the terror zone kinds' games begun since the last level run (macros/tzloop.py IDLE_GAMES)
    # The terror zone kinds' experience since the loop turned on (macros/experience.py; the player, 2026-10-19: "we
    # should log experience in tz leveling")
    experience: Ledger = field(default_factory=Ledger)
    # A service restart in the middle of a game (macros/midgame.py; the player, 2026-10-21 ~14:50: "pick new code in
    # the middle of the act run, without save/exit, just continue"): the games' records (terror/tracker.py
    # `ZoneTracker.record`, midgame.py RECORD) the game's state is kept in and taken up from at the first leg in it,
    # the game last looked up there, the route progress of the last leg (its facts in the record); the restart waiting
    # for a safe point (midgame.TOWN, SAFE, TRIP), the place the loop stands at for it (the service restarts then:
    # runner.py `restart_due`), the refusal last said; TRIP's: the game whose portal return is the restart's (in the
    # record: midgame.py NAMED), and (game, the portal trips made for the restart in it)
    records: Any = None
    recorded: str | None = None
    facts_from: Any = None
    restart_when: str | None = None
    safe_point: str | None = None
    unsafe_said: str | None = None
    restart_trip: str | None = None
    restart_trips: tuple[str, int] | None = None

    def start(self) -> None:
        self.on, self.made, self.own, self.abandon, self.seen, self.moved = True, Counter(), None, False, None, None
        self.counted_in, self.placed, self.portal, self.printed = None, False, None, None
        self.beset_due, self.fetch_back, self.fought_back = None, None, None
        if OFF_TIME_NOT_COUNTED:
            self.progressed = None  # the no-progress clock from the loop's start, not the game's (17:43:37)
        self.experience = Ledger()
        self.tidy_panels = True

    def recover(self, why: object, now: float) -> bool:
        """Whether the loop goes on after `why` by leaving the game: always but dead. Past RECOVERIES within
        RECOVERY_SECONDS the next leg waits RECOVERY_PAUSE: a stopped loop stood until someone looked (2026-10-17)."""
        if isinstance(why, Dead):
            return False
        self.recovered = [at for at in self.recovered if now - at < RECOVERY_SECONDS]
        if len(self.recovered) >= RECOVERIES:
            self.cooling = max(self.cooling, now + RECOVERY_PAUSE)  # a longer wait set (a zone's) kept
            LOG.warning('Macro: loop: %d recoveries in %.0f s: the next leg after %.0f s (%s)',
                        len(self.recovered) + 1, RECOVERY_SECONDS, RECOVERY_PAUSE, why)  # fmt: skip
        self.recovered.append(now)
        self.abandon = True
        return True

    def overdue(self, game: str | None, now: float) -> bool:
        """Whether the loop has been in `game` (None: the lobby) over GAME_SECONDS plus TRIP_SECONDS a trip. The
        loop's own wait (`cooling`: the next terror zone's) is not counted."""
        if self.seen is None or self.seen[0] != game or now < self.cooling:
            self.seen = (game, now)
            return False
        return now - self.seen[1] > self.allowed_seconds(game) and not self.abandon

    def progress_seen(self, game: str | None, now: float, mark: tuple) -> None:
        """Note `mark` (the kills, the levels finished and cleared, the level: running/watch.py) in `game`: a change, or
        another game, starts the no-progress clock anew."""
        if self.progressed is None or self.progressed[0] != game or self.progressed[2] != mark:
            self.progressed = (game, now, mark)
        elif OFF_TIME_NOT_COUNTED and not self.on:
            self.progressed = (game, now, mark)
            self.seen = (game, now)

    def no_progress(self, game: str | None, now: float) -> bool:
        """Whether `game` has gone NO_PROGRESS_SECONDS with no progress (`progress_seen`); the loop's own wait
        (`cooling`) is not counted."""
        if self.progressed is None or self.progressed[0] != game or now < self.cooling:
            self.progressed = (game, now, self.progressed[2] if self.progressed is not None else ())
            return False
        return now - self.progressed[1] > NO_PROGRESS_SECONDS and not self.abandon

    def over_time(self, game: str | None, now: float, *, owing: bool) -> bool:
        """The watchdog's cut: a game that owes levels or bosses (`owing`) by no progress, any other by its clock."""
        if owing:
            self.overdue(game, now)  # its clock kept for the games that owe nothing
            return self.no_progress(game, now)
        return self.overdue(game, now)

    def allowed_seconds(self, game: str | None) -> float:
        """The cap of `game` (`overdue`): the kind's game_seconds (GAME_SECONDS), each act of a shard over the limit
        played in it after the kind's own its ACT_SECONDS (actloop.py OVERFLOW, 2026-10-21: two acts in one game
        are not cut at the first's cap), TRIP_SECONDS a trip for room."""
        extra = sum(ACT_SECONDS.get(act, ACT_GAME_SECONDS) for act in self.overflow_acts(game))
        return (self.kind.game_seconds or GAME_SECONDS) + extra + TRIP_SECONDS * self.trips_in(game)

    def overflow_acts(self, game: str | None) -> tuple[int, ...]:
        """The acts of shards over the limit played in `game` after the kind's own (actloop.py OVERFLOW: in
        `Agenda.acts` with an overflow outcome); () for another game than the agenda's."""
        agenda = self.agenda
        if game is None or getattr(agenda.game, 'name', agenda.game) != game:
            return ()
        return tuple(act for act in agenda.acts if act in agenda.overflow)

    def recovery_due(self, now: float, game: str | None) -> bool:
        """Whether the stand `still` counts has lasted STILL_RECOVER in `game` with no recovery asked in it yet; the
        recovery is noted as asked. Read after `still` has noted the look (it keeps the stand)."""
        if STILL_RECOVER is None or self.moved is None or game is None or game != self.moved_in:
            return False
        if now - self.moved[1] < STILL_RECOVER or self.still_recovered == self.moved[1]:
            return False
        self.still_recovered = self.moved[1]
        return True

    def still(
        self,
        where: tuple[float, float] | None,
        now: float,
        game: str | None = None,
        kills: int = 0,
        waiting: bool = False,
    ) -> bool:
        """Whether the character has stood within STILL_UNITS over STILL_SECONDS in `game`. A new game counts afresh:
        every game starts at the same waypoint. `now`: time.monotonic(). `kills`: the hunt's running kill count
        (combat/score.py `LiveScore.killed`): a kill counts the stand afresh, a fight in place is no stall (Worldstone
        Keep 2 at 04:45:58-04:46:43 on 2026-10-20: 45 s in one place, full life, 13 of 35 Stone Skin hostiles killed,
        the game left mid-fight). `waiting`: the run waits by design (the Throne's waves, hunting/throne.py
        `Waves.due`, bounded there by WAVE_WAIT): the stand counts afresh (the player, 2026-10-20: "tz leveling should
        do baal and trone fight")."""
        if where is None:
            return False
        cooling = now < self.cooling  # the recoveries' pause is the loop's own wait
        if (
            self.moved is None
            or cooling
            or waiting
            or math.dist(where, self.moved[0]) > STILL_UNITS
            or game != self.moved_in
            or kills != self.moved_kills
        ):
            self.moved, self.moved_in, self.moved_kills = (where, now), game, kills
            return False
        if now - self.moved[1] > STILL_SECONDS and not self.abandon:
            self.moved = (where, now)  # once: the next stand counts afresh
            return True
        return False

    def beset(
        self,
        where: tuple[float, float] | None,
        life: tuple[int, int] | None,
        now: float,
        game: str | None,
        area: int | None,
    ) -> bool:
        """Whether the character stood (STILL_UNITS) losing BESET_LOSS of max life within BESET_SECONDS, counted as life
        missing from the maximum (a buff's end lowers both). `life`: (points, maximum). Asked only outside a fight
        (runner.py `poll`); once, then afresh; never in town, the lobby or while leaving. `now`: time.monotonic()."""
        if where is None or life is None or game is None or area is None or area in TOWN_IDS or life[1] <= 0:
            self.hurt.clear()
            return False
        self.hurt = [
            look
            for look in self.hurt
            if now - look[0] <= BESET_SECONDS and look[3] == game and math.dist(look[1], where) <= STILL_UNITS
        ]
        # Missing life, not points: Battle Orders running out took 2937/2937 to 1886/1886 with no hit and left the
        # game as beset (Lost City, 01:08:29 on 2026-10-20)
        missing = life[1] - life[0]
        self.hurt.append((now, where, missing, game))
        if missing - min(look[2] for look in self.hurt) >= BESET_LOSS * life[1] and not self.abandon:
            self.hurt.clear()
            return True
        return False

    def beset_again(self, game: str | None, now: float) -> bool:
        """Whether a fight back's last leg in `game` was within BESET_AGAIN_SECONDS. `now`: time.monotonic()."""
        fought = self.fought_back
        return fought is not None and game is not None and fought[0] == game and now - fought[1] <= BESET_AGAIN_SECONDS

    def fight_back_due(self, game: str) -> None:
        """Beset in `game`: its next leg fights the attacker (FIGHT_BACK), the ones after fetch the valuables."""
        self.beset_due, self.fetch_back = game, None

    def spinning(self, world: World, now: float, life: tuple[int, int] | None) -> bool:
        """LEG_SPIN: whether this leg, with the SPIN_LEGS - 1 before it, each started within SPIN_GAP s of the last in
        the level `world` is in, comes with a hostile within SIGHT of the character and life falling by SPIN_FALL
        between two of their starts: the legs end at once in a fight. Each leg's start is kept. `now`:
        time.monotonic(); `life`: (points, maximum) as the runner's poll read it."""
        player = world.player
        if not LEG_SPIN or not world.in_game or player is None or player.in_town or player.mode in DEAD or not life:
            self.leg_starts.clear()
            return False
        here = (world.game_name, player.area)
        kept = [start for start in self.leg_starts if (start[1], start[2]) == here]
        self.leg_starts = [*kept, (now, *here, float(life[0]))][-SPIN_LEGS:]
        times = [start[0] for start in self.leg_starts]
        if len(times) < SPIN_LEGS or any(later - earlier > SPIN_GAP for earlier, later in pairwise(times)):
            return False
        lives = [start[3] for start in self.leg_starts]
        if not any(later < earlier - SPIN_FALL * life[1] for earlier, later in pairwise(lives)):
            return False  # not hurt: legs that end fast for their own reasons (a warp, a pickup, a portal)
        from inventory_tracking.macros.hunting.base import SIGHT, hostiles  # late: the hunt builds on the loop

        near = [m for m in hostiles(world) if math.dist((player.x, player.y), (m.x, m.y)) <= SIGHT]
        if not near:
            return False
        self.leg_starts.clear()  # afresh after the fight back
        LOG.info('Macro: loop: %d legs in %.1f s in level %d with %d hostiles within %.0f: the fight first (LEG_SPIN)',
                 SPIN_LEGS, times[-1] - times[0], player.area, len(near), SIGHT)  # fmt: skip
        return True

    def after_beset(self, world: World) -> str | None:
        """FIGHT_BACK or PICK_BACK when one is due where `world` is; None otherwise (out of the game, in a town, dead,
        or leaving: the due one dropped)."""
        player = world.player
        if not world.in_game or player is None or player.mode in DEAD or player.in_town or self.abandon:
            self.beset_due = self.fetch_back = None
            return None
        game = world.game_name
        if self.beset_due == game:
            return FIGHT_BACK
        if self.fetch_back == game:
            return PICK_BACK
        self.beset_due = self.fetch_back = None
        return None

    def stop(self) -> None:
        self.on = False

    def sort(
        self,
        held: frozenset[tuple[int, int, int]],
        name: str | None,
        loose: frozenset[tuple[int, int, int]] = frozenset(),
    ) -> None:
        """Tell `held` apart: at the first look the player's are neither the loop's (`mine`, from `store`) nor `loose`
        (unidentified, runes, gems); then the loop's are what is not the player's."""
        if self.own is None:
            self.mine = self.mine or self._stored(name)
            # Items moved by hand change cells and the store loses them: loose ones are the loop's (2026-10-18 10:28)
            taken = (held & loose) - self.mine
            if taken:
                LOG.info("Macro: loop: %d items unidentified, runes or gems taken for the loop's", len(taken))
            self.own = held - self.mine - loose
        mine = held - self.own
        if mine != self.mine:
            self.mine = mine
            self._keep(name)

    @property
    def volatile(self) -> Volatile:
        return Volatile(self.store.parent / STORE_FILE if self.store is not None else None)

    def protected(self, pack: Pack, name: str, loose: frozenset[tuple[int, int, int]]) -> frozenset[Cell]:
        """The character's protected cells; none kept: seeded from `pack` as `sort` tells the player's items."""
        store = self.volatile
        cells = store.protected(name)
        if cells is None:
            self.mine = self.mine or self._stored(name)
            theirs = (own_of(pack.items) - self.mine - loose) | {(i.txt, i.x, i.y) for i in pack.items if i.txt in KEPT}
            cells = store.seed(name, [i for i in pack.items if (i.txt, i.x, i.y) in theirs], "the loop's first look")
        return cells

    def tell(
        self,
        pack: Pack,
        name: str,
        loose: frozenset[tuple[int, int, int]] = frozenset(),
        item_stats: Stats | None = None,
    ) -> None:
        """`own` at every leg from the protected cells (macros/volatile.py); the player's items' stats learnt when it
        changes."""
        first = self.own is None
        cells = self.protected(pack, name, loose)
        self.own, self.character = players_of(pack, cells), name
        if first:
            LOG.info("Macro: loop: volatile cells %s ('#' the player's); %d of the player's items; protected cells "
                     'empty: %s', picture(cells), len(self.own), sorted(empty(pack, cells)) or 'none')  # fmt: skip
        theirs = [i for i in pack.items if (i.txt, i.x, i.y) in self.own and i.txt not in KEPT]
        units = frozenset(i.unit_id for i in theirs)
        if item_stats is None or units == self.printed:
            return
        self.printed = units
        found = []
        for item in theirs:
            stats = item_stats(item.unit_id)
            if stats:
                found.append(print_of(item, stats))
        if new := self.volatile.learn(name, found):
            LOG.info("Macro: volatile cells: %d more of the player's items known by their stats", new)

    def told(self, pack: Pack, name: str, item_stats: Stats | None = None) -> frozenset[tuple[int, int, int]] | None:
        """The player's items in `pack` told from the loop's (`own`), by the protected cells (`tell`) or, with no
        store (tests), by `sort`; unidentified magic-or-better items, runes and gems count as the loop's at a first
        look. Every activity's no-room routine asks this too (runner.py `_room_own`)."""
        loose = frozenset(
            (i.txt, i.x, i.y) for i in pack.items if (not i.identified and i.quality >= MAGIC) or i.txt in RESOURCES
        )
        if self.store is not None:
            self.tell(pack, name, loose, item_stats)
        else:
            self.sort(own_of(pack.items), name, loose)
        return self.own

    def players_item(self, item: Carried, stats: Mapping[int, int]) -> bool:
        """Whether `item` is the player's by its stats (volatile.py `prints`): never sold nor dropped."""
        from inventory_tracking.macros.volatile import is_players

        return self.store is not None and is_players(item, stats, self.volatile.prints(self.character))

    def visit_due(self, game: str) -> bool:
        """Whether a town visit is due in `game` (once): room low (or a trip) with anything to take away, or, except at
        a game's end, short stock or a repair. Any errand is the whole visit (the player, 2026-10-17)."""
        if self.visited == game and not self.route_full:
            return False
        if self.visiting == game and self.visited != game:
            return True  # cut short: made again from what is left
        cramped = self.tripping(game) or self.room_low
        return (cramped and self.carrying) or (self.done != game and (self.short or self.repair))

    @property
    def room_low(self) -> bool:
        """Whether the room is low for a visit: under TRADE_ROOM cells, or a route starting with the cube full
        (`route_full`)."""
        return (self.free is not None and cells_low(self.free)) or self.route_full

    def fold_due(self, world: World) -> bool:
        """FOLD_AT_ROOT: whether a zone kind standing in a town between its levels (a root change) makes the town visit
        on the way: under FOLD_ROOM cells free, something to take away, FOLD_GAIN cells or more new since the game's
        last visit (a visit that left the room low is not made again for nothing), no trip for room under way (its
        package has its own visit). `visit_due` decides the rest, as before."""
        player = world.player
        if not FOLD_AT_ROOT or not self.kind.agenda or not world.in_game or player is None or not player.in_town:
            return False
        game = world.game_name
        if self.free is None or self.free >= FOLD_ROOM or not self.carrying or self.gainable < FOLD_GAIN:
            return False
        return not self.tripping(game)

    def route_starts_full(
        self, world: World, cube: tuple[str, ...], items: list[Carried], carried: list[Carried]
    ) -> bool:
        """Whether a route begun from where `world` is starts with the town visit: in a town, the cube's rows `cube`
        with no SURE_BLOCK free and some of the loop's `items` in the inventory (the volatile cells: never the
        player's), under ROUTE_VISITS this game, and, after a visit this game, something of `carried` it did not leave
        (no visit again for a keeper that waits in the cube)."""
        player = world.player
        if not world.in_game or player is None or not player.in_town or not cube or not items:
            return False
        if Grid(cube).has_room(SURE_BLOCK):
            return False
        game = world.game_name
        if self.route_visits is not None and self.route_visits[0] == game and self.route_visits[1] >= ROUTE_VISITS:
            return False
        left = self.visit_units[1] if self.visit_units is not None and self.visit_units[0] == game else None
        if self.visited == game and (left is None or not {i.unit_id for i in carried} - left):
            return False
        if not self.route_full:
            LOG.info("Macro: loop: a route starts with the cube full and %d of the loop's items in the inventory: the "
                     'town visit first', len(items))  # fmt: skip
        return True

    def tripping(self, game: str) -> bool:
        """Whether a trip for room is under way in `game` (begun, not back through the portal)."""
        return self.trip == game and self.returned != game

    def trips_in(self, game: str | None) -> int:
        """The trips for room made in `game`."""
        return self.trips if game is not None and self.trip == game else 0

    def cube_try(self, game: str | None) -> None:
        """Room is made in the cube for a valuable in `game` (`cube_tried`), at the inventory's free cells now."""
        self.make_room, self.room_tried, self.room_free = True, game, self.free

    def cube_tried(self, game: str | None) -> bool:
        """Whether the cube was tried for room in `game` and the inventory has not changed since (CUBE_PER_NEED);
        else, as before, once a game. 2026-10-22 22:33: in a 3 h shard game the cube made room at 22:18 and 22:24, and
        at 22:33 an Amulet the cube had room for was "the cube was tried in this game": the loop stopped."""
        if self.room_tried != game:
            return False
        return not CUBE_PER_NEED or self.room_free is None or self.room_free == self.free

    def may_trip(self, game: str | None) -> bool:
        """Whether another trip may be made in `game`: none under way, under TRIPS_A_GAME (a zone kind's
        TRIPS_A_ZONE_GAME), and the last made room (or it is unread)."""
        made = self.trips_in(game)
        if made == 0:
            return True
        if game is None or self.tripping(game):
            return False
        if TRIPS_BY_GAIN and self.kind.packaged and self.trip_gained is not None:
            return self.trip_gained > 0  # a trip that made room is no ping-pong, however many came before
        most = TRIPS_A_ZONE_GAME if self.kind.packaged else TRIPS_A_GAME
        if made >= most:
            return False
        return self.trip_gained is None or self.trip_gained > 0

    def repair_waited(self) -> bool:
        """Whether a repair may be tried: not for RETRY_GAMES games after one that raised nothing."""
        return self.repair_failed is None or self.games - self.repair_failed >= RETRY_GAMES

    def exit_of(self, game: str) -> Exit:
        """How the visit in `game` ends: LEAVE at a game's end, the portal on a trip, else the waypoint."""
        if self.done == game:
            return Exit.LEAVE
        if self.tripping(game):
            return Exit.PORTAL
        return Exit.WAYPOINT

    def _stored(self, name: str | None) -> frozenset[tuple[int, int, int]]:
        if self.store is None or name is None:
            return frozenset()
        try:
            rows = json.loads(self.store.read_text()).get(name, [])
            return frozenset((int(txt), int(x), int(y)) for txt, x, y in rows)
        except OSError, ValueError, TypeError, AttributeError:
            return frozenset()

    def _keep(self, name: str | None) -> None:
        if self.store is None or name is None:
            return
        try:
            kept = json.loads(self.store.read_text()) if self.store.exists() else {}
            kept[name] = sorted(self.mine)
            self.store.write_text(json.dumps(kept))
        except (OSError, ValueError, TypeError, AttributeError) as error:
            LOG.info("Macro: the loop's items are not kept in %s: %s", self.store, error)

    def begin_trip(self, game: str) -> None:
        """A trip for room starts in `game` (TRIP, tzloop.py `trip`): counted, with its own Fortress, way back and visit
        (none of the game's earlier ones count for it)."""
        self.trips = self.trips_in(game) + 1
        self.trip_due, self.trip, self.fortressed = False, game, None
        self.trip_free, self.trip_gained = self.free, None
        self.returned = None
        self.visiting = self.visited = None
        midgame.keep(self)  # a trip begun is in the game's record at once
        self.route_full = False  # the trip's visit is no route's start (`route_starts_full`)

    def back_through_portal(self, run: Run, game: str) -> None:
        """Back through the portal (`portal_at`), a trip's end told first; the restart's own (`back_after_restart`)."""
        if self.restart_trip == game:
            self.back_after_restart(run)
            return
        if self.tripping(game):
            self._back_from_trip()
        self.returned = game
        through_portal(run, self.portal_at)

    def back_after_restart(self, run: Run) -> None:
        """midgame.TRIP's return: back through the portal left for the restart, found by the place the character came
        to in town (`portal_at`, in the game's record) and the open portal nearest it; with none taken and the character
        still in town (the portal gone), said, and the loop's own way back from town (the agenda's next goal, the
        kind's next leg) instead of a stop. The player's hand and a cancel stop it as any leg's."""
        # The watch tools read it (d2-loop-watch logwords.py TRIP_BACK)
        LOG.info('Macro: loop: back through the portal left for the restart')
        try:
            through_portal(run, self.portal_at)
        except Hand, Cancelled:
            raise
        except Abort as stop:
            player = run.world().player
            if player is None or not player.in_town:
                raise
            # The watch tools read it (d2-loop-watch logwords.py TRIP_NO_PORTAL)
            LOG.info("Macro: loop: the portal left for the restart is not taken (%s): the loop's own way back from "
                     'town', stop)  # fmt: skip
        self.restart_trip = None

    def begin_restart_trip(self, world: World) -> None:
        """midgame.TRIP at a field level's safe moment: its package pushed (Town Portal, back through the portal after
        the restart), the stand in town then TOWN's (`hold_at_safe_point`), said and in the game's record at once."""
        player = world.player
        assert player is not None
        game = world.game_name
        self.agenda.begin(self.game_id or game)  # a kind with no agenda of its own has none begun for this game
        self.agenda.push(*midgame.restart_package(player.area))
        self.restart_trip = game
        made = self.restart_trips[1] if self.restart_trips is not None and self.restart_trips[0] == game else 0
        self.restart_trips = (game, made + 1)
        # The watch tools read it (d2-loop-watch logwords.py TRIP_BEGUN; restart.py --when trip)
        LOG.info('Macro: loop: safe moment for the restart: %s, %s: Town Portal to town for it, back through it '
                 'after', display_name(player.area), self.game_id)  # fmt: skip
        midgame.keep(self)

    def note_portal(self, run: Run) -> None:
        """Where the character stands after a portal to town (`back_through_portal`)."""
        here = run.world().player
        self.portal_at = (here.x, here.y) if here is not None else None

    def prebuff_once(self, run: Run, game: str) -> None:
        """The prebuff, once a game."""
        if self.prebuffed != game:
            prebuff(run)
            self.prebuffed = game

    def _back_from_trip(self) -> None:
        """A trip's return: the room it made (`trip_gained`); the cube and the level's ground tried again (`room_tried`,
        `SHUNNED`, `forget`)."""
        if self.free is not None and self.trip_free is not None:
            self.trip_gained = self.free - self.trip_free
        LOG.info('Macro: loop: back from trip %d of this game for room: %s cells free, %s before it', self.trips,
                 self.free if self.free is not None else '?',
                 self.trip_free if self.trip_free is not None else '?')  # fmt: skip
        self.room_tried = None
        SHUNNED.clear()
        if self.forget is not None:
            self.forget()

    def observe(self, world: World) -> GameId | None:
        """The game `world` is in (`GameId`), logged on change; the lobby or an unread character keeps the last."""
        if not world.in_game or world.player is None:
            return self.game_id
        seen = GameId(world.game_name, world.player.unit_id)
        if seen != self.game_id:
            LOG.info('Macro: loop: game changed: %s, was %s', seen, self.game_id or 'none')
            self.game_id = seen
        return seen

    def count(self, world: World, leg: str) -> None:
        """Count `leg` where `world` is; `Abort` past REPEATS. The lobby's legs count by the game just left, so each
        game left has its own count."""
        where = world.game_name if world.in_game else f'the lobby after {world.game_name or "no game"}'
        if where != self.counted_in:
            # Only where the loop is now: game names come round again (2026-10-18 09:19)
            self.made.clear()
            self.counted_in = where
        self.made[where, leg] += 1
        bound = REPEATS.get(leg, REPEAT) * (1 + len(self.overflow_acts(where)) if leg in ACT_LEGS else 1)
        if self.merc_trips.game == where:
            bound += MERC_TRIP_LEGS.get(leg, 0) * self.merc_trips.past_cap()
        if self.made[where, leg] > bound:
            # Afresh after the Abort: the recovery makes the leg again (a count left over stopped each try, 2026-10-18)
            del self.made[where, leg]
            raise Abort(f'{leg} again and again in {where}: nothing came of it')

    def next_game(self, run: Run, world: World, key_names) -> None:
        """The NEXT_GAME leg: the next game made from the lobby, prebuffed in its town."""
        self.trip_due = self.swap_due = self.fresh = False
        self.gheed = None  # a parked Gheed's Fortune is fetched from the next game's town
        trace = create_next_game(run, world.game_name)
        self.lobby_fails = 0
        run.keys = character_keys(run, key_names)
        now = run.world()
        try:
            # In town: Consume speeds the town walks (the player, 2026-10-18)
            prebuff(run, fresh=trace)
            self.prebuffed = now.game_name
        except Hand:
            raise
        except Abort as stop:
            if now.player is None or now.player.area not in PREBUFF_LATER:
                raise
            # Consume cannot take the Encampment's start NPCs (routines.py TOWN_NPCS): again on Catacombs 2 (`DOWN`);
            # Harrogath's start is unplayed by the loop (2026-10-25): again on the Worldstone Keep 2 (`DOWN_THE_KEEP`)
            LOG.info('Macro: loop: the prebuff in %s failed (%s): again on %s', display_name(now.player.area), stop,
                     PREBUFF_LATER[now.player.area])  # fmt: skip

    def town(self, run: Run, visit: Callable[[Exit], object] | None, game: str, exit: Exit) -> None:
        """The TOWN leg: the town visit, ending by `exit`."""
        if visit is None:
            raise Abort('no town visit to make')
        self.visiting = game
        contract = visit(exit)
        self.visited = game
        self.repair = False
        if self.route_full:
            made = self.route_visits[1] if self.route_visits is not None and self.route_visits[0] == game else 0
            self.route_visits, self.route_full = (game, made + 1), False  # the next look judges afresh
        after = run.carried() if run.carried is not None else None
        if after is not None and self.own is not None:
            # What the visit left: a route's start visits again only for something picked up since (`route_full`)
            self.visit_units = (game, frozenset(i.unit_id for i in (*loot(after, self.own), *after.in_cube)))
        # A keeper no stash page takes: the loop stops in town, not a recovery (the player, 2026-10-18: "if stash is
        # full - we need to stop loop")
        full = tuple(getattr(contract, 'stash_full', None) or ())
        if full:
            raise Abort(f'the stash is full: {", ".join(full)}', cause='stash')

    def look_at_experience(self, run: Run, world: World) -> None:
        """A terror zone kind's leg look (macros/experience.py `Ledger.look`): the gain of a level once it is left."""
        if self.kind.key not in TZ_KINDS:
            if self.experience.first is not None:
                self.experience = Ledger()  # a TZ kind chosen again counts afresh
            return
        if world.in_game and world.player is not None:
            game_id = str(self.game_id or world.game_name)
            say_experience(self.experience.look(game_id, world.player.area, experience_now(run), time.monotonic()))

    def into_the_chamber(self, way_on: Callable[[], None]) -> None:
        """TO_THE_CHAMBER: the way on at the Throne's portal (running/legs.py `_way_on`: the level run while the portal
        is shut, the press once Baal is gone). A click that did not take (teleport.py `Untook`: Baal still on his
        throne, the hall not clear, the portal not open yet) is no stop: the leg is made again, the next one's level
        run fights the hall or waits, REPEATS bounding it. 2026-10-22 (the TZ's, tzloop.py SKIP_USE and FOUGHT_FIRST):
        "No click took Worldstone Chamber" left games with Baal alive; the player: "we need to kill all bosses, no
        exceptions to that".
        """
        from inventory_tracking.macros.teleport import Untook  # late: only this leg's

        try:
            way_on()
        except Untook as untook:
            LOG.info('Macro: loop: the Worldstone Chamber: %s: the leg is made again', untook)

    def leave(self, run: Run, game: str) -> None:
        """The LEAVE leg: Save and Exit, the game done and counted. A game's planned end in a level first makes the
        loot's field routine (loot/api.py `settle`, M4); a game given up does not."""
        if not self.abandon:
            settle_field(run, 'Save and Exit')
        self.done = game
        if self.kind.key in TZ_KINDS:
            say_experience(self.experience.game_over(self.games + 1, experience_now(run), time.monotonic()))
        leave_game(run)
        self.abandon = False
        self.games += 1

    def note_slain(self, game: str, dead: frozenset[str], clock: float) -> None:
        """The bosses read dead in `game` at the run clock `clock`, each kept at its first reading (`landing`)."""
        if self.slain_game != game:
            self.slain_game, self.slain = game, {}
        for name in dead:
            self.slain.setdefault(name, clock)

    def landing(self, clock: float) -> float:
        """Seconds before the drops of the last boss killed have landed, 0 when they have: DROPS_AFTER_KILL from the
        kill the service saw (KILLED_AT: the bosses and the tracked super uniques), else DROPS_LAND from the first leg
        that read the boss dead (`note_slain`)."""
        now = time.monotonic()
        waits = [DROPS_AFTER_KILL - (now - at) for at in KILLED_AT.values()]
        waits += [
            DROPS_LAND - (clock - at)
            for name, at in self.slain.items()
            if now - KILLED_AT.get(name, -math.inf) > KILL_FRESH
        ]
        return max([0.0, *waits])

    def settle(self, run: Run) -> None:
        """Wait for the drops of a boss just killed to land, before a level or the game is left (game 30, 21:55:06:
        the game was left 0.8 s after Diablo died, his drop still falling)."""
        wait = self.landing(run.clock())
        if wait > 0:
            LOG.info("Macro: loop: a boss's drops may still be landing: %.1fs more before the level is left", wait)
            watched_sleep(run, wait, "the boss drops' wait")  # a hostile hitting the character ends it (threat.py)

    def last_look(self, run: Run, hands: LegHands) -> str | None:
        """Before a game's end: what the loop would pick up still lying on the ground, None with nothing. In a level
        the drops of a boss just killed land first (`settle`), the ground is read again and what the loop takes is
        picked up (`take_one`, at most LAST_PICKS), and the guard reads it once more (`left`; unread, the game's
        sightings). In town the game's sightings alone. None with the game given up (`abandon`); `Dead` with the
        character dead (nothing more is pressed)."""
        player = run.world().player
        if player is not None and player.mode in DEAD:
            raise Dead('the character is dead')
        if self.abandon:
            return None
        if player is None or player.in_town:
            return hands.sighted(None)
        self.settle(run)
        for _ in range(LAST_PICKS):
            if not hands.take_one():
                break
        left = hands.left() if hands.left is not None else hands.sighted(None)
        if left == UNREAD:
            LOG.info("Macro: loop: the ground unread at the game's end: the game's sightings decide")
            left = hands.sighted(None)
        return left

    def swap_out(self, run: Run, world: World, key_names, item_stats: Stats | None) -> None:
        """The swap's first leg (SWAP_OUT): the player's Gheed's Fortune read, Town Portal home with it."""
        game = world.game_name if world.in_game else ''
        self.swap_due, self.swap = False, game
        now = run.reads.carried()
        ours = gheeds(now, self.own) if now is not None and self.own is not None else None
        if now is None or ours is None:
            raise Abort("a unique Grand Charm the pickup could not take, and no Gheed's Fortune of the player's")
        self.swap_units = frozenset(i.unit_id for i in (*now.items, *now.in_cube))
        self.swap_level = world.player.area if world.player is not None else None
        found = magic_find(item_stats, ours.unit_id)
        LOG.info("Macro: charms: another Gheed's Fortune on the ground, the player's carried at (%d, %d) (unit %d, "
                 'magic find %s%%): to town, it goes onto a shared stash page', ours.x, ours.y, ours.unit_id,
                 found if found is not None else '?')  # fmt: skip
        to_town(run, key_names)  # no pickup at the portal: the charm is refused
        self.note_portal(run)
        self.gheed = OUT

    def stash_gheeds(self, run: Run, item_stats: Stats | None, shown: Remembered | None) -> None:
        """GHEED_STASH: the player's Gheed's Fortune onto a shared page (charms.py `park`); the give-ups forgotten."""
        now = run.reads.carried()
        ours = gheeds(now, self.own) if now is not None and self.own is not None else None
        if ours is None:
            self.gheed = RETURN
            raise Abort("no Gheed's Fortune of the player's carried to put onto a shared page")
        try:
            self.parked = park(run, ours, item_stats, shown)
        except Abort:
            self.gheed = RETURN  # it stays carried: back to the level, whose valuable keeps the game
            raise
        self.gheed = PICK
        SHUNNED.clear()  # the refused charm is taken now
        if self.forget is not None:
            # and by the level run, which gave it up (rca/2026-10-18/loop-robustness-findings.md §2.3)
            self.forget()
        LOG.info("Macro: charms: back through the portal for the new Gheed's Fortune")

    def swap_back(self, run: Run, world: World, key_names) -> None:
        """SWAP_BACK: the new one picked up or not, Town Portal home for the choice."""
        parked = self.parked
        assert parked is not None
        now = run.reads.carried()
        found = candidates(now, parked, self.swap_units) if now is not None else []
        if found:
            LOG.info("Macro: charms: the new Gheed's Fortune picked up (unit %d at (%d, %d)%s): to town to compare",
                     found[0].unit_id, found[0].x, found[0].y,
                     ', unidentified' if not found[0].identified else '')  # fmt: skip
        else:
            LOG.info("Macro: charms: no new Gheed's Fortune picked up: to town for the player's, on shared page %s",
                     parked.page)  # fmt: skip
        self.gheed = CHOOSE
        if world.player is not None and not world.player.in_town:
            to_town(run, key_names)
            self.note_portal(run)

    def choose_gheeds(self, run: Run, hands: LegHands, item_stats: Stats | None, shown: Remembered | None) -> None:
        """GHEED_CHOOSE: the new one identified at Cain, the better roll kept at the player's cell (charms.py
        `choose`); `parked` cleared."""
        identify, bring = hands.identify, hands.bring
        parked = self.parked
        assert parked is not None
        now = run.reads.carried()
        found = candidates(now, parked, self.swap_units) if now is not None else []
        unread = tuple(i for i in found if not i.identified)
        if unread and identify is not None:
            LOG.info('Macro: charms: the new unique Grand Charm identified at Cain')
            identify(unread)
            now = run.carried() if run.carried is not None else now
            found = candidates(now, parked, self.swap_units) if now is not None else []
        rivals = [i for i in found if i.identified and i.unique == GHEEDS_FORTUNE]
        for other in (i for i in found if i not in rivals):
            LOG.info(
                "Macro: charms: the new unique Grand Charm (unit %d) is %s: no Gheed's Fortune to compare",
                other.unit_id,
                f'unique row {other.unique}' if other.identified else 'still unidentified',
            )
        new = max(rivals, key=lambda i: magic_find(item_stats, i.unit_id) or 0) if rivals else None
        if new is not None and now is not None and new.unit_id in now.cube_items and bring is not None:
            bring([new])  # Ctrl + click to the stash works from the inventory only
            after = run.reads.carried()
            new = next((i for i in after.items if i.unit_id == new.unit_id), None) if after is not None else None
        # Anything else picked up in the swap (runner.py `_gheeds_swap`) is in the player's cell: onto a shared page
        others = newcomers(now, parked, self.swap_units) if now is not None else []
        kept = choose(run, parked, new, item_stats, shown, others=others)
        if self.own is not None:
            self.own = (self.own - {parked.cell}) | {(kept.txt, kept.x, kept.y)}
        self.parked = None

    def moment(self, world: World, hands: LegHands, progress: Progress | None = None) -> midgame.Moment:
        """What a safe point for a restart is judged by now (macros/midgame.py `refusal`); the ground is read only in
        a field level, for SAFE and TRIP; TRIP's boss alive on the level by the route `progress` fights there."""
        from inventory_tracking.macros.hunting.base import hostiles  # late: the hunt's modules import this one

        player = world.player
        if not world.in_game or player is None:
            return midgame.Moment(in_game=world.in_game)
        game, in_town = world.game_name, player.in_town
        here = (player.x, player.y)
        field = not in_town and self.restart_when in (midgame.SAFE, midgame.TRIP)
        trip = field and self.restart_when == midgame.TRIP
        due = (
            ('room in the cube', self.make_room),
            ('an item dropped for room', self.drop_room),
            ('a fight back', self.beset_due == game or self.fetch_back == game),
            ('the game given up', self.abandon),
            ('a visit cut short', self.visiting == game and self.visited != game),
            ('a trip for room', self.trip_due),
        )
        return midgame.Moment(
            in_game=True,
            in_town=in_town,
            dead=player.mode in DEAD,
            panels=tuple(world.open_panels),
            hostile=midgame.nearest(here, ((m.x, m.y) for m in hostiles(world))) if field else None,
            valuable=(hands.left() if hands.left is not None else None) if field else None,
            remembered=hands.sighted(player.area) if field else None,
            stack=tuple(goal.label for goal in reversed(self.agenda.stack) if goal.kind != RESUME),
            swap=self.swap_due or self.gheed is not None or self.agenda.holds(SWAP_GOALS),
            pending=tuple(name for name, now in due if now),
            arena=boss_alive(progress, player.area) if trip else '',
            herald=next(
                (goal.label for goal in self.agenda.kills.values() if goal.tier == HERALD and goal.area == player.area),
                None,
            )
            if trip
            else None,
            trips=self.kind.agenda or self.kind.packaged,
            tripped=self.restart_trips[1] if self.restart_trips is not None and self.restart_trips[0] == game else 0,
        )

    def hold_at_safe_point(self, run: Run, world: World, hands: LegHands, progress: Progress | None = None) -> None:
        """A restart waits for a safe point (`restart_when`, macros/midgame.py): at one, between two legs, the loop
        stands until the service's restart cancels the run (`Cancelled`), PARK_SECONDS at most (then the hold is
        dropped and the leg made); elsewhere the refusal is said when it changes and the leg is made. TRIP at a field
        level's safe moment: the portal trip's package pushed (`begin_restart_trip`), this leg its Town Portal, the
        stand at the next leg's start in town."""
        when = self.restart_when
        assert when is not None
        why = midgame.refusal(when, self.moment(world, hands, progress), midgame.sight())
        if why is not None:
            if why != self.unsafe_said:
                self.unsafe_said = why
                LOG.info('Macro: loop: no safe point for the restart yet: %s', why)
            return
        player = world.player
        if when == midgame.TRIP and world.in_game and player is not None and not player.in_town:
            self.unsafe_said = None
            self.begin_restart_trip(world)
            return
        where = display_name(player.area) if world.in_game and player is not None else 'the lobby'
        # The watch tools read it (d2-loop-watch logwords.py SAFE_POINT; restart.py --when)
        LOG.info('Macro: loop: safe point: %s, %s: the loop stands for the restart', where,
                 self.game_id if world.in_game else 'between games')  # fmt: skip
        self.safe_point = where
        try:
            deadline = time.monotonic() + midgame.PARK_SECONDS
            while time.monotonic() < deadline:
                if run.cancelled.wait(midgame.PARK_SLICE):
                    raise Cancelled
        finally:
            self.safe_point = None
        self.restart_when = self.unsafe_said = None
        LOG.info('Macro: loop: no restart came at the safe point within %.0f s: the hold is dropped, the loop goes on',
                 midgame.PARK_SECONDS)  # fmt: skip

    def leg(
        self,
        run: Run,
        key_names,
        progress: Progress | None,
        hands: LegHands,
        *,
        item_stats: Stats | None = None,
        shown: Remembered | None = None,
    ) -> str:
        """Make the next leg with the runner's `hands`; returns its name. `item_stats(unit)`: game/memory.py
        `GameMemory.item_stats`; `shown`: the shared page the stash showed last (visit.py `Remembered`)."""
        level_run, pick_up, visit, down, fight = hands.level_run, hands.take_one, hands.visit, hands.way_on, hands.fight
        left = hands.left
        world = run.world()
        if (cooling := self.cooling - time.monotonic()) > 0:
            # The recoveries' pause is stood only where nothing attacks (lobby, town); elsewhere the game is left first
            # (the player, 2026-10-19: "we stood still while under attack and almost died")
            if not world.in_game or (world.player is not None and world.player.in_town):
                if cooling > RECOVERY_PAUSE:
                    LOG.info('Macro: loop: waiting %.0f s before the next leg (the next terror zone)', cooling)
                # In slices: the next zone's wait is up to 30 min, and a run cancelled (the player's KP_6, a restart)
                # ends it at once
                while (cooling := self.cooling - time.monotonic()) > 0:
                    if run.cancelled.is_set():
                        raise Cancelled
                    run.pace.sleep(min(cooling, COOLING_SLICE))
                world = run.world()
            else:
                area = world.player.area if world.player is not None else 'an unread level'
                LOG.info('Macro: loop: the pause after recoveries (%.0f s) is not stood in level %s: the game is left '
                         'first', cooling, area)  # fmt: skip
        if world.in_game and world.player is None:
            # A game still loading: waited for, not a leg's stop
            world = run.seen(lambda w: w.player is not None or not w.in_game, LOADING_SECONDS) or run.world()
        self.observe(world)
        # The game's record (macros/midgame.py RECORD): taken up at the first leg in it, before the agenda's `begin`,
        # which would start the game afresh (a second shard for an act terrorized); then kept as each leg starts
        self.facts_from = progress
        midgame.take_up(self, world, progress)
        midgame.keep(self, progress)
        if self.restart_when is not None:
            self.hold_at_safe_point(run, world, hands, progress)
        if not world.in_game:
            self.abandon = False  # left
        elif progress is not None and progress.dead is not None:
            self.note_slain(world.game_name, progress.dead(), run.clock())  # `landing`'s clock for a kill unseen
        if not self.placed and not self.chosen and world.player is not None:
            # The kind by where the character stands; the shared Fortress keeps the chosen one
            self.placed = True
            found = kind_of(world.player.area)
            if found is not None and found != self.kind:
                LOG.info('Macro: loop: %s, by where the character is', found.name)
                self.kind = found
        self.look_at_experience(run, world)
        pack = run.carried() if world.in_game and run.carried is not None else None
        if world.in_game and world.player is not None:
            source = portal_source(run)
            if source != self.portal:
                # Logged on change: confirms the Sling is read and bound (macros/sling-plan.md)
                worn = run.reads.worn_skills()
                LOG.info('Macro: loop: Town Portal from %s: skill %d %s; worn skills %s', source.name, source.skill,
                         slot_note(world, source), sorted(worn) if worn is not None else 'unread')  # fmt: skip
                self.portal = source
        self.short = short(pack, self.portal or FROM_TOME)
        if pack is not None and world.player is not None and self.own is None:
            mine_now = self.mine or self._stored(world.player.name)
            LOG.info("Macro: loop: carried at its first look: %s; the cube: %s", '; '.join(
                f"{_named(i)} ({i.x},{i.y}){f' unique row {i.unique}' if i.quality == 7 else ''}"
                f"{' the loop' if (i.txt, i.x, i.y) in mine_now else ''}"
                for i in pack.items
            ), '; '.join(_named(i) for i in pack.in_cube))  # fmt: skip
        if pack is not None and world.player is not None:
            self.told(pack, world.player.name, item_stats)  # the player's first, so the first look counts the room too
        items = loot(pack, self.own) if pack and self.own else []
        in_town = world.player is not None and world.player.area == PANDEMONIUM_FORTRESS
        if self.parked is not None and pack is not None:
            self.fresh = bool(candidates(pack, self.parked, self.swap_units))
        if pack is not None and self.own is not None:  # unread in the lobby: the last look's stands
            carried = [*items, *pack.in_cube]
            # The trade waits until the inventory and the cube are both full (loot/storage.py `room`)
            space = room(Storage(pack, self.own))
            cube, in_inventory, in_cube = space.rows, space.inventory, space.cube
            self.free = space.free
            if in_town and space.low:
                LOG.info('Macro: loop: room low: %d cells free (inventory %d, cube %d, loop items %d in the inventory '
                         'and %d in the cube; cube rows %s)', self.free, in_inventory, in_cube, len(items),
                         len(pack.in_cube), '/'.join(cube))  # fmt: skip
            # A visit cannot take away a full gem stack's gems (kept, neither stashed nor sold)
            full = self.stash.full()
            stuck = full - sold_full(full)
            # ...but three of a kind are a transmute (cube.py `transmute`): a session's work
            cubable = Counter(i.txt for i in carried if i.txt in stuck and perfect_of(i.txt) not in (None, *full))
            self.carrying = (
                any(i.txt not in stuck for i in carried)
                or bool(surplus(carried, stuck))
                or any(count >= GEMS_A_KIND for count in cubable.values())
            )
            self.route_full = self.route_starts_full(world, cube, items, carried)
            self.gainable = new_cells(carried, self.visit_units, world.game_name)
            visiting = world.in_game and self.visiting == world.game_name and self.visited != world.game_name
            if in_town and cells_low(in_inventory) and not space.low and in_cube >= 3 and items and not visiting:
                # The loop's items into the cube for pickup room, between visits only (runner.py `make_room`)
                self.make_room = True
        self.northern_ready = None
        if self.kind.key == BAAL.key and world.in_game and world.player is not None and world.player.in_town:
            from inventory_tracking.macros import actloop  # late: as `loop_kinds`

            self.northern_ready = actloop.northern_ready(run, world.player.area)
        staff = run.teleport() if world.in_game and run.teleport is not None else None
        # In a visit any missing charge is topped up (town.py `tops_up`), decided again at Halbu's (macros/visit.py)
        in_session = world.in_game and self.visiting == world.game_name
        topped = tops_up(staff, in_session, self.visited == world.game_name)
        # A worn item low on durability is a repair of its own
        wear = run.wear() if world.in_game and run.wear is not None else None
        self.wear = worn_text(wear)
        coins = gold(run) if (staff is not None and (wants(staff) or topped)) or worn_out(wear) else None
        self.repair = due(staff, wear, coins, top_up=topped, waited=self.repair_waited())
        if not world.in_game and self.pending is not None:
            # A kind asked while on takes in the lobby, before the kind picks its leg: the terror zone kinds make the
            # next game by their agenda, never through the NEXT_GAME branch below (game 31, 21:55 on 2026-10-19)
            self.kind, self.pending, self.chosen = self.pending, None, True
            run.say(f'Loop run: {self.kind.name}')
        goal = None
        seen = hands.life() if hands.life is not None else None
        if self.spinning(world, time.monotonic(), seen) and hands.fight_back is not None:
            self.fight_back_due(world.game_name)  # legs ending at once in a fight (LEG_SPIN): the fight first
        if (beset := self.after_beset(world)) is not None:
            leg = beset  # before the kind's own legs: the attacker first, then its ground
        elif self.kind.agenda or self.kind.packaged:
            from inventory_tracking.macros import tzloop  # late: tzloop imports this module

            # Lower Kurast: a trip for room under way (the room package) before its own legs
            goal = tzloop.choose(world, progress, self, hands) if self.kind.agenda else tzloop.packaged(world, self)
            leg = tzloop.leg_of(goal) if goal is not None else next_leg(world, progress, self)
        else:
            leg = next_leg(world, progress, self)
        game = world.game_name if world.in_game else ''
        self.count(world, leg)
        run.say(f'Loop: game {self.games + 1}, {leg}')
        self.current = leg
        if leg != NEXT_GAME:
            run.keys = character_keys(run, key_names)  # Swap Weapons among them (`arrived`)
        if goal is not None:
            from inventory_tracking.macros import tzloop

            tzloop.perform(self, run, key_names, progress, goal, hands, item_stats=item_stats, shown=shown)
            return leg
        if leg == NEXT_GAME:
            if self.pending is not None:
                self.kind, self.pending, self.chosen = self.pending, None, True
                run.say(f'Loop run: {self.kind.name}')  # the request's kind takes (runner.py `choose_kind`)
            self.next_game(run, world, key_names)
        elif leg == FIGHT_BACK:
            if hands.fight_back is None:
                raise Abort('no level run to fight back with')
            self.beset_due, self.fetch_back, self.fought_back = None, game, (game, time.monotonic())
            hands.fight_back()  # posts the run and returns; its end is PICK_BACK's
        elif leg == PICK_BACK:
            self.fought_back = (game, time.monotonic())  # the fight is over: BESET_AGAIN_SECONDS counts from here
            if not pick_up():
                self.fetch_back = None  # nothing left: the kind's legs go on
        elif leg == TOWN:
            self.town(run, visit, game, self.exit_of(game))
        if leg in (TO_THE_CHESTS, TO_THE_CATACOMBS, TO_THE_KEEP):
            # The carried gold, once a game (the player, 2026-10-17: "just use gold in the inventory")
            coins = gold(run)
            LOG.info('Macro: loop: gold carried %s, the most worn item %s', coins, self.wear)
            if not (run.own_teleport is not None and run.own_teleport()):
                # Own Teleport (Enigma) is in every move whatever the gold (runner.py LOOPED_TELEPORT)
                self.teleports = teleports(coins, gold_cap(run), self.teleports)
            # The prebuff waits for the first level where the town's start may refuse it (`next_game`)
            later = (ROGUE_ENCAMPMENT, HARROGATH) if leg == TO_THE_KEEP else (ROGUE_ENCAMPMENT,)
            if world.player is None or world.player.area not in later:
                self.prebuff_once(run, game)
            travel(run, self.kind.start, self.marks)
        elif leg == CHESTS:
            level_run()
        elif leg in (DOWN, DOWN_THE_KEEP):
            if down is None:
                raise Abort('no level run to the stairs')
            self.prebuff_once(run, game)  # not cast in the Encampment or Harrogath (`next_game`)
            down()
        elif leg in (FIGHT_ANDARIEL, FIGHT_THRONE, FIGHT_BAAL):
            if fight is None:
                raise Abort('no level run to fight with')
            fight()  # posts the run and returns; its end is PICK_UP's
        elif leg == TO_THE_CHAMBER:
            if down is None:
                raise Abort('no way on to press')
            self.into_the_chamber(down)
        elif leg == PICK_UP:
            lair = self.kind.lair
            on_lair = lair is None or (world.player is not None and world.player.area == lair)
            boss = self.kind.boss if on_lair else None
            if boss is not None and (self.fought is None or self.fought[0] != game):
                # Her fight's run has just ended (`fight` only posts it): the clock starts here
                self.fought = (game, run.clock())
            if not pick_up() and progress is not None and world.player is not None:
                killed = time.monotonic() - KILLED_AT.get(boss, -math.inf) if boss is not None else math.inf
                if killed < KILL_FRESH:
                    landing = DROPS_AFTER_KILL - killed
                elif self.fought and self.fought[0] == game:
                    landing = DROPS_LAND - (run.clock() - self.fought[1])
                else:
                    landing = 0.0
                if landing > 0:
                    LOG.info("Macro: loop: %s's drops may still be landing: %.1fs more, then the ground again", boss,
                             landing)  # fmt: skip
                    watched_sleep(run, landing, f"{boss}'s drops' wait")  # a hostile hitting the character ends it
                else:
                    progress.looted(world.player.area)
        elif leg == PORTAL:
            if not pick_up():
                self.done = game
                to_town(run, key_names, pick_up)
        elif leg == TRIP:
            self.begin_trip(game)
            to_town(run, key_names)  # no pickup at the portal: no room
            self.note_portal(run)
        elif leg == SWAP_OUT:
            self.swap_out(run, world, key_names, item_stats)
        elif leg == GHEED_STASH:
            self.stash_gheeds(run, item_stats, shown)
        elif leg == SWAP_BACK:
            self.swap_back(run, world, key_names)
        elif leg == GHEED_CHOOSE:
            self.choose_gheeds(run, hands, item_stats, shown)
            level = self.swap_level
            seen = left() if left is not None else None
            done = progress is not None and level is not None and progress.step(level) is None and seen is None
            if self.swap == game and not done:
                self.gheed = RETURN
                LOG.info('Macro: charms: back through the portal for the rest of the level%s',
                         f' ({seen})' if seen else '')  # fmt: skip
            else:
                self.gheed = None
                if self.swap == game:
                    self.done = game  # Save and Exit from here
                    LOG.info("Macro: charms: the level's loot is done: the game is left from town")
        elif leg == TO_THE_ENCAMPMENT:
            travel(run, ROGUE_ENCAMPMENT, self.marks)
        elif leg == TO_HARROGATH:
            travel(run, HARROGATH, self.marks)
        elif leg == BAAL_SHARD:
            from inventory_tracking.macros import actloop  # late: as `loop_kinds`

            self.northern = game  # once a game, whatever comes of it
            try:
                actloop.baal_shard(self, run, hands.terrorized, hands.inventory_key())
            except Hand, Cancelled:
                self.northern = None  # the player's hand or a cut run: tried again at the next leg
                raise
        elif leg == THROUGH_PORTAL:
            self.back_through_portal(run, game)
            if self.gheed in (PICK, RETURN) and progress is not None and self.swap_level is not None:
                # Unmark looted: the pickup that shunned the refused charm marked it so
                progress.facts = replace(progress.facts, looted=progress.facts.looted - {self.swap_level})
            if self.gheed == RETURN:
                self.gheed = None
        elif leg == TO_THE_FORTRESS:
            self.fortressed = game
            if self.kind.fortress_ends_game:
                self.done = game
            travel(run, PANDEMONIUM_FORTRESS, self.marks)
        elif leg == LEAVE:
            if world.player is not None and not world.player.in_town and (left := self.last_look(run, hands)):
                # Never a game left with a valuable on the ground (the player, 2026-10-17), as tzloop.py LEAVE_GAME's
                raise Abort(f'the game ends, but {left} lies on the ground', cause='room')
            self.leave(run, game)
        return leg


def boss_alive(progress: Progress | None, area: int) -> str:
    """The boss the route fights on level `area` while not read dead (midgame.TRIP's arena); '' with none, or with the
    route or its kills unread."""
    from inventory_tracking.macros.tzloop import boss_of  # late: tzloop imports this module

    if progress is None:
        return ''
    boss = boss_of(progress, area)
    if not boss:
        return ''
    dead = progress.dead() if progress.dead is not None else frozenset()
    return '' if boss in dead else boss


def experience_now(run: Run) -> Reading | None:
    """The character's experience and level (macros/experience.py), None unread: never a leg's stop."""
    try:
        loot = run.reads.loot()
    except OSError, ValueError:
        return None
    return reading(dict(loot.stats)) if loot is not None and loot.stats else None


def say_experience(lines: list[str]) -> None:
    for line in lines:
        LOG.info('Macro: %s', line)


# Shares of the gold cap: Teleport from the first, Blade Warp alone under the second (the player, 2026-10-17: "if we
# make enough gold - we can use teleport staff more often"); 15 % still pays a full repair (history/loop.md)
TELEPORT_ON, TELEPORT_OFF = 0.35, 0.15
GOLD_CAP = 990_000  # the cap at level 99, for a level unread


def teleports(coins: int | None, cap: int | None, now: bool | None) -> bool | None:
    """Whether the loop's moves take the staff's Teleport this game (travel.py LOOPED_TELEPORT): on from TELEPORT_ON of
    the gold cap, off under TELEPORT_OFF, unchanged with the gold unread."""
    if coins is None:
        return now
    most = cap or GOLD_CAP
    if now is None:
        # First look since a start: on over TELEPORT_OFF (restarts began it off: slower stays, 2026-10-17)
        now = coins >= TELEPORT_OFF * most
        LOG.info(
            'Macro: loop: %d gold carried of %d: %s',
            coins,
            most,
            'Teleport in the moves' if now else 'Blade Warp alone',
        )
        return now
    if coins >= TELEPORT_ON * most:
        if not now:
            LOG.info('Macro: loop: %d gold carried of %d: Teleport in the moves', coins, most)
        return True
    if coins < TELEPORT_OFF * most:
        if now:
            LOG.info('Macro: loop: %d gold carried of %d: Blade Warp alone', coins, most)
        return False
    return now


def new_cells(carried: Sequence[Carried], left: tuple[str, frozenset[int]] | None, game: str | None) -> int:
    """The cells of `carried` (the loop's, inventory and cube) not among the units `left` by the game's last visit
    (`Loop.visit_units`); all of them with no visit in `game`."""
    units = left[1] if left is not None and left[0] == game else frozenset()
    return sum(item.size[0] * item.size[1] for item in carried if item.unit_id not in units)


def next_leg(world: World, progress: Progress | None, loop: Loop) -> str:
    """The leg the loop makes next from where the character is; `Abort` where it has none."""
    if not world.in_game:
        return NEXT_GAME
    player = world.player
    if player is None:
        raise Abort('not in a game')
    if player.mode in DEAD:
        raise Dead('the character is dead')
    swapping = gheeds_leg(world, loop)
    if swapping is not None:
        return swapping
    if loop.abandon:
        return LEAVE
    if player.area == PANDEMONIUM_FORTRESS:
        game = world.game_name
        if loop.visit_due(game):
            return TOWN
        if loop.done == game:
            return LEAVE
    return LEGS.get(loop.kind.key, lk_leg)(world, progress, loop)


def lk_leg(world: World, progress: Progress | None, loop: Loop) -> str:
    """Lower Kurast's legs (`next_leg`): the waypoint from the Fortress, the chests, what is left, the portal home."""
    player = world.player
    assert player is not None
    if player.area == PANDEMONIUM_FORTRESS:
        return TO_THE_CHESTS
    if player.area == LOWER_KURAST:
        step = progress.step(LOWER_KURAST) if progress is not None else None
        if step is not None and step.stage.kind == USE:
            return CHESTS
        if step is not None and step.stage.kind == LOOT:
            return PICK_UP
        return PORTAL
    if player.area == KURAST_DOCKS:
        return TO_THE_FORTRESS
    if player.in_town:
        # A game begins where the character was last saved: from any other town its waypoint (Lut Gholein after a
        # terror zone played by hand left game after game, 2026-10-19 18:54; the player: "let's add handling for
        # every town")
        return TO_THE_CHESTS
    raise Abort(f'the loop has nothing to do in {display_name(player.area)}')


def gheeds_leg(world: World, loop: Loop) -> str | None:
    """The Gheed's swap's leg where the character is (`Loop.gheed` the stage), None otherwise. A parked Gheed's Fortune
    is never left at a game's end: an abandoned game tries the way to the choice REPEAT times, then the next game's
    town fetches it."""
    player = world.player
    assert player is not None
    game, area, parked, stage = world.game_name, player.area, loop.parked, loop.gheed
    home, levels = swap_ground(loop.kind)
    to_home = HOME_LEGS[home]
    if loop.abandon:
        if parked is None:
            return None
        legs = {PANDEMONIUM_FORTRESS: GHEED_CHOOSE, home: TO_THE_FORTRESS}
        leg = legs.get(area, SWAP_BACK if area in levels else None)
        return leg if leg is not None and loop.made[game, leg] < REPEAT else None
    if area == PANDEMONIUM_FORTRESS:
        if parked is not None:
            return to_home if stage == PICK else GHEED_CHOOSE
        if stage == OUT:
            return GHEED_STASH
        return to_home if stage == RETURN else None
    if area == home:
        if parked is not None:
            return THROUGH_PORTAL if stage == PICK else TO_THE_FORTRESS
        if stage == OUT:
            return TO_THE_FORTRESS
        return THROUGH_PORTAL if stage == RETURN else None
    if area in levels:
        if parked is not None and (stage != PICK or loop.fresh):
            return SWAP_BACK
        if parked is None and loop.swap_due and loop.swap != game and loop.kind.swaps_gheeds:
            return SWAP_OUT
    return None


def swap_ground(kind: Kind) -> tuple[int, frozenset[int]]:
    """The Gheed's swap's town and levels for `kind` (`gheeds_leg`): a boss kind's own (its home among HOME_LEGS:
    Andariel's Encampment, Baal's Harrogath), else Andariel's as before (the agenda kinds' swap is their package's)."""
    if kind.agenda or kind.home not in HOME_LEGS:
        return ROGUE_ENCAMPMENT, ANDARIEL.levels
    return kind.home, kind.levels


def boss_town_leg(world: World, loop: Loop, to_start: str) -> str | None:
    """A boss kind's legs in the towns (`andariel_leg`, `baal_leg`): from the Fortress `to_start` (its waypoint), or
    home on a trip; at home Save and Exit at a game's end, a trip's Fortress and the way back through the portal, the
    Fortress for a session due (the room low with something a session takes, keys or scrolls short, a repair), else
    `to_start`; any other town `to_start` (as `lk_leg`); out of town a trip for room due (several a game:
    `Loop.may_trip`), else None for the kind's levels."""
    player = world.player
    assert player is not None
    game = world.game_name
    home = loop.kind.home
    if player.area == PANDEMONIUM_FORTRESS:
        return HOME_LEGS[home] if loop.tripping(game) else to_start
    if player.area == home:
        if loop.done == game:
            return LEAVE
        if loop.tripping(game):
            return TO_THE_FORTRESS if loop.fortressed != game else THROUGH_PORTAL
        if (loop.room_low and loop.carrying) or loop.short or loop.repair:
            return TO_THE_FORTRESS
        return to_start
    if player.in_town:
        return to_start
    if (
        loop.trip_due
        and not loop.tripping(game)
        and loop.trips_in(game) < TRIPS_A_GAME
        and player.area in loop.kind.levels
    ):
        return TRIP
    return None


def andariel_leg(world: World, progress: Progress | None, loop: Loop) -> str:
    """Andariel's legs (`next_leg`): the Encampment's waypoint (the Fortress first for its errands), down Levels 2 and
    3, on Level 4 her fight, the loot, Save and Exit."""
    player = world.player
    assert player is not None
    if (leg := boss_town_leg(world, loop, TO_THE_CATACOMBS)) is not None:
        return leg
    if player.area in (CATACOMBS_2, CATACOMBS_3):
        return DOWN
    if player.area == CATACOMBS_4:
        step = progress.step(CATACOMBS_4) if progress is not None else None
        if step is not None and step.stage.kind == FIGHT:
            return FIGHT_ANDARIEL
        if step is not None and step.stage.kind == LOOT:
            return PICK_UP
        return SWAP_BACK if loop.parked is not None else LEAVE
    raise Abort(f'the Andariel loop has nothing to do in {display_name(player.area)}')


def baal_leg(world: World, progress: Progress | None, loop: Loop) -> str:
    """Baal's legs (`next_leg`; the player, 2026-10-25: "build a baal runner, very similar to andariel runner"):
    Harrogath's waypoint (the Fortress first for its errands), down the Worldstone Keep 2 and 3, on the Throne its
    route's stages (the stand, the waves to Lister: FIGHT_THRONE; Lister's loot; the portal once Baal left:
    TO_THE_CHAMBER), in the Chamber his fight, the loot (his drops waited for: `Kind.lair`), Save and Exit."""
    player = world.player
    assert player is not None
    if (leg := boss_town_leg(world, loop, TO_THE_KEEP)) is not None:
        if leg == TO_THE_KEEP and loop.northern_ready is not None and loop.northern != world.game_name:
            return BAAL_SHARD  # act 5 terrorized first (actloop.py NORTHERN_FOR_BAAL); nothing spare: as before
        return leg
    area = player.area
    if area in (WORLDSTONE_KEEP_2, WORLDSTONE_KEEP_3):
        return DOWN_THE_KEEP
    step = progress.step(area) if progress is not None and area in (THRONE, CHAMBER) else None
    stage = step.stage.kind if step is not None else None
    if area == THRONE:
        if stage in (STAND, FIGHT):
            return FIGHT_THRONE  # the waves before the Chamber: its portal opens only once Baal walked into it
        if stage == LOOT:
            return PICK_UP
        return TO_THE_CHAMBER  # its USE stage (or unread): the way on, a level run while the portal is shut
    if area == CHAMBER:
        if stage == FIGHT:
            return FIGHT_BAAL
        if stage == LOOT:
            return PICK_UP
        return SWAP_BACK if loop.parked is not None else LEAVE
    raise Abort(f'the Baal loop has nothing to do in {display_name(area)}')


# Each kind's legs outside the town visit (`next_leg`); the TZ kinds' are the agenda's
LEGS = {LK.key: lk_leg, ANDARIEL.key: andariel_leg, BAAL.key: baal_leg}


def _named(item: Carried) -> str:
    from inventory_tracking.items.metadata import metadata  # late: only the log's

    base = metadata()['bases'].get(str(item.txt))
    return base['name'] if base is not None else f'item {item.txt}'
