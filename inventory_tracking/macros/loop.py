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
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import NamedTuple

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Carried, Pack, World
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
from inventory_tracking.native.layout import TOWN_IDS
from inventory_tracking.routes.model import FIGHT, LOOT, USE
from inventory_tracking.routes.progress import Progress
from inventory_tracking.terror.bosses import KILLED_AT


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
    'LegHands',
    'Loop',
    'kind_of',
    'next_leg',
]

KURAST_DOCKS, LOWER_KURAST, PANDEMONIUM_FORTRESS = 75, 79, 103
ROGUE_ENCAMPMENT, CATACOMBS_2, CATACOMBS_3, CATACOMBS_4 = 1, 35, 36, 37  # levels.txt


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
    trips: bool = False  # no room for a valuable: a trip to town and back (macros/stops.py)
    swaps_gheeds: bool = False  # the Gheed's swap (macros/charms.py)
    boss: str | None = None  # whose drops may still be landing at PICK_UP (`KILLED_AT`)
    badge: bool = True  # the HUD's badge names the kind (runner.py `run_badge`)
    fortress_ends_game: bool = False  # leaving its level for the Fortress ends the game (`done`)
    full_clear: bool = False  # every hostile, every room: the Herald hunt (macros/tzloop.py `full_clear`)


LK = Kind(
    'lk', 'Lower Kurast', LOWER_KURAST, frozenset((LOWER_KURAST,)), KURAST_DOCKS, KEYS_WANTED, 'chests opened an hour',
    badge=False, fortress_ends_game=True,
)  # fmt: skip
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
)
KINDS = {kind.key: kind for kind in (LK, ANDARIEL)}
# The terror zone kinds (macros/goals-plan.md): goals from the agenda (tzloop.py), offered only with tzloop.ENABLED
FIELD = frozenset(range(137)) - {ROGUE_ENCAMPMENT, 40, KURAST_DOCKS, PANDEMONIUM_FORTRESS, 109}
TZ_GAME_SECONDS = 1200.0
TZ = Kind(
    'tz', 'TZ leveling', 0, FIELD, PANDEMONIUM_FORTRESS, metric='elite kills an hour', game_seconds=TZ_GAME_SECONDS,
    agenda=True,
)  # fmt: skip
# The Herald hunt's measure is not ruled yet (goals-plan.md open question 8)
TZ_CLEAR = replace(TZ, key='tzclear', name='Full clear TZ', metric='Herald and elite kills an hour', full_clear=True)
TZ_KINDS = frozenset((TZ.key, TZ_CLEAR.key))


