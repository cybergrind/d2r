"""The KP_6 loop: plays games until it is toggled off (routes/lower-kurast-loop-plan.md phase 4), of one `Kind`: the
Lower Kurast chests, or Andariel (routes/andariel-loop-plan.md: the player, 2026-10-18, "I want to build andariel loop
that will be similar to lower kurast loop, we're going to use the same KP_6 run start/stop it").

The loop is a state machine read from where the character is, so it goes on from any point (`next_leg`): one leg a
run of the runner's (macros/runner.py LOOP), the next chosen when it is over. The legs are the routines built for
them: the next game and its prebuff (routines.py), the waypoint (waypoint.py), the KP_1 level run for the chests
(pursuit.py, run as attack mode: the runner starts it and comes back here when it ends), the pickup of what is left,
the portal (portal.py), Save and Exit. The player, 2026-10-16: games end in act 4 (portal → Kurast Docks → waypoint
→ Pandemonium Fortress → Save and Exit), where the next game starts by its waypoint.

A leg that `Abort`s (a place the loop has no leg for, a leg made again and again in one game with nothing coming of
it: `REPEATS`) or a game that lasts over GAME_SECONDS is recovered from by leaving the game (`recover`, `abandon`): the
player, 2026-10-17: "we should try to not stuck in some weird situation without being able to fix it from agent". It
stops by itself, saying why (`Macro: loop stopped: …`), only with the character dead (`Dead`); past RECOVERIES
recoveries within RECOVERY_SECONDS it goes on after RECOVERY_PAUSE, saying so for the watch to fix (the player,
2026-10-18: "how to setup the loop in the way that would fully prevent us from stopping").
"""

import json
import math
import time
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from inventory_tracking.common import LOG
from inventory_tracking.items.grid import Grid
from inventory_tracking.levels.presets import display_name
from inventory_tracking.macros.actuator import Abort, Hand
from inventory_tracking.macros.agenda import Agenda
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
    overflow,
    own_of,
    perfect_of,
    roomed,
)
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.junk import MAGIC
from inventory_tracking.macros.pickup import SHUNNED
from inventory_tracking.macros.portal import FROM_TOME, PortalSource, portal_source, slot_note, through_portal, to_town
from inventory_tracking.macros.repair import RETRY_GAMES, due, gold, wants, worn_out, worn_text
from inventory_tracking.macros.routines import DEAD, Dead, character_keys, create_next_game, leave_game, prebuff
from inventory_tracking.macros.shop import KEYS_ONE_STACK, KEYS_WANTED, gold_cap, short
from inventory_tracking.macros.stash import INVENTORY_CELLS, RESOURCES
from inventory_tracking.macros.town import GEMS_A_KIND, TRADE_ROOM, Exit, sold_full, surplus, tops_up
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
from inventory_tracking.macros.world import TOWN_IDS, Carried, Pack, World
from inventory_tracking.routes.model import FIGHT, LOOT, USE
from inventory_tracking.routes.progress import Progress
from inventory_tracking.terror.bosses import KILLED_AT


if TYPE_CHECKING:
    from inventory_tracking.macros.tzloop import TzHands


__all__ = [
    'ANDARIEL',
    'KINDS',
    'LK',
    'LOWER_KURAST',
    'TOWN',
    'TRADE_ROOM',
    'TRIPS_A_GAME',
    'Dead',
    'GameId',
    'Kind',
    'Loop',
    'kind_of',
    'next_leg',
]

KURAST_DOCKS, LOWER_KURAST, PANDEMONIUM_FORTRESS = 75, 79, 103
ROGUE_ENCAMPMENT, CATACOMBS_2, CATACOMBS_3, CATACOMBS_4 = 1, 35, 36, 37  # levels.txt


@dataclass(frozen=True)
class Kind:
    """A kind of the loop's run: `start` the level its waypoint leads to, `levels` the run's levels (its sightings),
    `home` the town of its act (where its new games start, or its portal leads), `keys` the keys a visit to Jamella buys
    up to (macros/shop.py: two stacks for the chests, one where none is opened)."""

    key: str
    name: str
    start: int
    levels: frozenset[int]
    home: int
    keys: int = KEYS_ONE_STACK
    # The measure the kind is tuned by (the player, 2026-10-19 ~02:12: "every loop has it's own metric, that it must
    # optimize: boss kills/elites kill/opened chest. the only thing that has more priority - proper interactions with
    # drops"), named for the log and the watch tools
    metric: str = ''
    # Seconds a game of the kind may last before the watchdog leaves it (`overdue`); None: GAME_SECONDS
    game_seconds: float | None = None
    # Where the kinds differ, as the code asks it (never the kind itself; cleanup phase 3, 2026-10-19)
    agenda: bool = False  # its legs are the agenda's goals (macros/tzloop.py), not `next_leg`'s
    trips: bool = False  # a valuable with no room is a trip to town and back through the portal (macros/stops.py)
    swaps_gheeds: bool = False  # the Gheed's swap (macros/charms.py)
    boss: str | None = None  # whose drops may still be landing after the kill at the PICK_UP leg (`KILLED_AT`)
    badge: bool = True  # the HUD's badge names the kind (runner.py `run_badge`)
    fortress_ends_game: bool = False  # its level left for the Fortress ends its game (`done`)
    full_clear: bool = False  # every hostile, every room: the Herald hunt (macros/tzloop.py `full_clear`)


LK = Kind(
    'lk', 'Lower Kurast', LOWER_KURAST, frozenset((LOWER_KURAST,)), KURAST_DOCKS, KEYS_WANTED, 'chests opened an hour',
    badge=False, fortress_ends_game=True,
)  # fmt: skip
# Andariel (routes/andariel-loop-plan.md): the waypoint to Catacombs Level 2, its stairs and Level 3's down, her fight
# on Level 4, the loot, Save and Exit there: the next game starts in the Rogue Encampment, a waypoint from Level 2
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
)
KINDS = {kind.key: kind for kind in (LK, ANDARIEL)}
# The terror zone kinds (macros/goals-plan.md; the player, 2026-10-19 ~02:12: "we're going to have separate mods: -
# full clear tz : for herald hunting - tz leveling: clear only elites/champs"): any zone, its goals from the agenda
# (macros/tzloop.py), never chosen by where the character stands (`kind_of`), offered only with macros/tzloop.py
# ENABLED (`loop_kinds`). A zone's game lasts minutes, not the Andariel run's one (open question 5 of goals-plan.md)
FIELD = frozenset(range(137)) - {ROGUE_ENCAMPMENT, 40, KURAST_DOCKS, PANDEMONIUM_FORTRESS, 109}
TZ_GAME_SECONDS = 1200.0
TZ = Kind(
    'tz', 'TZ leveling', 0, FIELD, PANDEMONIUM_FORTRESS, metric='elite kills an hour', game_seconds=TZ_GAME_SECONDS,
    agenda=True,
)  # fmt: skip
# The Herald hunt's measure is not ruled yet (goals-plan.md open question 8): Heralds and elites an hour, both reported
TZ_CLEAR = replace(TZ, key='tzclear', name='Full clear TZ', metric='Herald and elite kills an hour', full_clear=True)
TZ_KINDS = frozenset((TZ.key, TZ_CLEAR.key))


def loop_kinds() -> dict[str, Kind]:
    """The kinds the player may choose (KP_6 three times, restart.py --kind): the terror zone kinds only once they are
    promoted (macros/tzloop.py ENABLED)."""
    from inventory_tracking.macros import tzloop  # late: tzloop imports this module

    return {**KINDS, **({TZ.key: TZ, TZ_CLEAR.key: TZ_CLEAR} if tzloop.ENABLED else {})}


def kind_of(area: int | None) -> Kind | None:
    """The kind whose levels or act's town `area` is: the loop started there runs it. None: the Fortress, which both
    share, the lobby, elsewhere."""
    return next((kind for kind in KINDS.values() if area in kind.levels or area == kind.home), None)


# The legs, as the HUD says them.
NEXT_GAME = 'next game'
# The town visit (macros/visit.py `visit`; macros/town-plan.md step 3): Cain, the stash, Jamella, Halbu, the exit, each
# once and only with something to do. It took the place of four legs (identify, the stash, scrolls and keys, the staff's
# charges), which walked back and forth between them (the player, 2026-10-18 12:55: "we visit the stash only ONE time,
# no running back and forward")
TOWN = 'town visit'
TO_THE_CHESTS = 'to Lower Kurast'
CHESTS = 'the chests'
PICK_UP = 'what is left'
PORTAL = 'Town Portal'
TO_THE_FORTRESS = 'to Pandemonium Fortress'
LEAVE = 'Save and Exit'
TO_THE_CATACOMBS = 'to the Catacombs'  # Andariel's legs: the waypoint to Catacombs Level 2
DOWN = 'down the Catacombs'  # the level run to the stairs (Levels 2 and 3), then through them
FIGHT_ANDARIEL = 'Andariel'  # the level run on Level 4: her fight
# A trip to town from the level for room (`Loop.trip`): the portal, the Fortress's session, back by the Rogue
# Encampment's waypoint and through the portal
TRIP = 'to town for room'
TO_THE_ENCAMPMENT = 'to the Rogue Encampment'
THROUGH_PORTAL = 'back through the portal'
# Another Gheed's Fortune on the ground, carry-one (macros/charms.py; the player, 2026-10-18 13:39: "go to town; put our
# own gheed into SHARED tab; go back and pick new one; go to town, identify; check what is better (magic find roll);
# keep in own inventory better one"): to town by the portal (`SWAP_OUT`), the Fortress's stash (`GHEED_STASH`), back
# by the Rogue Encampment and the portal for the new one; to town again (`SWAP_BACK`), Cain and the stash
# (`GHEED_CHOOSE`), back through the portal for the rest of the level
SWAP_OUT = "Gheed's Fortune away"
GHEED_STASH = "Gheed's Fortune onto a shared page"
SWAP_BACK = "Gheed's Fortunes to compare"
GHEED_CHOOSE = "the better Gheed's Fortune"
# `Loop.gheed`, the swap's stage: on the way to the stash with the player's; back for the new one (theirs parked); on
# the way to compare; back to the level after the choice
OUT, PICK, CHOOSE, RETURN = 'out', 'pick', 'choose', 'return'
# Trips for room a game (`Loop.may_trip`; the player, 2026-10-18 16:50: "one game can do several trips to the town"),
# each only after one that made room: a trip whose visit can take nothing away (the player's charms, 13:38:17 on
# 2026-10-18) is not made again and again. Three: the inventory filled twice more on one level is rare (one game of
# 173 cycles needed two that day), and each trip is ~37 s of a 240 s game (GAME_SECONDS)
TRIPS_A_GAME = 3
# How often one leg may be made in one game before the loop gives up on it: a pickup a drop at a time, the level run
# again after it stopped short, any other leg once more after a failure that left the character where it was.
REPEATS = {PICK_UP: 20, CHESTS: 3, DOWN: 12, FIGHT_ANDARIEL: 3}  # DOWN: the pickups at the stairs too
# A game's trips for room and its Gheed's swap each go to the Fortress and back by the portal, the swap twice; the
# Fortress once more at an Andariel game's start (the Rogue Encampment's errands)
REPEATS |= {
    TRIP: TRIPS_A_GAME,
    TO_THE_FORTRESS: 1 + TRIPS_A_GAME + 2,
    TO_THE_ENCAMPMENT: TRIPS_A_GAME + 2,
    THROUGH_PORTAL: TRIPS_A_GAME + 2,
}
# A game's visits: the start's, each trip's, and one cut by the player's hand (REPEAT 2 stopped the loop on the third)
REPEATS |= {TOWN: 1 + TRIPS_A_GAME + 1}
# The terror zone kinds' legs (macros/tzloop.py, the agenda's goals by kind); a zone's game has up to ~8 excursions
# (the Kurast temples) of up to 7 levels: each bound is a game's worth, the agenda's own TRIES bound each goal
TZ_WAYPOINT, TZ_LEVEL, TZ_LOOT, TZ_PICKUP = 'TZ waypoint', 'TZ level', 'TZ loot', 'TZ pickup'
TZ_NEXT_LEVEL, TZ_PORTAL, TZ_BACK = 'TZ next level', 'TZ Town Portal', 'TZ back through the portal'
REPEATS |= {TZ_WAYPOINT: 12 + 2 * TRIPS_A_GAME, TZ_LEVEL: 40, TZ_LOOT: 20, TZ_PICKUP: 20, TZ_NEXT_LEVEL: 30}
REPEATS |= {TZ_PORTAL: 10 + TRIPS_A_GAME, TZ_BACK: 1 + TRIPS_A_GAME}
# Andariel's drops land through her death animation (mode 0, 1.55 s in the takes of 11:39-11:48 on 2026-10-18), the
# last 1.7 s after the kill was said; her fight's level run ends 0.4 s or more after it. Four games of 19 left 0.5-0.8 s
# after the kill (11:41:52, 11:51:39, 11:52:14): her level is not left with nothing to pick up before this long after
# the fight's end, and the ground is looked at again
DROPS_LAND = 2.0
# From her kill as the service saw it (terror/bosses.py KILLED_AT: the probe sees a death start within 0.25 s): the
# last item came 1.7 s after it. Timed from the first loot leg instead, every game waited 2 s, her pack's fight long
# after her death included (13:21 on 2026-10-18); DROPS_LAND stays for a kill this service did not see (a restart)
DROPS_AFTER_KILL = 1.9
KILL_FRESH = 120.0  # seconds: a kill older than this is another game's
REPEAT = 2
# A game longer than this is left (a game takes 40-75 s, 2026-10-17); a leg's stop or such a game is recovered from
# by leaving the game; past RECOVERIES times in RECOVERY_SECONDS the next leg waits RECOVERY_PAUSE first (`recover`)
FULL_FILE = 'full-stacks.json'
# The trade's trigger (town.py TRADE_ROOM): the loop's unidentified items and its junk wait, in the inventory and the
# cube, until fewer than TRADE_ROOM cells are free in both together; then the whole visit at once (`TOWN`)
GAME_SECONDS = 240.0
# A trip for room's time (`overdue`): the p90 of 2026-10-18's, 78.3 s (rca/2026-10-18/trips-and-towns-findings.md §2.4);
# several trips a game (TRIPS_A_GAME) would take a game with its fight and loot past GAME_SECONDS, and the watchdog's
# stop in town would stand the loop with the valuable on the level
TRIP_SECONDS = 80.0
LOADING_SECONDS = 10.0  # for a game's character to be read after it shows as in a game
# The character not moving STILL_SECONDS in a game, by STILL_UNITS, is the loop stuck too (the level run stood by a
# Flawless Diamond with the inventory full from 01:15:03 on 2026-10-17, the player's "we stuck, but didn't detect it
# in time"): the longest stand in a good game is a shop visit, under 15 s
STILL_SECONDS = 45.0
STILL_UNITS = 2.0
RECOVERIES = 3
RECOVERY_SECONDS = 600.0
RECOVERY_PAUSE = 30.0  # past RECOVERIES: a failing leg is not tried again at once, nor the loop stopped (`recover`)
# The character standing in a battle level outside a fight (attack mode off: a leg's own wait or spin) and losing
# BESET_LOSS of its life within BESET_SECONDS is beset (`beset`): the game is left at once. 09:36:41-09:37:11 on
# 2026-10-19 the recovery's pause stood 30 s at the Frozen River door among three hostiles, life 3119 -> 2334, until
# the player struck them (the player: "we stood still while under attack and almost died, only user intervented and
# helped to kill attackers ... we must not die or we lose exp and our gear"); a hit there was 130-260 life (4-8 %)
BESET_SECONDS = 4.0
BESET_LOSS = 0.05