def loop_kinds() -> dict[str, Kind]:
    """The kinds the player may choose (KP_6 three times, restart.py --kind); TZ kinds only with tzloop.ENABLED."""
    from inventory_tracking.macros import tzloop  # late: tzloop imports this module

    return {**KINDS, **({TZ.key: TZ, TZ_CLEAR.key: TZ_CLEAR} if tzloop.ENABLED else {})}


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
# The Gheed's swap (macros/charms.py; the player, 2026-10-18: "put our own gheed into SHARED tab; go back and pick new
# one; go to town, identify; check what is better")
SWAP_OUT = "Gheed's Fortune away"
GHEED_STASH = "Gheed's Fortune onto a shared page"
SWAP_BACK = "Gheed's Fortunes to compare"
GHEED_CHOOSE = "the better Gheed's Fortune"
# `Loop.gheed`, the swap's stage
OUT, PICK, CHOOSE, RETURN = 'out', 'pick', 'choose', 'return'
# Trips for room a game (`Loop.may_trip`; the player, 2026-10-18: "one game can do several trips to the town"), each
# after one that made room. Three: two were needed once in 173 cycles (2026-10-18); a trip is ~37 s
TRIPS_A_GAME = 3
# How often one leg may be made in one game before the loop gives up on it (default REPEAT).
REPEATS = {PICK_UP: 20, CHESTS: 3, DOWN: 12, FIGHT_ANDARIEL: 3}  # DOWN: the pickups at the stairs too
# Each trip and the swap (twice) go to the Fortress and back; once more at an Andariel game's start
REPEATS |= {
    TRIP: TRIPS_A_GAME,
    TO_THE_FORTRESS: 1 + TRIPS_A_GAME + 2,
    TO_THE_ENCAMPMENT: TRIPS_A_GAME + 2,
    THROUGH_PORTAL: TRIPS_A_GAME + 2,
}
# A game's visits: the start's, each trip's, one cut by the player's hand
REPEATS |= {TOWN: 1 + TRIPS_A_GAME + 1}
# The terror zone kinds' legs (tzloop.py): each bound a game's worth (~8 excursions of up to 7 levels)
TZ_WAYPOINT, TZ_LEVEL, TZ_LOOT, TZ_PICKUP = 'TZ waypoint', 'TZ level', 'TZ loot', 'TZ pickup'
TZ_NEXT_LEVEL, TZ_PORTAL, TZ_BACK = 'TZ next level', 'TZ Town Portal', 'TZ back through the portal'
REPEATS |= {TZ_WAYPOINT: 12 + 2 * TRIPS_A_GAME, TZ_LEVEL: 40, TZ_LOOT: 20, TZ_PICKUP: 20, TZ_NEXT_LEVEL: 30}
REPEATS |= {TZ_PORTAL: 10 + TRIPS_A_GAME, TZ_BACK: 1 + TRIPS_A_GAME}
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
REPEAT = 2
FULL_FILE = 'full-stacks.json'
GAME_SECONDS = 240.0  # a game longer than this is left (games take 40-75 s, 2026-10-17)
# Added to GAME_SECONDS per trip for room (`overdue`): the trips' p90 (rca/2026-10-18/trips-and-towns-findings.md §2.4)
TRIP_SECONDS = 80.0
LOADING_SECONDS = 10.0  # for a game's character to be read after it shows as in a game
# A stand this long within STILL_UNITS is the loop stuck (the player, 2026-10-17: "we stuck, but didn't detect it in
# time"); the longest good stand is a shop visit, under 15 s
STILL_SECONDS = 45.0
STILL_UNITS = 2.0
RECOVERIES = 3
RECOVERY_SECONDS = 600.0
RECOVERY_PAUSE = 30.0  # past RECOVERIES in RECOVERY_SECONDS: a pause before the next leg, not a stop (`recover`)
# Standing outside a fight and losing BESET_LOSS of max life within BESET_SECONDS is beset (`beset`): the attacker is
# fought back (FIGHT_BACK; the player, 2026-10-19: "we stood still while under attack and almost died"); a hit there
# was 4-8 %
BESET_SECONDS = 4.0
BESET_LOSS = 0.05
# Beset again this soon after fighting back (`beset_again`): the fight cannot be won, the game is left (2026-10-19:
# a level run's fight takes 5-20 s, the loop's next legs a minute)
BESET_AGAIN_SECONDS = 60.0


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
    fight: Callable[[], None] | None = None
    fight_back: Callable[[], None] | None = None  # the level run posted against an attacker (FIGHT_BACK)
    left: Callable[[], str | None] | None = None
    sighted: Callable[[int | None], str | None] = lambda area: None
    terrorized: Callable[[int], bool | None] = lambda area: None
    navigate: Callable[[], None] = lambda: None


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
    fought: tuple[str, float] | None = None  # (game, run clock) at her level's first loot leg (`DROPS_LAND`)
    recovered: list[float] = field(default_factory=list)
    # Looks in a stand outside a fight (`beset`): (when, where, life, game)
    hurt: list[tuple[float, tuple[float, float], int, str]] = field(default_factory=list)
    # Beset (runner.py `_loop_stopped`): the game a fight back is due in, the game whose valuables are fetched after
    # it, and (game, when) of the fight back's last leg (`beset_again`)
    beset_due: str | None = None
    fetch_back: str | None = None
    fought_back: tuple[str, float] | None = None
    # (game or None for the lobby, since when) (`overdue`)
    seen: tuple[str | None, float] | None = None
    # The level card's marks by label, in tiles (levels/guide.py `marks`): a waypoint out of sight
    marks: Callable[[str], tuple[tuple[float, float], ...]] | None = None
    # Resource classes whose stash stack is at 99, kept in FULL_FILE (the player, 2026-10-17: "we better just sell
    # them"): not picked up, sold at Jamella (shop.py `restock`)
    full: set[int] = field(default_factory=set)
    # The staff's Teleport in the loop's moves while the gold pays for it (`teleports`); None: undecided
    teleports: bool | None = None
    wear: str = '?'  # the most worn item's durability at the last look, for the log
    # The last game looked at (`observe`): kept through the lobby and a KP_6 off and on
    game_id: GameId | None = None

    @property
    def sold_full(self) -> frozenset[int]:
        """The full stacks' classes not picked up (town.py `sold_full`): runes and materials, never gems or potions."""
        return sold_full(self.full)

    # A repair due (repair.py `wants`), and the game count of a visit that raised nothing (RETRY_GAMES)
    repair: bool = False
    repair_failed: int | None = None
    # No room for a valuable: the loop's items into the cube at the next leg, once a game (`room_tried`)
    make_room: bool = False
    room_tried: str | None = None
    # Then one of the loop's to-identify items dropped for the block (cube.py `drop_for`), once a game (`dropped`)
    drop_room: bool = False
    dropped: str | None = None
    # The trade (`TOWN`): cells free in inventory and cube, anything a visit takes away (`carrying`)
    free: int | None = None
    carrying: bool = False
    visiting: str | None = None
    visited: str | None = None
    waiting: bool = False  # for the game window's focus (runner.py): watchdogs pause
    moved: tuple[tuple[float, float], float] | None = None  # where the character last moved to, and when (`still`)
    moved_in: str | None = None  # the game `moved` was read in (`still`: a new game counts afresh)
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

    def start(self) -> None:
        self.full |= self._full_stored()
        self.on, self.made, self.own, self.abandon, self.seen, self.moved = True, Counter(), None, False, None, None
        self.counted_in, self.placed, self.portal, self.printed = None, False, None, None
        self.beset_due, self.fetch_back, self.fought_back = None, None, None

    def recover(self, why: object, now: float) -> bool:
        """Whether the loop goes on after `why` by leaving the game: always but dead. Past RECOVERIES within
        RECOVERY_SECONDS the next leg waits RECOVERY_PAUSE: a stopped loop stood until someone looked (2026-10-17)."""
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
        """Whether the loop has been in `game` (None: the lobby) over GAME_SECONDS plus TRIP_SECONDS a trip."""
        if self.seen is None or self.seen[0] != game:
            self.seen = (game, now)
            return False
        allowed = (self.kind.game_seconds or GAME_SECONDS) + TRIP_SECONDS * self.trips_in(game)
        return now - self.seen[1] > allowed and not self.abandon

    def still(self, where: tuple[float, float] | None, now: float, game: str | None = None) -> bool:
        """Whether the character has stood within STILL_UNITS over STILL_SECONDS in `game`. A new game counts afresh:
        every game starts at the same waypoint. `now`: time.monotonic()."""
        if where is None:
            return False
        cooling = now < self.cooling  # the recoveries' pause is the loop's own wait
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
        """Whether the character stood (STILL_UNITS) losing BESET_LOSS of max life within BESET_SECONDS. `life`:
        (points, maximum). Asked only outside a fight (runner.py `poll`); once, then afresh; never in town, the lobby or
        while leaving. `now`: time.monotonic()."""
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

    def beset_again(self, game: str | None, now: float) -> bool:
        """Whether a fight back's last leg in `game` was within BESET_AGAIN_SECONDS. `now`: time.monotonic()."""
        fought = self.fought_back
        return fought is not None and game is not None and fought[0] == game and now - fought[1] <= BESET_AGAIN_SECONDS

    def fight_back_due(self, game: str) -> None:
        """Beset in `game`: its next leg fights the attacker (FIGHT_BACK), the ones after fetch the valuables."""
        self.beset_due, self.fetch_back = game, None

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

    def players_item(self, item: Carried, stats: Mapping[int, int]) -> bool:
        """Whether `item` is the player's by its stats (volatile.py `prints`): never sold nor dropped."""
        from inventory_tracking.macros.volatile import is_players

        return self.store is not None and is_players(item, stats, self.volatile.prints(self.character))

    def visit_due(self, game: str) -> bool:
        """Whether a town visit is due in `game` (once): room low (or a trip) with anything to take away, or, except at
        a game's end, short stock or a repair. Any errand is the whole visit (the player, 2026-10-17)."""
        if self.visited == game:
            return False
        if self.visiting == game:
            return True  # cut short: made again from what is left
        cramped = self.tripping(game) or (self.free is not None and self.free < TRADE_ROOM)
        return (cramped and self.carrying) or (self.done != game and (self.short or self.repair))

    def tripping(self, game: str) -> bool:
        """Whether a trip for room is under way in `game` (begun, not back through the portal)."""
        return self.trip == game and self.returned != game

    def trips_in(self, game: str | None) -> int:
        """The trips for room made in `game`."""
        return self.trips if game is not None and self.trip == game else 0

    def may_trip(self, game: str | None) -> bool:
        """Whether another trip may be made in `game`: none under way, under TRIPS_A_GAME, and the last made room (or
        it is unread)."""
        made = self.trips_in(game)
        if made == 0:
            return True
        if made >= TRIPS_A_GAME or game is None or self.tripping(game):
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
        """A trip for room starts in `game` (TRIP, tzloop.py `trip`): counted, with its own Fortress, way back and visit
        (none of the game's earlier ones count for it)."""
        self.trips = self.trips_in(game) + 1
        self.trip_due, self.trip, self.fortressed = False, game, None
        self.trip_free, self.trip_gained = self.free, None
        self.returned = None
        self.visiting = self.visited = None

    def back_through_portal(self, run: Run, game: str) -> None:
        """Back through the portal (`portal_at`), a trip's end told first."""
        if self.tripping(game):
            self._back_from_trip()
        self.returned = game
        through_portal(run, self.portal_at)

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
        if self.made[where, leg] > REPEATS.get(leg, REPEAT):
            # Afresh after the Abort: the recovery makes the leg again (a count left over stopped each try, 2026-10-18)
            del self.made[where, leg]
            raise Abort(f'{leg} again and again in {where}: nothing came of it')

    def next_game(self, run: Run, world: World, key_names) -> None:
        """The NEXT_GAME leg: the next game made from the lobby, prebuffed in its town."""
        self.trip_due = self.swap_due = self.fresh = False
        self.gheed = None  # a parked Gheed's Fortune is fetched from the next game's town
        trace = create_next_game(run, world.game_name)
        run.keys = character_keys(run, key_names)
        now = run.world()
        try:
            # In town: Consume speeds the town walks (the player, 2026-10-18)
            prebuff(run, fresh=trace)
            self.prebuffed = now.game_name
        except Hand:
            raise
        except Abort as stop:
            if now.player is None or now.player.area != ROGUE_ENCAMPMENT:
                raise
            # Consume cannot take the Encampment's start NPCs (routines.py TOWN_NPCS): again on Catacombs 2 (`DOWN`)
            LOG.info('Macro: loop: the prebuff in the Rogue Encampment failed (%s): again on Catacombs 2', stop)

    def town(self, run: Run, visit: Callable[[Exit], object] | None, game: str, exit: Exit) -> None:
        """The TOWN leg: the town visit, ending by `exit`."""
        if visit is None:
            raise Abort('no town visit to make')
        self.visiting = game
        contract = visit(exit)
        self.visited = game
        self.repair = False
        # A keeper no stash page takes: the loop stops in town, not a recovery (the player, 2026-10-18: "if stash is
        # full - we need to stop loop")
        full = tuple(getattr(contract, 'stash_full', None) or ())
        if full:
            raise Abort(f'the stash is full: {", ".join(full)}', cause='stash')

    def leave(self, run: Run, game: str) -> None:
        """The LEAVE leg: Save and Exit, the game done and counted."""
        self.done = game
        leave_game(run)
        self.abandon = False
        self.games += 1

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
        identify, bring, left = hands.identify, hands.bring, hands.left
        world = run.world()
        if (cooling := self.cooling - time.monotonic()) > 0:
            # The recoveries' pause is stood only where nothing attacks (lobby, town); elsewhere the game is left first
            # (the player, 2026-10-19: "we stood still while under attack and almost died")
            if not world.in_game or (world.player is not None and world.player.in_town):
                run.pace.sleep(cooling)
                world = run.world()
            else:
                area = world.player.area if world.player is not None else 'an unread level'
                LOG.info('Macro: loop: the pause after recoveries (%.0f s) is not stood in level %s: the game is left '
                         'first', cooling, area)  # fmt: skip
        if world.in_game and world.player is None:
            # A game still loading: waited for, not a leg's stop
            world = run.seen(lambda w: w.player is not None or not w.in_game, LOADING_SECONDS) or run.world()
        self.observe(world)
        if not world.in_game:
            self.abandon = False  # left
        if not self.placed and not self.chosen and world.player is not None:
            # The kind by where the character stands; the shared Fortress keeps the chosen one
            self.placed = True
            found = kind_of(world.player.area)
            if found is not None and found != self.kind:
                LOG.info('Macro: loop: %s, by where the character is', found.name)
                self.kind = found
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
            # The player's items told first, so the first look counts the room too
            loose = frozenset(
                (i.txt, i.x, i.y) for i in pack.items if (not i.identified and i.quality >= MAGIC) or i.txt in RESOURCES
            )
            if self.store is not None:
                self.tell(pack, world.player.name, loose, item_stats)
            else:
                self.sort(own_of(pack.items), world.player.name, loose)  # no store (tests)
        items = loot(pack, self.own) if pack and self.own else []
        in_town = world.player is not None and world.player.area == PANDEMONIUM_FORTRESS
        if self.parked is not None and pack is not None:
            self.fresh = bool(candidates(pack, self.parked, self.swap_units))
        if pack is not None and self.own is not None:  # unread in the lobby: the last look's stands
            carried = [*items, *pack.in_cube]
            cube = roomed(pack).cube or ()
            in_inventory = INVENTORY_CELLS - sum(item.size[0] * item.size[1] for item in pack.items)
            in_cube = sum(row.count('.') for row in cube)
            self.free = in_inventory + in_cube  # the trade waits until both are full
            if in_inventory < TRADE_ROOM and overflow(pack, self.own):
                # Cube room in pieces no loop item fits is no room
                self.free = min(self.free, in_inventory)
            if not any(rows and Grid(rows).has_room(SURE_BLOCK) for rows in (pack.inventory, cube)):
                # No SURE_BLOCK free in either: no room, whatever the cell count
                self.free = min(self.free, TRADE_ROOM - 1)
            if in_town and self.free < TRADE_ROOM:
                LOG.info('Macro: loop: room low: %d cells free (inventory %d, cube %d, loop items %d in the inventory '
                         'and %d in the cube; cube rows %s)', self.free, in_inventory, in_cube, len(items),
                         len(pack.in_cube), '/'.join(cube))  # fmt: skip
            # A visit cannot take away a full gem stack's gems (kept, neither stashed nor sold)
            stuck = self.full - self.sold_full
            # ...but three of a kind are a transmute (cube.py `transmute`): a session's work
            cubable = Counter(i.txt for i in carried if i.txt in stuck and perfect_of(i.txt) not in (None, *self.full))
            self.carrying = (
                any(i.txt not in stuck for i in carried)
                or bool(surplus(carried, stuck))
                or any(count >= GEMS_A_KIND for count in cubable.values())
            )
            visiting = world.in_game and self.visiting == world.game_name and self.visited != world.game_name
            if in_town and in_inventory < TRADE_ROOM <= self.free and in_cube >= 3 and items and not visiting:
                # The loop's items into the cube for pickup room, between visits only (runner.py `make_room`)
                self.make_room = True
        staff = run.teleport() if world.in_game and run.teleport is not None else None
        # In a visit any missing charge is topped up (town.py `tops_up`), decided again at Halbu's (macros/visit.py)
        in_session = world.in_game and self.visiting == world.game_name
        topped = tops_up(staff, in_session, self.visited == world.game_name)
        # A worn item low on durability is a repair of its own
        wear = run.wear() if world.in_game and run.wear is not None else None
        self.wear = worn_text(wear)
        coins = gold(run) if (staff is not None and (wants(staff) or topped)) or worn_out(wear) else None
        self.repair = due(staff, wear, coins, top_up=topped, waited=self.repair_waited())
        goal = None
        if (beset := self.after_beset(world)) is not None:
            leg = beset  # before the kind's own legs: the attacker first, then its ground
        elif self.kind.agenda:
            from inventory_tracking.macros import tzloop  # late: tzloop imports this module

            goal = tzloop.choose(world, progress, self, hands)
            leg = tzloop.leg_of(goal)
        else:
            leg = next_leg(world, progress, self)
        game = world.game_name if world.in_game else ''
        self.count(world, leg)
        run.say(f'Loop: game {self.games + 1}, {leg}')
        if leg != NEXT_GAME:
            run.keys = character_keys(run, key_names)  # Swap Weapons among them (`arrived`)
        if goal is not None:
            from inventory_tracking.macros import tzloop

            tzloop.perform(self, run, key_names, progress, goal, hands)
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
        if leg in (TO_THE_CHESTS, TO_THE_CATACOMBS):
            # The carried gold, once a game (the player, 2026-10-17: "just use gold in the inventory")
            coins = gold(run)
            LOG.info('Macro: loop: gold carried %s, the most worn item %s', coins, self.wear)
            if not (run.own_teleport is not None and run.own_teleport()):
                # Own Teleport (Enigma) is in every move whatever the gold (runner.py LOOPED_TELEPORT)
                self.teleports = teleports(coins, gold_cap(run), self.teleports)
            if world.player is None or world.player.area != ROGUE_ENCAMPMENT:
                self.prebuff_once(run, game)
            travel(run, self.kind.start, self.marks)
        elif leg == CHESTS:
            level_run()
        elif leg == DOWN:
            if down is None:
                raise Abort('no level run to the stairs')
            self.prebuff_once(run, game)  # not cast in the Encampment (`next_game`)
            down()
        elif leg == FIGHT_ANDARIEL:
            if fight is None:
                raise Abort('no level run to fight with')
            fight()  # posts the run and returns; its end is PICK_UP's
        elif leg == PICK_UP:
            boss = self.kind.boss
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
            to_town(run, key_names)  # no pickup at the portal: no room
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
                # and by the level run, which gave it up (rca/2026-10-18/loop-robustness-findings.md §2.3)
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
                bring([new])  # Ctrl + click to the stash works from the inventory only
                after = run.reads.carried()
                new = next((i for i in after.items if i.unit_id == new.unit_id), None) if after is not None else None
            # Anything else picked up in the swap (runner.py `_gheeds_swap`) is in the player's cell: onto a shared page
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
                    self.done = game  # Save and Exit from here
                    LOG.info("Macro: charms: the level's loot is done: the game is left from town")
        elif leg == TO_THE_ENCAMPMENT:
            travel(run, ROGUE_ENCAMPMENT, self.marks)
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
            self.leave(run, game)
        return leg


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
    """Andariel's legs (`next_leg`): the Encampment's waypoint (the Fortress first for its errands), down Levels 2 and
    3, on Level 4 her fight, the loot, Save and Exit."""
    player = world.player
    assert player is not None
    game = world.game_name
    if player.area == PANDEMONIUM_FORTRESS:
        return TO_THE_ENCAMPMENT if loop.tripping(game) else TO_THE_CATACOMBS
    if player.area == ROGUE_ENCAMPMENT:
        if loop.done == game:
            return LEAVE
        if loop.tripping(game):
            return TO_THE_FORTRESS if loop.fortressed != game else THROUGH_PORTAL
        cramped = loop.free is not None and loop.free < TRADE_ROOM
        if (cramped and loop.carrying) or loop.short or loop.repair:
            return TO_THE_FORTRESS
        return TO_THE_CATACOMBS
    if player.in_town:
        return TO_THE_CATACOMBS  # any other town: its waypoint (as `lk_leg`)
    if (
        loop.trip_due
        and not loop.tripping(game)
        and loop.trips_in(game) < TRIPS_A_GAME
        and player.area in ANDARIEL.levels
    ):
        return TRIP  # several a game (`Loop.may_trip`)
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


# Each kind's legs outside the town visit (`next_leg`); the TZ kinds' are the agenda's
LEGS = {LK.key: lk_leg, ANDARIEL.key: andariel_leg}


def _named(item: Carried) -> str:
    from inventory_tracking.items.metadata import metadata  # late: only the log's

    base = metadata()['bases'].get(str(item.txt))
    return base['name'] if base is not None else f'item {item.txt}'