class GameId(NamedTuple):
    """A game as the loop tells one from the next: its name and the player's unit id in it (the key `Sightings` keeps,
    world.py `Loot.game`). Names come round again (cyber99 -> cyber1, the second cyber81 of a session at 09:19:49 on
    2026-10-18); the unit id is a new one in a new game. The seed of the per-game record (rca/2026-10-18/
    arch-loop-orchestration.md Option B, step 1): logged when it changes (`Loop.observe`); the TZ agenda keys its
    game by it (tzloop.py)."""

    name: str
    player: int

    def __str__(self) -> str:
        return f'{self.name} (player unit {self.player})'


@dataclass
class Loop:
    """The loop's memory across its legs: on or off, the games played, the game prebuffed in, the game whose chests
    are done (the portal cast), and how often each leg was made in a game."""

    on: bool = False
    kind: Kind = LK
    placed: bool = False  # the kind told by where the loop's first leg finds the character (`leg`, `kind_of`)
    chosen: bool = False  # the kind chosen by hand (KP_6 three times) or carried over a restart: kept wherever
    games: int = 0
    prebuffed: str | None = None
    done: str | None = None
    made: Counter[tuple[str, str]] = field(default_factory=Counter)
    # The inventory as the player keeps it, by class and cell, read at the loop's first leg in a game: what is not in
    # it is the loop's, moved into the cube before a game is left (macros/cube.py, phase 9)
    own: frozenset[tuple[int, int, int]] | None = None
    # The loop's items still carried, by class and cell, kept from one KP_6 to the next and in `store` (by the
    # character's name) from one service to the next: an item the loop left in the inventory, the cube full, is still
    # the loop's when it starts again, not the player's (the player, 2026-10-16: "moving items to the cube from
    # inventory - seems not working. or working not always")
    mine: frozenset[tuple[int, int, int]] = frozenset()
    store: Path | None = None
    # The player's protected inventory cells (macros/volatile.py) are kept per character in STORE_FILE beside `store`;
    # `own` is told from them at every leg; `printed`: the unit ids of the player's items whose stats were last learnt
    # (ids, not class and cell: the Gheed's swap at 06:02 on 2026-10-19 put a new charm of its class in its cell)
    printed: frozenset[int] | None = None
    character: str | None = None
    # The keys or the Town Portal charges under shop.py MIN_STOCK at the last leg's look: Jamella first (phase 8)
    short: bool = False
    # How the character casts Town Portal at the last look in a game (macros/portal.py `portal_source`): the Sling's
    # has no charges to count or buy (the player, 2026-10-18); None: not read since the start
    portal: PortalSource | None = None
    # The game is to be left from wherever the character is (`recover`), and when the recoveries were
    abandon: bool = False
    fetch_again: str | None = None  # the game a leg was made again for a valuable left for no lack of room (runner.py)
    cooling: float = 0.0  # time.monotonic() before which no leg is made (`recover`, RECOVERY_PAUSE)
    fought: tuple[str, float] | None = None  # (the game, the run's clock) at her level's first loot leg (`DROPS_LAND`)
    recovered: list[float] = field(default_factory=list)
    # The character's looks in a stand outside a fight (`beset`): (when, where, life, the game)
    hurt: list[tuple[float, tuple[float, float], int, str]] = field(default_factory=list)
    # The game (None: the lobby) the loop was last seen in, and since when (`overdue`)
    seen: tuple[str | None, float] | None = None
    # The level card's marks by label, in tiles (levels/guide.py `marks`): the town's waypoint out of sight
    marks: Callable[[str], tuple[tuple[float, float], ...]] | None = None
    # The resource classes whose stash stack is full (99: the player, 2026-10-17, "we have 99 tal runes and cannot add
    # more. probably we better just sell them (and other runes that will have 99)"), kept in FULL_FILE beside `store`:
    # not picked up, and those carried are sold at Jamella (shop.py `restock`)
    full: set[int] = field(default_factory=set)
    # The staff's Teleport in the loop's moves (`teleports`): while the gold carried pays for it
    teleports: bool | None = None  # None: not decided since the start (`teleports`)
    wear: str = '?'  # the most worn item's durability at the last look (`leg`), for the log
    # The game the last look in one was of (`observe`): kept through the lobby and over a KP_6 off and on
    game_id: GameId | None = None

    @property
    def sold_full(self) -> frozenset[int]:
        """The full stacks' classes that are not picked up (town.py `sold_full`): the runes (sold), the materials (put
        down), never a gem or a potion."""
        return sold_full(self.full)

    # The staff's charges low enough for Halbu's repair (macros/repair.py `wants`), and the game count of a visit that
    # did not raise them (none tried again for RETRY_GAMES games)
    repair: bool = False
    repair_failed: int | None = None
    # A valuable the inventory has no room for, stood by: the loop's items go into the cube at the next leg
    # (`make_room`), once a game (`room_tried`, the game's name), before the loop stops for the player
    make_room: bool = False
    room_tried: str | None = None
    # Then one of the loop's items taken only to identify it dropped for the valuable's block (macros/cube.py
    # `drop_for`), once a game (`dropped`), before the loop stops for the player
    drop_room: bool = False
    dropped: str | None = None
    # The trade (`TOWN`): the inventory and cube cells free at the last look, whether the loop carried anything a visit
    # takes away (`carrying`); the game whose visit began (`visiting`: a visit cut by the player's hand is made again,
    # and plans only what is left) and the game whose visit is done (`visited`: once a game; a trip's own: `TRIP`)
    free: int | None = None
    carrying: bool = False
    visiting: str | None = None
    visited: str | None = None
    waiting: bool = False  # for the game window's focus (runner.py): the watchdogs pause
    moved: tuple[tuple[float, float], float] | None = None  # where the character last moved to, and when (`still`)
    moved_in: str | None = None  # the game `moved` was read in (`still`: a new game counts afresh)
    counted_in: str | None = None  # where `made` counts (`count`)
    # A valuable on the level with no room for it, the cube tried (runner.py `_loop_stopped`): a trip to town for
    # room (`trip`, its game; `trips` made in it, up to TRIPS_A_GAME: `may_trip`); the Fortress reached on it
    # (`fortressed`), the portal's town end (`portal_at`), the level reached again (`returned`), the sightings' trips
    # back given again for it (`forgiven`: the game and the trip's number); the cells free as it began (`trip_free`)
    # and those it made (`trip_gained`, at its return: None unread)
    trip_due: bool = False
    trip: str | None = None
    trips: int = 0
    fortressed: str | None = None
    portal_at: tuple[float, float] | None = None
    returned: str | None = None
    forgiven: tuple[str, int] | None = None
    trip_free: int | None = None
    trip_gained: int | None = None
    # A unique Grand Charm on the ground the pickup could not take with the player's Gheed's Fortune carried (runner.py
    # `_loop_stopped`): the swap (SWAP_OUT ... GHEED_CHOOSE), once a game (`swap`, its game; `swap_level` where it
    # began); `parked` the player's on a shared page (kept over a restart: runner.py `resume_state`), `gheed` the
    # stage (OUT, PICK, CHOOSE, RETURN), `swap_units` the units carried before, `fresh` a new one carried at the last
    # look (macros/charms.py `candidates`)
    swap_due: bool = False
    swap: str | None = None
    swap_level: int | None = None
    parked: Parked | None = None
    gheed: str | None = None
    swap_units: frozenset[int] = frozenset()
    fresh: bool = False
    # The runner's (runner.py `_forget_given_up`): the level run's give-up memory cleared once the player's Gheed's
    # Fortune is on a shared page (`GHEED_STASH`), as the pickup step's `SHUNNED` is: the refused charm is tried again
    forget: Callable[[], None] | None = None
    # The terror zone kinds' goals (macros/agenda.py, macros/goals-plan.md): the game's queue, its package stack, the
    # leaders seen; a new game starts them afresh (`Agenda.begin`). The Lower Kurast and Andariel kinds read none of it
    agenda: Agenda = field(default_factory=Agenda)

    def start(self) -> None:
        self.full |= self._full_stored()
        self.on, self.made, self.own, self.abandon, self.seen, self.moved = True, Counter(), None, False, None, None
        self.counted_in, self.placed, self.portal, self.printed = None, False, None, None

    def recover(self, why: object, now: float) -> bool:
        """Whether the loop goes on after `why` stopped a leg, by leaving the game: not with the character dead.
        Past RECOVERIES recoveries within RECOVERY_SECONDS the next leg waits RECOVERY_PAUSE (`cooling`) and the loop
        goes on: a stopped loop stood until someone looked (10 stops of "Save and Exit again and again", 200 min, on
        2026-10-17; the player, 2026-10-18: "fully prevent us from stopping")."""
        if isinstance(why, Dead):
            return False
        self.recovered = [at for at in self.recovered if now - at < RECOVERY_SECONDS]
        if len(self.recovered) >= RECOVERIES:
            self.cooling = now + RECOVERY_PAUSE
            LOG.warning('Macro: loop: %d recoveries in %.0f s: the next leg after %.0f s (%s)',
                        len(self.recovered) + 1, RECOVERY_SECONDS, RECOVERY_PAUSE, why)  # fmt: skip
        self.recovered.append(now)
        self.abandon = True
        return True

    def overdue(self, game: str | None, now: float) -> bool:
        """Whether the loop has been in `game` (None: the lobby) over GAME_SECONDS, and TRIP_SECONDS more for each trip
        for room made in it, seen now."""
        if self.seen is None or self.seen[0] != game:
            self.seen = (game, now)
            return False
        allowed = (self.kind.game_seconds or GAME_SECONDS) + TRIP_SECONDS * self.trips_in(game)
        return now - self.seen[1] > allowed and not self.abandon

    def still(self, where: tuple[float, float] | None, now: float, game: str | None = None) -> bool:
        """Whether the character, at `where` now, has stood within STILL_UNITS for over STILL_SECONDS in `game`. A new
        game counts afresh: every game begins by the Fortress's waypoint, the same place, and the stand of the game
        before (a recovery's RECOVERY_PAUSE in it) counted on into the next, which was left 5 s in, then again
        (09:22:44-09:23:50 on 2026-10-19: 5 recoveries in a row). `now` is time.monotonic()."""
        if where is None:
            return False
        cooling = now < self.cooling  # the pause after recoveries (`recover`) is the loop's own wait, no stand
        if self.moved is None or cooling or math.dist(where, self.moved[0]) > STILL_UNITS or game != self.moved_in:
            self.moved, self.moved_in = (where, now), game
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
        """Whether the character, at `where` in level `area` of `game` with `life` (points, maximum) now, has stood
        (within STILL_UNITS) losing BESET_LOSS of its maximum life within BESET_SECONDS: hit with no fight. The caller
        asks it only outside a fight (runner.py `poll`: attack mode off). Said once, then counted afresh; not while the
        game is being left already (`abandon`), nor in a town or the lobby. `now` is time.monotonic()."""
        if where is None or life is None or game is None or area is None or area in TOWN_IDS or life[1] <= 0:
            self.hurt.clear()
            return False
        self.hurt = [
            look
            for look in self.hurt
            if now - look[0] <= BESET_SECONDS and look[3] == game and math.dist(look[1], where) <= STILL_UNITS
        ]
        self.hurt.append((now, where, life[0], game))
        if max(look[2] for look in self.hurt) - life[0] >= BESET_LOSS * life[1] and not self.abandon:
            self.hurt.clear()
            return True
        return False

    def stop(self) -> None:
        self.on = False

    def sort(
        self,
        held: frozenset[tuple[int, int, int]],
        name: str | None,
        loose: frozenset[tuple[int, int, int]] = frozenset(),
    ) -> None:
        """The carried items `held` told apart: at the loop's first look the player's are what is not the loop's
        (`mine`, read from `store` for the character `name`) nor `loose` (an unidentified item, a rune or a gem: never
        one the player keeps carried); then the loop's are what is not the player's."""
        if self.own is None:
            self.mine = self.mine or self._stored(name)
            # Items moved by hand change cells, and the store knows them no more: Antlers, a Ring, two runes and a
            # Flawless Topaz read as the player's took the loop's room, no 1 x 3 left for a Grand Charm (10:28 on
            # 2026-10-18, after the player sorted game 28's items by hand)
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
        """The character's protected cells as kept; none kept, seeded from `pack` (the player's items told apart as
        `sort` tells them at the loop's first look: neither the loop's stored items nor `loose`)."""
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
        """`own` at every leg: the inventory's items on the player's protected cells (macros/volatile.py); the cube's
        and the volatile cells' are the loop's. The stats of the player's items learnt whenever `own` changes."""
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

    def players_item(self, item: Carried, stats: Mapping[int, int]) -> bool:
        """Whether `item` is one of the player's by its stats (macros/volatile.py `prints`): never sold nor dropped."""
        from inventory_tracking.macros.volatile import is_players

        return self.store is not None and is_players(item, stats, self.volatile.prints(self.character))

    def visit_due(self, game: str) -> bool:
        """Whether a town visit is due in `game` (once: `visited`): the room low (TRADE_ROOM; a trip for room whatever
        the cells count) with anything a visit takes away, or, but at a game's end, keys or scrolls short or a repair
        due. Any errand to a vendor is the whole visit (the player, 15:52 on 2026-10-17: "when we get to maintenance
        (refilling, trading, repairing) - it is better to identify everything, stash good, sell junk, refill, optionally
        repair ... right now we're running between vendors/stash/waypoint with items that could be already 10 times
        sold"). At a game's end the room alone: a refill or a repair waits for the next game's start."""
        if self.visited == game:
            return False
        if self.visiting == game:
            return True  # begun and cut short: made again, from what is left
        cramped = self.tripping(game) or (self.free is not None and self.free < TRADE_ROOM)
        return (cramped and self.carrying) or (self.done != game and (self.short or self.repair))

    def tripping(self, game: str) -> bool:
        """Whether a trip for room is on its way in `game`: begun (`TRIP`) and not back through the portal."""
        return self.trip == game and self.returned != game

    def trips_in(self, game: str | None) -> int:
        """The trips for room made in `game`."""
        return self.trips if game is not None and self.trip == game else 0

    def may_trip(self, game: str | None) -> bool:
        """Whether another trip for room may be made in `game` (the player, 2026-10-18 16:50: "one game can do several
        trips to the town"): none on its way, fewer than TRIPS_A_GAME made, and the last one made room (a visit that
        took nothing away would take nothing away again); a last one whose room was unread may be made once more."""
        made = self.trips_in(game)
        if made == 0:
            return True
        if made >= TRIPS_A_GAME or game is None or self.tripping(game):
            return False
        return self.trip_gained is None or self.trip_gained > 0

    def repair_waited(self) -> bool:
        """Whether a repair may be tried: none for RETRY_GAMES games after a visit to Halbu that raised nothing."""
        return self.repair_failed is None or self.games - self.repair_failed >= RETRY_GAMES

    def exit_of(self, game: str) -> Exit:
        """How the visit in `game` ends: none at a game's end (Save and Exit from where it ends), the portal back on a
        trip for room, else the waypoint."""
        if self.done == game:
            return Exit.LEAVE
        if self.tripping(game):
            return Exit.PORTAL
        return Exit.WAYPOINT

    def _full_stored(self) -> set[int]:
        if self.store is None:
            return set()
        try:
            return {int(txt) for txt in json.loads((self.store.parent / FULL_FILE).read_text())}
        except OSError, ValueError, TypeError:
            return set()

    def keep_full(self) -> None:
        """`full` into FULL_FILE."""
        if self.store is None:
            return
        try:
            (self.store.parent / FULL_FILE).write_text(json.dumps(sorted(self.full)))
        except OSError as error:
            LOG.info('Macro: the full stacks are not kept: %s', error)

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
        """A trip to town for room starts in `game` (the TRIP leg, macros/tzloop.py `trip`): counted (`may_trip`), and
        with its own Fortress, its own way back and a whole visit of its own: a Fortress reached before it this game is
        not its (11:56:48 on 2026-10-18), nor a way back the Gheed's swap made (13:59:45), nor the game's first visit
        (12:36: the Fortress and straight back, still no room)."""
        self.trips = self.trips_in(game) + 1
        self.trip_due, self.trip, self.fortressed = False, game, None
        self.trip_free, self.trip_gained = self.free, None
        self.returned = None
        self.visiting = self.visited = None

    def back_through_portal(self, run: Run, game: str) -> None:
        """Through the portal back to the level it was opened on (`portal_at`), a trip's end told first."""
        if self.tripping(game):
            self._back_from_trip()
        self.returned = game
        through_portal(run, self.portal_at)

    def note_portal(self, run: Run) -> None:
        """Where the character stands after a portal to town: the way back's spot (`back_through_portal`)."""
        here = run.world().player
        self.portal_at = (here.x, here.y) if here is not None else None

    def prebuff_once(self, run: Run, game: str) -> None:
        """The prebuff, once a game."""
        if self.prebuffed != game:
            prebuff(run)
            self.prebuffed = game

    def _back_from_trip(self) -> None:
        """A trip for room through the portal back to its level: the room it made (`trip_gained`, `may_trip`); the cube
        tried again before another trip (the visit emptied it: `room_tried`); the level's ground tried again with the
        room, by the pickup (`SHUNNED`) and the level run (`forget`), as at the Gheed's swap's GHEED_STASH (the player,
        2026-10-18 16:50: "one game can do several trips to the town")."""
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
        """The game `world` is in, by its name and the player's unit (`GameId`), logged when it is another than the
        last look's; the lobby, or a game whose character is not read yet, keeps the last. Nothing reads it yet: the
        log says whether the unit id tells every new game apart before the per-game record is keyed by it."""
        if not world.in_game or world.player is None:
            return self.game_id
        seen = GameId(world.game_name, world.player.unit_id)
        if seen != self.game_id:
            LOG.info('Macro: loop: game changed: %s, was %s', seen, self.game_id or 'none')
            self.game_id = seen
        return seen

    def count(self, world: World, leg: str) -> None:
        """`leg` made once more where `world` is; `Abort` when that is more than REPEATS allows. A game's legs count
        in that game; the lobby's (the next game) count by the game just left, so each game left has its own: counted
        all in one, the third game the loop made stopped it, "next game again and again in the lobby" (20:55:43 and
        21:05:53 on 2026-10-16, each the third game after KP_6)."""
        where = world.game_name if world.in_game else f'the lobby after {world.game_name or "no game"}'
        if where != self.counted_in:
            # Counted only where the loop is now: names come round again (cyber99 -> cyber1), and the second cyber81
            # of a session began with the first one's count, "next game again and again in the lobby after cyber81"
            # at its first try (09:19:49 on 2026-10-18)
            self.made.clear()
            self.counted_in = where
        self.made[where, leg] += 1
        if self.made[where, leg] > REPEATS.get(leg, REPEAT):
            # Said once, then counted afresh: the recovery that follows makes the leg again, and a count left over the
            # limit stopped each try at once, 4 recoveries in 20 ms and the loop held 30 s (the player's mouse in the
            # lobby twice, 18:55:33-34 on 2026-10-18)
            del self.made[where, leg]
            raise Abort(f'{leg} again and again in {where}: nothing came of it')

    def next_game(self, run: Run, world: World, key_names) -> None:
        """The NEXT_GAME leg: the next game made from the lobby, prebuffed in its town."""
        self.trip_due = self.swap_due = self.fresh = False
        self.gheed = None  # a player's Gheed's Fortune still parked is fetched from the next game's town
        trace = create_next_game(run, world.game_name)
        run.keys = character_keys(run, key_names)
        now = run.world()
        try:
            # In town: Consume's speed is the town's walks' too (the player, 10:58 on 2026-10-18: "consume buff
            # grants +run/walk speed and make things faster in town, so, probably we should keep it up in town
            # too"); the battleground's own (Battle Orders at the arrival's swap, the Defiler) are cast there
            prebuff(run, fresh=trace)
            self.prebuffed = now.game_name
        except Hand:
            raise
        except Abort as stop:
            if now.player is None or now.player.area != ROGUE_ENCAMPMENT:
                raise
            # Kashya, Warriv and Cain stand where a game starts there, and Consume cannot take them (routines.py
            # TOWN_NPCS; three tries and the game left, 10:20:17 on 2026-10-18): cast again on Catacombs Level 2
            # (`DOWN`), the game not left for it
            LOG.info('Macro: loop: the prebuff in the Rogue Encampment failed (%s): again on Catacombs 2', stop)

    def town(self, run: Run, visit: Callable[[Exit], object] | None, game: str, exit: Exit) -> None:
        """The TOWN leg: the town visit, ending by `exit`."""
        # One town visit (macros/visit.py `visit`; the player, 2026-10-18 12:55: "identify everything with cain;
        # move to the shared stash; put all items that we need to keep in stash ... visit store and sell junk items
        # from inventory and cube; refill the consumables; if we need to repair things - repair things; go to
        # waypoint"): begun (`visiting`), a cut one made again from what is left; done once a game (`visited`)
        if visit is None:
            raise Abort('no town visit to make')
        self.visiting = game
        contract = visit(exit)
        self.visited = game
        self.repair = False
        # A keeper no stash page takes (town.py `Contract.stash_full`): the loop stops (the player, 2026-10-18
        # 16:50: "if stash is full - we need to stop loop"), here in town after the visit's own end, nothing of the
        # level's left behind by a game left; not a recovery (runner.py `_loop_stopped`, cause 'stash')
        full = tuple(getattr(contract, 'stash_full', None) or ())
        if full:
            raise Abort(f'the stash is full: {", ".join(full)}', cause='stash')

    def leave(self, run: Run, game: str) -> None:
        """The LEAVE leg: Save and Exit, the game done and counted."""
        self.done = game  # Andariel's games are left from her level: done there
        leave_game(run)
        self.abandon = False
        self.games += 1

    def leg(
        self,
        run: Run,
        key_names,
        progress: Progress | None,
        level_run: Callable[[], None],
        pick_up: Callable[[], bool],
        visit: Callable[[Exit], object] | None = None,
        identify: Callable[[tuple[Carried, ...]], object] | None = None,
        bring: Callable[[list[Carried]], int] | None = None,
        down: Callable[[], None] | None = None,
        fight: Callable[[], None] | None = None,
        item_stats: Stats | None = None,
        shown: Remembered | None = None,
        left: Callable[[], str | None] | None = None,
        tz: TzHands | None = None,
    ) -> str:
        """Make the next leg (`next_leg`); the leg made. `level_run()` asks the runner for the KP_1 level run,
        which follows this leg; `pick_up()` takes one drop, False with nothing worth it on the ground; `visit(exit)`
        makes the town visit (macros/visit.py `visit`: Cain, the stash, Jamella, Halbu, the exit) and says what it left;
        `identify(items)` identifies `items` (at Cain, macros/cain.py) and `bring(items)` takes items out of the cube
        into the inventory (macros/cube.py `unpack`), for the Gheed's swap; `down()` Andariel's level run to the stairs
        or the press through them; `fight()` her level run, fighting; `item_stats(unit)` an item's stats
        (world.GameMemory.item_stats: a Gheed's Fortune's Magic Find), `shown` the shared page the stash showed last
        (macros/visit.py `Remembered`), `left()` a valuable seen and still on the ground (runner.py
        `_valuable_left`); `tz` the terror zone kinds' hands (macros/tzloop.py `TzHands`)."""
        world = run.world()
        if (cooling := self.cooling - time.monotonic()) > 0:
            # Recoveries one after another: a pause, not a stop (`recover`), and only where nothing attacks: the lobby
            # or a town. In a battle level the game is left first (the recovery's leg) and the rest of the pause waited
            # in the lobby: the pause stood 30 s in the Crystalline Passage among three hostiles, 09:36:41-09:37:11 on
            # 2026-10-19, life 3119 -> 2334 until the player struck them ("we stood still while under attack and
            # almost died")
            if not world.in_game or (world.player is not None and world.player.in_town):
                run.pace.sleep(cooling)
                world = run.world()
            else:
                area = world.player.area if world.player is not None else 'an unread level'
                LOG.info('Macro: loop: the pause after recoveries (%.0f s) is not stood in level %s: the game is left '
                         'first', cooling, area)  # fmt: skip
        if world.in_game and world.player is None:
            # A game still loading: its character not read yet. Waited for, not a leg's stop: three recoveries in 20 ms
            # from it stopped the loop (12:45:41 on 2026-10-17, "not in a game")
            world = run.seen(lambda w: w.player is not None or not w.in_game, LOADING_SECONDS) or run.world()
        self.observe(world)
        if not world.in_game:
            self.abandon = False  # left
        if not self.placed and not self.chosen and world.player is not None:
            # The kind is where the character stands: the Rogue Encampment's, Lower Kurast's (the Fortress, both
            # kinds' town, keeps the kind chosen: three presses of KP_6)
            self.placed = True
            found = kind_of(world.player.area)
            if found is not None and found != self.kind:
                LOG.info('Macro: loop: %s, by where the character is', found.name)
                self.kind = found
        pack = run.carried() if world.in_game and run.carried is not None else None
        if world.in_game and world.player is not None:
            source = portal_source(run)
            if source != self.portal:
                # Said at the loop's first leg in a game and whenever it changes (the ring put on or taken off): the
                # first live game confirms the Sling is read and its skill bound (macros/sling-plan.md)
                worn = run.reads.worn_skills()
                LOG.info('Macro: loop: Town Portal from %s: skill %d %s; worn skills %s', source.name, source.skill,
                         slot_note(world, source), sorted(worn) if worn is not None else 'unread')  # fmt: skip
                self.portal = source
        self.short = short(pack, self.portal or FROM_TOME)
        if pack is not None and world.player is not None and self.own is None:
            # What the loop's first look finds carried, told apart (the player's own, the loop's, the cube's)
            mine_now = self.mine or self._stored(world.player.name)
            LOG.info("Macro: loop: carried at its first look: %s; the cube: %s", '; '.join(
                f"{_named(i)} ({i.x},{i.y}){f' unique row {i.unique}' if i.quality == 7 else ''}"
                f"{' the loop' if (i.txt, i.x, i.y) in mine_now else ''}"
                for i in pack.items
            ), '; '.join(_named(i) for i in pack.in_cube))  # fmt: skip
        if pack is not None and world.player is not None:
            # The player's items told first: the room is counted at the loop's first look too (a restart's first leg in
            # the Rogue Encampment went to the Catacombs with the inventory full, 10:21:28 on 2026-10-18)
            loose = frozenset(
                (i.txt, i.x, i.y) for i in pack.items if (not i.identified and i.quality >= MAGIC) or i.txt in RESOURCES
            )
            if self.store is not None:
                self.tell(pack, world.player.name, loose, item_stats)  # the kept volatile cells (macros/volatile.py)
            else:
                self.sort(own_of(pack.items), world.player.name, loose)  # no store (tests): the first look's
        items = loot(pack, self.own) if pack and self.own else []
        in_town = world.player is not None and world.player.area == PANDEMONIUM_FORTRESS
        if self.parked is not None and pack is not None:
            self.fresh = bool(candidates(pack, self.parked, self.swap_units))
        if pack is not None and self.own is not None:  # unread in the lobby: the last look's stand
            carried = [*items, *pack.in_cube]
            cube = roomed(pack).cube or ()
            in_inventory = INVENTORY_CELLS - sum(item.size[0] * item.size[1] for item in pack.items)
            in_cube = sum(row.count('.') for row in cube)
            self.free = in_inventory + in_cube  # the cube's room too: the trade waits until both are full
            if in_inventory < TRADE_ROOM and overflow(pack, self.own):
                # The cube's room in pieces none of the loop's items fits ('.#./.#./.#./...': 9 cells, two items
                # stayed out, the inventory full, a Rage Mask left, 12:44-12:45 on 2026-10-17): no room as such
                self.free = min(self.free, in_inventory)
            if not any(rows and Grid(rows).has_room(SURE_BLOCK) for rows in (pack.inventory, cube)):
                # No SURE_BLOCK free in the inventory nor in the cube, whatever the cells count: no room as such
                self.free = min(self.free, TRADE_ROOM - 1)
            if in_town and self.free < TRADE_ROOM:
                # The trade's trigger told (a second session one game after a full one, 14:15 on 2026-10-17)
                LOG.info('Macro: loop: room low: %d cells free (inventory %d, cube %d, loop items %d in the inventory '
                         'and %d in the cube; cube rows %s)', self.free, in_inventory, in_cube, len(items),
                         len(pack.in_cube), '/'.join(cube))  # fmt: skip
            # What a visit can take away: not a full gem stack's gems, kept and neither stashed nor sold (`sold_full`
            # is the runes' and the materials'), which sent the loop to a session every game, each leaving the room as
            # low (the cube full of them, 07:05-07:07 on 2026-10-18)
            stuck = self.full - self.sold_full
            # A transmute's worth of one kind (cube.py `transmute`, three into a perfect one) is a session's work too:
            # without it the kept gems filled the cube and the inventory, and no session came (21 items, 09:43 to 10:22
            # on 2026-10-18)
            cubable = Counter(i.txt for i in carried if i.txt in stuck and perfect_of(i.txt) not in (None, *self.full))
            self.carrying = (
                any(i.txt not in stuck for i in carried)
                or bool(surplus(carried, stuck))
                or any(count >= GEMS_A_KIND for count in cubable.values())
            )
            visiting = world.in_game and self.visiting == world.game_name and self.visited != world.game_name
            if in_town and in_inventory < TRADE_ROOM <= self.free and in_cube >= 3 and items and not visiting:
                # the loop's items into the cube (the runner's `make_room`, no walk): the inventory's room for pickups,
                # between visits only (in one it moved the session's junk into the cube, 13:03 on 2026-10-17)
                self.make_room = True
        staff = run.teleport() if world.in_game and run.teleport is not None else None
        # His line learned first, his panel only opened (no gold spent) while repairs are off (macros/repair.py); in a
        # visit (town.py `tops_up`) any charge missing, decided again at Halbu's stop (macros/visit.py)
        in_session = world.in_game and self.visiting == world.game_name
        topped = tops_up(staff, in_session, self.visited == world.game_name)
        # A worn item low on durability: a repair of its own, the staff's charges full (Teleport of the character's own)
        wear = run.wear() if world.in_game and run.wear is not None else None
        self.wear = worn_text(wear)
        coins = gold(run) if (staff is not None and (wants(staff) or topped)) or worn_out(wear) else None
        self.repair = due(staff, wear, coins, top_up=topped, waited=self.repair_waited())
        goal = None
        if self.kind.agenda:
            from inventory_tracking.macros import tzloop  # late: tzloop imports this module

            # The terror zone kinds' legs are the agenda's goals (macros/goals-plan.md), performed by tzloop
            goal = tzloop.choose(world, progress, self, tz)
            leg = tzloop.leg_of(goal)
        else:
            leg = next_leg(world, progress, self)
        game = world.game_name if world.in_game else ''
        self.count(world, leg)
        run.say(f'Loop: game {self.games + 1}, {leg}')
        if leg != NEXT_GAME:
            run.keys = character_keys(run, key_names)  # Swap Weapons among them: the arrival's check (`arrived`)
        if goal is not None:
            from inventory_tracking.macros import tzloop

            tzloop.perform(self, run, key_names, progress, goal, tz, visit)
            return leg
        if leg == NEXT_GAME:
            self.next_game(run, world, key_names)
        elif leg == TOWN:
            self.town(run, visit, game, self.exit_of(game))
        if leg in (TO_THE_CHESTS, TO_THE_CATACOMBS):
            # The carried gold once a game: the repairs' and the sales' (the player, 2026-10-17: "just use gold in the
            # inventory")
            coins = gold(run)
            LOG.info('Macro: loop: gold carried %s, the most worn item %s', coins, self.wear)
            if not (run.own_teleport is not None and run.own_teleport()):
                # The staff's charges priced by the gold; Teleport of the character's own (Enigma) is in every move
                # whatever the gold (runner.py, LOOPED_TELEPORT)
                self.teleports = teleports(coins, gold_cap(run), self.teleports)
            if world.player is None or world.player.area != ROGUE_ENCAMPMENT:
                self.prebuff_once(run, game)
            travel(run, self.kind.start, self.marks)
        elif leg == CHESTS:
            level_run()
        elif leg == DOWN:
            if down is None:
                raise Abort('no level run to the stairs')
            self.prebuff_once(run, game)  # by the waypoint it came in by (none in the Rogue Encampment: `NEXT_GAME`)
            down()
        elif leg == FIGHT_ANDARIEL:
            if fight is None:
                raise Abort('no level run to fight with')
            fight()  # posts her level run and returns; the run's end is the next leg's (`PICK_UP`)
        elif leg == PICK_UP:
            boss = self.kind.boss
            if boss is not None and (self.fought is None or self.fought[0] != game):
                # The first look at her level's loot: her fight's run has just ended (`fight` only posts it: the clock
                # at its leg let the game be left 0.05 s into the loot, 13:02:58 on 2026-10-18)
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
                    LOG.info("Macro: loop: Andariel's drops may still be landing: %.1fs more, then the ground again",
                             landing)  # fmt: skip
                    run.pace.sleep(landing)
                else:
                    progress.looted(world.player.area)
        elif leg == PORTAL:
            if not pick_up():
                self.done = game
                to_town(run, key_names, pick_up)
        elif leg == TRIP:
            self.begin_trip(game)
            to_town(run, key_names)  # no pickup at the portal: there is no room
            self.note_portal(run)
        elif leg == SWAP_OUT:
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
        elif leg == GHEED_STASH:
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
                # and by the level run too, which gave it up: at 13:57:50 on 2026-10-18 the new one (the same unit) was
                # never tried, the run stood 45 s by it (rca/2026-10-18/loop-robustness-findings.md §2.3)
                self.forget()
            LOG.info("Macro: charms: back through the portal for the new Gheed's Fortune")
        elif leg == SWAP_BACK:
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
        elif leg == GHEED_CHOOSE:
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
                bring([new])  # out of the cube: a Ctrl + click from the inventory takes it to the stash
                after = run.reads.carried()
                new = next((i for i in after.items if i.unit_id == new.unit_id), None) if after is not None else None
            # A Latent Sunder charm picked up in the swap made with no 1 x 3 free (runner.py `_gheeds_swap`) lies in
            # the player's cell: onto a shared page, so the player's comes back
            others = newcomers(now, parked, self.swap_units) if now is not None else []
            kept = choose(run, parked, new, item_stats, shown, others=others)
            if self.own is not None:
                self.own = (self.own - {parked.cell}) | {(kept.txt, kept.x, kept.y)}
            self.parked = None
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
                    self.done = game  # the level's loot done: Save and Exit from here
                    LOG.info("Macro: charms: the level's loot is done: the game is left from town")
        elif leg == TO_THE_ENCAMPMENT:
            travel(run, ROGUE_ENCAMPMENT, self.marks)
        elif leg == THROUGH_PORTAL:
            self.back_through_portal(run, game)
            if self.gheed in (PICK, RETURN) and progress is not None and self.swap_level is not None:
                # The level's ground looked at again: a pickup that found nothing it could take (the refused charm
                # shunned) marked it looted, and the leg after would leave it with the new one on the ground
                progress.facts = replace(progress.facts, looted=progress.facts.looted - {self.swap_level})
            if self.gheed == RETURN:
                self.gheed = None
        elif leg == TO_THE_FORTRESS:
            self.fortressed = game
            if self.kind.fortress_ends_game:
                self.done = game  # left Lower Kurast: a game begun here is not the loop's to play
            # (Andariel's: from the Rogue Encampment to the Fortress's trade session, her level still ahead)
            travel(run, PANDEMONIUM_FORTRESS, self.marks)
        elif leg == LEAVE:
            self.leave(run, game)
        return leg


# Shares of the gold cap: Teleport from the first, Blade Warp alone under the second. 0.6/0.3 left it off for long
# stretches: a session's sales (~40-100k) pay less than its repairs (~85k), and the gold has no other use in the loop
# (the player, 2026-10-17: "if we make enough gold - we can use teleport staff more often"). Off under 15% (141,000
# at level 94: a full repair, ~118,000, is still paid from it)
TELEPORT_ON, TELEPORT_OFF = 0.35, 0.15
GOLD_CAP = 990_000  # the cap at level 99, for a level unread


def teleports(coins: int | None, cap: int | None, now: bool | None) -> bool | None:
    """Whether the loop's moves take the staff's Teleport this game (travel.py LOOPED_TELEPORT): from TELEPORT_ON of
    the gold cap carried, until under TELEPORT_OFF of it; as it was, with the gold unread. With charges, ~7 a cycle
    (~11,900 gold), it spends about twice what the sales bring: the gold over the cap would fall to the ground at a sale
    (the player, 2026-10-17: "if we make enough gold - we can use teleport staff more often to speed up things")."""
    if coins is None:
        return now
    most = cap or GOLD_CAP
    if now is None:
        # The first look since a start: on over TELEPORT_OFF. Each restart began it off, and at 527,000-588,000 carried
        # (under TELEPORT_ON) 12 of 24 stays were made without it, 32.9 s against 26.0 (16:40-16:50 on 2026-10-17)
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
        # The town visit (`Loop.visit_due`): the room low with anything a visit takes, keys or scrolls short, a repair
        # due; once a game, the cut one made again
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
    raise Abort(f'the loop has nothing to do in {display_name(player.area)}')


def gheeds_leg(world: World, loop: Loop) -> str | None:
    """The Gheed's swap's leg where the character is (macros/charms.py; `Loop.gheed` its stage), None for the loop's
    others. The player's Gheed's Fortune is never left in the stash at a game's end: with it parked the Fortress's leg
    is the choice, the Rogue Encampment's the way there, a level's (the new one carried, or no stage of picking it up)
    the way to town; a game given up (`abandon`) tries each of these REPEAT times before it is left, and the next game's
    town fetches it."""
    player = world.player
    assert player is not None
    game, area, parked, stage = world.game_name, player.area, loop.parked, loop.gheed
    if loop.abandon:
        if parked is None:
            return None
        legs = {PANDEMONIUM_FORTRESS: GHEED_CHOOSE, ROGUE_ENCAMPMENT: TO_THE_FORTRESS}
        leg = legs.get(area, SWAP_BACK if area in ANDARIEL.levels else None)
        return leg if leg is not None and loop.made[game, leg] < REPEAT else None
    if area == PANDEMONIUM_FORTRESS:
        if parked is not None:
            return TO_THE_ENCAMPMENT if stage == PICK else GHEED_CHOOSE
        if stage == OUT:
            return GHEED_STASH
        return TO_THE_ENCAMPMENT if stage == RETURN else None
    if area == ROGUE_ENCAMPMENT:
        if parked is not None:
            return THROUGH_PORTAL if stage == PICK else TO_THE_FORTRESS
        if stage == OUT:
            return TO_THE_FORTRESS
        return THROUGH_PORTAL if stage == RETURN else None
    if area in ANDARIEL.levels:
        if parked is not None and (stage != PICK or loop.fresh):
            return SWAP_BACK
        if parked is None and loop.swap_due and loop.swap != game and loop.kind.swaps_gheeds:
            return SWAP_OUT
    return None


def andariel_leg(world: World, progress: Progress | None, loop: Loop) -> str:
    """Andariel's legs out of the Fortress (`next_leg`): from the Rogue Encampment the waypoint to Catacombs Level 2, or
    to the Fortress first when a trade session is due there (the player, 2026-10-18: "inventory management and trading
    - same as LK"); down Levels 2 and 3; on Level 4 her fight, the loot, Save and Exit there."""
    player = world.player
    assert player is not None
    game = world.game_name
    if player.area == PANDEMONIUM_FORTRESS:
        return TO_THE_ENCAMPMENT if loop.tripping(game) else TO_THE_CATACOMBS
    if player.area == ROGUE_ENCAMPMENT:
        if loop.done == game:
            return LEAVE
        if loop.tripping(game):
            # On a trip for room: the Fortress's session, then back through the portal to the level
            return TO_THE_FORTRESS if loop.fortressed != game else THROUGH_PORTAL
        cramped = loop.free is not None and loop.free < TRADE_ROOM
        # The Fortress's errands (`next_leg`): the room low with anything a session can take, keys or scrolls short,
        # the staff to repair
        if (cramped and loop.carrying) or loop.short or loop.repair:
            return TO_THE_FORTRESS
        return TO_THE_CATACOMBS
    if (
        loop.trip_due
        and not loop.tripping(game)
        and loop.trips_in(game) < TRIPS_A_GAME
        and player.area in ANDARIEL.levels
    ):
        return TRIP  # several a game (`Loop.may_trip`, the runner's rule): none while one is on its way
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


# Each kind's legs out of the trade's reach (`next_leg`); a terror zone kind's are the agenda's (`Kind.agenda`)
LEGS = {LK.key: lk_leg, ANDARIEL.key: andariel_leg}


def _named(item: Carried) -> str:
    from inventory_tracking.items.metadata import metadata  # late: only the log's

    base = metadata()['bases'].get(str(item.txt))
    return base['name'] if base is not None else f'item {item.txt}'
