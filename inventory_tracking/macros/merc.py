"""The mercenary lost, or the belt low on healing potions: a town trip at the first safe moment.

The player, 2026-10-21 ~19:00: "also, we have lost merc -> probably better retreat to the town and refill hp potions in
the belt". At 18:55:55 that day the merc died to a tier 5 Herald pack in Worldstone Keep 1 and the loop fought on for
three minutes with no merc and the belt short (rca/2026-10-21/merc-lost-findings.md).

- `MercWatch` reads the merc from the service's own full looks (runner.py `_merc_poll`, every LOOK_SECONDS): lost when
  no merc of the character's is alive for CORPSE_HOLD s with its corpse read (its unit in `World.dead`: a direct read of
  the death), or for ABSENT_HOLD s with none read at all; one look with it alive clears it. `make osd` logs a single
  "Mercenary sample: None" now and then in normal play: one look never makes it lost.
- The belt: under BELT_LOW healing potions (one column's worth) for BELT_HOLD s, BELT_HOLD_DANGER s with a dangerous
  pack near (`dangerous`); after the trip the run goes back through the portal and the level's run takes up the pack
  the terror tracker remembers (its leaders: hunting/choice.py `agenda_target`, terror/tracker.py `remembered`).
- The trip waits for a safe moment (`MercWatch.moment`): no hostile within SIGHT, or, after SAFE_WAIT s, the life over
  SAFE_LIFE and none within SAFE_NEAR. The hunt's own safety retreats meanwhile; no Town Portal under hostiles in reach.
- `merc_package`: the room package as it is (the shared town visit: identify, stash, junk sold, Jamella's keys and
  healing potions, the cube emptied), then Tyrael's revive, back through the same portal, the same level's run on. The
  level's sightings are the runner's: they survive the trip.
- `town_routine` pays with the carried gold only (skill rule 3): the revive costs at most COST_MOST, and the game takes
  what the carried gold does not cover from the stash's (D2MOO SUnitNpc.cpp D2GAME_NPC_ResurrectMerc), so no revive is
  clicked unless the carried gold covers its cost; the stash's gold is read before and after, and a drop turns revives
  off for good (STASH_TOUCHED), as repair.py's.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.config import BELT
from inventory_tracking.game.records import Monster, World
from inventory_tracking.macros import repair, shop
from inventory_tracking.macros.actuator import Abort, Cancelled, Hand
from inventory_tracking.macros.agenda import PANDEMONIUM_FORTRESS, STACK, TOWN_ROUTINE, Objective, room_package
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.hunting.base import SIGHT, hostiles
from inventory_tracking.macros.routines import DEAD
from inventory_tracking.macros.shop import _close
from inventory_tracking.macros.waypoint import travel
from inventory_tracking.models import PotionType
from inventory_tracking.native.layout import BELT_COLUMNS, BELT_SIZE, DEAD_MODES
from inventory_tracking.tracking.belt import potion_kind


__all__ = [
    'BELT_EMPTY_TRIP',
    'MERC_LOST_TRIP',
    'MERC_REVIVE',
    'MERC_ROUTINE',
    'MERC_TRIP',
    'MercWatch',
    'merc_package',
    'owned_merc',
    'revive_after_visit',
    'revive_cost',
    'town_routine',
]

# The player, 2026-10-21 ~19:00: "also, we have lost merc -> probably better retreat to the town and refill hp potions
# in the belt". False: the merc's death is not looked for, as before (the loop fights on without it)
MERC_LOST_TRIP = True
# The trip's revive at Tyrael (the same ruling). False: the trip refills the belt only
MERC_REVIVE = True
# MERC_AT_ANY_VISIT (2026-10-23, the cyberg46 shard game: the merc died at 04:35:43 past its game's TRIPS_A_GAME and
# stayed dead; the visits for room and the belt at 04:54 and after passed Tyrael by, "no mana for Teleport" 199 times
# from 04:37). True: a shared town visit in the Fortress ends with a dead merc revived (`revive`, the carried gold),
# once a visit; it makes no trip of its own, so TRIPS_A_GAME's ping-pong cannot come back. A game whose revive failed
# (UNREVIVED) is not tried again. Not bound to a merc seen alive in this service (LEVELS): a restart forgets that
# (05:11 restart, the merc dead since 04:35). False: only a merc trip revives, as before.
MERC_AT_ANY_VISIT = True
# The same ruling, the belt's half; the player, 2026-10-21 ~20:00: "actually, we shouldn't get to the no hp potions and
# just 2 rejuv potions. - restock hp potions in the down, we may need several tries to kill especially nasty pack ... we
# must have top priority to no die ourselves and prevent loosing experience": the belt LOW on healing potions
# (BELT_LOW) is a trip at the first safe moment, sooner with a dangerous pack near. Before it the loop only warned
# ("potion stock: no healing potion on the belt", hunt.py `sense`) and took potions off the ground (supply.py);
# Jamella's potions came only with a town visit for room. False: no trip for the belt
BELT_EMPTY_TRIP = True

# monstats.txt rows whose AI is Hireable (pricing/raw/game-excel/monstats.txt *hcIdx, 2026-10-21; hireling.txt Class
# in third-parties/d2data json/hireling.json): roguehire, act2hire, act3hire, act5hire1, act5hire2
HIRELINGS = frozenset((271, 338, 359, 560, 561))
# Who revives a merc in each town (levels.txt: each act's first level). Acts 1, 2, 3, 5: hireling.txt `Seller`
# (d2data hireling.json: 150 kashya, 198 greiz, 252 asheara, 515 qual-kehk, as monstats.txt names them); act 4 has no
# hireling row: Tyrael (367 tyrael2) revives there (D2MOO SUnitNpc.cpp D2GAME_NPC_ResurrectMerc: Kashya, Greiz,
# Asheara, Tyrael2, Qual-Kehk). The trip goes to the Fortress from every act (`merc_package`), so only Tyrael is
# visited today; the others are for a revive in the act's own town
REVIVERS = {1: 150, 40: 198, 75: 252, 103: 367, 109: 515}
TYRAEL = REVIVERS[PANDEMONIUM_FORTRESS]
# Where Tyrael stands in the Fortress (NpcStationary in monstats.txt): the take 20261021T153936Z-103 read him at
# (5020, 5020) in every frame, by Cain at (5024, 5026). His place when he is out of the units' reach
TYRAEL_PLACE = (5020.0, 5020.0)
# The revive's cost: min(COST_MOST, merc level squared x 15 / 2) (hireling.txt resurrectcostmultiplier 15,
# resurrectcostdivisor 2, resurrectcostmax 50000 in every row; D2MOO Monsters.cpp MONSTERS_GetHirelingResurrectionCost).
# The player's merc was level 95 on 2026-10-21 (stat 12 in the take 20261021T155355Z-128): 50000
COST_MULTIPLIER, COST_DIVISOR, COST_MOST = 15, 2, 50_000
LEVEL_STAT = 12  # itemstatcost.txt `level`

LOOK_SECONDS = 2.0  # the service's own merc look (runner.py `_merc_poll`): a full read, so not at every poll
# Seconds the merc is lost for before it counts: its corpse read (mode 0 then 12 from 18:55:54, in the unit table to
# the take's end), or nothing of it read at all. osd.log has single "Mercenary sample: None" in normal play (18:53:00,
# 18:53:05, 18:53:37 on 2026-10-21, each followed by a sample 0.2 s later): no one look counts
CORPSE_HOLD = 3.0
ABSENT_HOLD = 10.0
# The belt's low mark: under one column's worth of healing potions. The belt is 4 columns of BELT_SIZE / BELT_COLUMNS
# = 4 rows (native/layout.py), two of them healing columns (config.py BELT.layout: rejuvenation, rejuvenation, healing,
# healing; the player, 2026-10-13), so 8 healing potions at most and the trip under 4. The healer gave the merc three
# in 7 s at 18:55:44-18:55:51 on 2026-10-21 (osd.log): under a column is one such burst from empty
BELT_ROWS = BELT_SIZE // BELT_COLUMNS
HEALING_CAPACITY = BELT_ROWS * (
    sum(1 for kind in BELT.layout if kind is PotionType.HEALING) if BELT.layout is not None else BELT_COLUMNS // 2
)
BELT_LOW = BELT_ROWS
BELT_HOLD = 6.0  # seconds the belt reads low before its trip comes due (a potion off the ground ends it)
BELT_HOLD_DANGER = 2.0  # ... with a dangerous pack near: life first
REFILLED = BELT_LOW  # healing potions on the belt that call the belt's trip off before it is made (off the ground)
DANGEROUS_PACK = 4  # hostiles within SIGHT that make a fight dangerous; a leader or Herald alone
# The safe moment (`moment`): none within SIGHT; or, SAFE_WAIT s after the trip came due, the life over SAFE_LIFE of
# its most and no hostile within SAFE_NEAR units (a Town Portal's cast and the step into it, ~1 s)
SAFE_WAIT = 15.0
SAFE_WAIT_DANGER = 5.0  # the belt low, a dangerous pack near: the portal sooner ("top priority to no die ourselves")
SAFE_LIFE = 0.6
SAFE_NEAR = 12.0
# The merc's and the belt's trips in one game, together: "we may need several tries to kill especially nasty pack" (the
# player, 2026-10-21 ~20:00). loop.py MERC_TRIPS bounds the trips' legs with it (a test holds them equal). A belt trip
# only after one that bought healing potions (`NO_POTIONS`)
TRIPS_A_GAME = 4
# 2026-10-22 (rca/2026-10-22/belt-refill-findings.md): a shard game runs hours over several acts (cyberg65: 18:58 to
# past 23:15) and its merc drinks a belt's worth in one burst; with TRIPS_A_GAME made it was never refilled again
# ("an empty belt = defect", "top priority to no die ourselves"). On: past TRIPS_A_GAME a belt trip is still made while
# the last trip's visit put healing potions on the belt (`Trips.may`, as loop.py TRIPS_BY_GAIN for room); one that put
# none ends them (the ping-pong the cap was for). The count is in the game's record (macros/midgame.py), so a restart
# neither resets nor loses it. False: TRIPS_A_GAME caps them
BELT_TRIPS_BY_GAIN = True

# The package's routine (agenda goal kind) and its leg (tzloop.py LEGS: `Loop: game N, merc trip`)
MERC_ROUTINE = 'merc routine'
MERC_TRIP = 'merc trip'
WHY_MERC, WHY_BELT = 'the merc lost', 'healing potions low on the belt'

HIS_SEEN = (0.1, 0.9, 0.42, 0.8)  # window fractions Tyrael is walked to be drawn within: his menu is drawn over him
REVIVE_SECONDS = 2.0  # for the merc to show alive after the Resurrect line's click
LOADING_SECONDS = 8.0  # for a level loaded after a click that took the character away (Travel to Harrogath)
STASH_TOUCHED = Path(__file__).resolve().parents[1] / 'runs' / 'alt-d' / 'revive-touched-stash.txt'
# The merc's level by character name, from its last look alive (`MercWatch.see`): the revive's cost
LEVELS: dict[str, int] = {}
# The games a trip came back from with the merc still dead (`town_routine`): no merc trip again in them
UNREVIVED: set[str] = set()
# The games whose last trip bought no healing potion (the carried gold under the reserve, her window shut): no belt trip
# again in them, a merc trip still
NO_POTIONS: set[str] = set()


@dataclass
class Trips:
    """The merc's and the belt's trips made in `game`: how many, the healing potions on the belt when the last was
    pushed and what its visit put on (None: not back yet, or unread). One object, the loop's (loop.py
    `Loop.merc_trips`), changed in place: the service's watch (`MercWatch.book`) counts them, the trip's routine
    (`town_routine`) writes the gain, the game's record keeps them over a restart (`state`, `take_up`)."""

    game: str | None = None
    made: int = 0
    belt: int | None = None
    gained: int | None = None

    def begin(self, game: str | None) -> None:
        """Another game: none made in it."""
        self.game, self.made, self.belt, self.gained = game, 0, None, None

    def pushed(self, healing: int | None) -> None:
        """A trip pushed with `healing` potions on the belt."""
        self.made, self.belt, self.gained = self.made + 1, healing, None

    def back(self, healing: int | None) -> None:
        """The trip's visit done with `healing` potions on the belt: what it put on (None when either is unread)."""
        self.gained = healing - self.belt if healing is not None and self.belt is not None else None

    def may(self, why: str | None) -> bool:
        """Whether a trip for `why` may be made: under TRIPS_A_GAME; past it (BELT_TRIPS_BY_GAIN) only the belt's, and
        only while the last trip put healing potions on the belt."""
        if self.made < TRIPS_A_GAME:
            return True
        return BELT_TRIPS_BY_GAIN and why == WHY_BELT and self.gained is not None and self.gained > 0

    def past_cap(self) -> int:
        """The trips made past TRIPS_A_GAME (loop.py `Loop.count`: the legs a trip makes count them too)."""
        return max(0, self.made - TRIPS_A_GAME)

    def state(self) -> dict:
        return {'made': self.made, 'belt': self.belt, 'gained': self.gained}

    def take_up(self, game: str, state: object) -> None:
        """`state` (`state`) of `game` from the game's record; a malformed one leaves these as they are."""
        if not isinstance(state, dict):
            return
        try:
            made = int(state.get('made') or 0)
            belt, gained = state.get('belt'), state.get('gained')
            belt = int(belt) if belt is not None else None
            gained = int(gained) if gained is not None else None
        except TypeError, ValueError:
            return
        self.game, self.made, self.belt, self.gained = game, made, belt, gained


def revive_cost(level: int | None) -> int:
    """The gold the revive of a merc of `level` costs; COST_MOST, the most it can, with the level unread."""
    if not level:
        return COST_MOST
    return min(COST_MOST, COST_MULTIPLIER * level * level // COST_DIVISOR)


def owned_merc(world: World) -> Monster | None:
    """The character's merc alive in the look: a hireling it owns, not dying or dead; None with none."""
    player = world.player
    if player is None:
        return None
    return next(
        (m for m in world.monsters if m.txt_id in HIRELINGS and m.owner == player.unit_id and m.mode not in DEAD_MODES),
        None,
    )


def healing_on_belt(belt: tuple[int | None, ...] | None) -> int | None:
    """Healing potions on the belt (its cells' item classes); None unread."""
    if belt is None:
        return None
    return sum(1 for cell in belt if potion_kind(cell) is PotionType.HEALING)


def dangerous(world: World) -> bool:
    """Whether the fight is against a dangerous pack: DANGEROUS_PACK hostiles within SIGHT, or a leader or a Herald."""
    near = near_hostiles(world, SIGHT)
    return len(near) >= DANGEROUS_PACK or any(m.leader or m.tier for m in near)


def near_hostiles(world: World, reach: float) -> list[Monster]:
    player = world.player
    if player is None:
        return []
    return [m for m in hostiles(world) if math.dist((m.x, m.y), (player.x, player.y)) <= reach]


@dataclass
class MercWatch:
    """What the service's merc looks say, for one game at a time (`see`), and the trip they make due."""

    had: set[str] = field(default_factory=set)  # characters seen with a merc alive since the service started
    game: str | None = None
    unit: int | None = None  # the merc's unit id in this game
    gone: float | None = None  # the first look of this absence
    corpse: bool = False  # its corpse read in this absence
    empty: float | None = None  # the first look with the belt under BELT_LOW healing potions
    due: str | None = None  # the trip due (WHY_MERC, WHY_BELT), its clock
    due_at: float = 0.0
    said: str | None = None  # the wait for a safe moment, said once a trip
    book: Trips = field(default_factory=Trips)  # the trips made in `game` (the loop's, runner.py)
    healing: int | None = None  # healing potions on the belt at the last look
    looked_at: float = -math.inf

    @property
    def trips(self) -> int:
        """The trips made in `game`."""
        return self.book.made if self.book.game == self.game else 0

    def see(
        self, world: World, belt: tuple[int | None, ...] | None, now: float, level: int | None = None
    ) -> str | None:
        """One look (a full read: monsters and corpses, `belt` its cells); the trip due now, None with none."""
        player = world.player
        if not world.in_game or player is None:
            return self.due  # a loading screen: no look
        if world.game_name != self.game:
            self.game, self.unit, self.gone, self.corpse, self.empty = world.game_name, None, None, False, None
            self.due, self.said = None, None
        if self.book.game != world.game_name:
            self.book.begin(world.game_name)  # in place: the loop's record holds the same object
        merc = owned_merc(world)
        if merc is not None:
            self.had.add(player.name)
            self.unit, self.gone, self.corpse = merc.unit_id, None, False
            if level:
                LEVELS[player.name] = level
            if self.due == WHY_MERC:
                self.due = None
                LOG.info('Macro: merc: alive again before the trip: no trip for it')
        elif player.name in self.had and not player.in_town:
            self.gone = now if self.gone is None else self.gone
            self.corpse = self.corpse or (self.unit is not None and self.unit in world.dead)
        self._belt(world, belt, now)
        if MERC_LOST_TRIP and self.due is None and self.lost(now) and world.game_name not in UNREVIVED:
            self.due, self.due_at = WHY_MERC, now
            LOG.info('Macro: merc: dead: %s for %.0f s%s', 'its corpse read' if self.corpse else 'no merc read',
                     now - (self.gone or now), f' (unit {self.unit})' if self.unit is not None else '')  # fmt: skip
        if not self.book.may(self.due):
            return None
        return self.due

    def _belt(self, world: World, belt: tuple[int | None, ...] | None, now: float) -> None:
        healing = healing_on_belt(belt)
        player = world.player
        if healing is None or player is None or player.in_town:
            return
        self.healing = healing
        if self.due == WHY_BELT and healing >= REFILLED:
            self.due, self.empty = None, None
            LOG.info('Macro: belt: %d healing potions on it again before the trip: no trip for it', healing)
            return
        if healing >= BELT_LOW:
            self.empty = None
            return
        self.empty = now if self.empty is None else self.empty
        hold = BELT_HOLD_DANGER if dangerous(world) else BELT_HOLD
        if BELT_EMPTY_TRIP and self.due is None and now - self.empty >= hold and world.game_name not in NO_POTIONS:
            self.due, self.due_at = WHY_BELT, now
            LOG.info('Macro: belt: %d healing potions of %d for %.0f s: a trip to refill it', healing,
                     HEALING_CAPACITY, now - self.empty)  # fmt: skip

    def lost(self, now: float) -> bool:
        """Whether the merc reads lost: gone CORPSE_HOLD s with its corpse read, ABSENT_HOLD s with none."""
        if self.gone is None:
            return False
        return now - self.gone >= (CORPSE_HOLD if self.corpse else ABSENT_HOLD)

    def moment(self, world: World, life: tuple[int, int] | None, now: float) -> str | None:
        """Why now is a safe moment for the Town Portal, None while it is not (`said` once)."""
        player = world.player
        if player is None or player.mode in DEAD or player.in_town or world.open_panels:
            return None
        if not near_hostiles(world, SIGHT):
            return f'no hostile within {SIGHT:.0f}'
        waited = now - self.due_at
        share = life[0] / life[1] if life is not None and life[1] > 0 else 0.0
        wait = SAFE_WAIT_DANGER if self.due == WHY_BELT and dangerous(world) else SAFE_WAIT
        if waited >= wait and share >= SAFE_LIFE and not near_hostiles(world, SAFE_NEAR):
            return f'{waited:.0f} s waited, life {share:.0%}, no hostile within {SAFE_NEAR:.0f}'
        if self.said != self.due:
            self.said = self.due
            LOG.info('Macro: %s: the town trip waits for a safe moment (hostiles within %.0f)',
                     'merc lost' if self.due == WHY_MERC else 'belt low', SIGHT)  # fmt: skip
        return None

    def tripped(self) -> None:
        """The trip is pushed: counted for the game, with the belt's healing potions then."""
        self.book.pushed(self.healing)
        self.due, self.empty, self.said = None, None, None


def merc_package(area: int) -> tuple[Objective, ...]:
    """The trip from field level `area`: the room package as it is (agenda.py `room_package`: Town Portal, the
    Fortress, the shared town visit, back through the same portal, the run on), the revive (`town_routine`) after the
    visit. The player, 2026-10-21 ~20:36: "every time we visit town and traders - we need to to the routine => get back
    with clear cube and clear inventory space"; "do not invent any IFs here: reuse routines". The belt is filled by
    the visit's own Jamella stop, every visit ("hp refill is just an another step in routine": visit.py
    POTIONS_WALK)."""
    goals = list(room_package(area))
    after = next(index for index, goal in enumerate(goals) if goal.kind == TOWN_ROUTINE) + 1
    goals.insert(after, Objective(MERC_ROUTINE, 'the merc revived', STACK))
    return tuple(goals)


def town_routine(run: Run, trips: Trips | None = None) -> None:
    """MERC_ROUTINE in the Fortress, after the visit: the merc revived at Tyrael when it is dead and the carried gold
    covers the cost. A belt still low after the visit ends the belt's trips for the game (`NO_POTIONS`). `trips`: the
    game's (`Trips`), told what the visit put on the belt (BELT_TRIPS_BY_GAIN)."""
    world = run.world()
    player = world.player
    if player is None:
        raise Abort('no character read for the merc trip')
    healing = belt_healing(run)
    if trips is not None and trips.game == world.game_name:
        trips.back(healing)
        LOG.info('Macro: merc trip %d: %s healing potions on the belt, %s before the trip: %s put on', trips.made,
                 healing, trips.belt, trips.gained)  # fmt: skip
    if healing is None or healing < BELT_LOW:
        NO_POTIONS.add(world.game_name)
        LOG.info('Macro: merc trip: %s healing potions on the belt after the visit: no belt trip again in this game',
                 healing)  # fmt: skip
    if owned_merc(world) is not None:
        LOG.info('Macro: merc trip: the merc is alive: no revive')
    elif not revive(run, player.name):
        UNREVIVED.add(world.game_name)  # no merc trip again in this game: the belt's may still come


def revive_after_visit(run: Run) -> bool:
    """MERC_AT_ANY_VISIT: a dead merc revived at the end of a visit in the Fortress; whether a revive was tried."""
    if not MERC_AT_ANY_VISIT:
        return False
    world = run.world()
    player = world.player
    if (
        player is None
        or player.area != PANDEMONIUM_FORTRESS
        or owned_merc(world) is not None
        or world.game_name in UNREVIVED
    ):
        return False
    LOG.info("Macro: merc: dead at the visit's end: revived at Tyrael on the way (MERC_AT_ANY_VISIT)")
    if not revive(run, player.name):
        UNREVIVED.add(world.game_name)
    return True


def belt_healing(run: Run) -> int | None:
    """Healing potions on the belt as the run reads it now; None unread."""
    loot = run.reads.loot()
    return healing_on_belt(loot.belt) if loot is not None and loot.belt_read else None


def revive(run: Run, name: str) -> bool:
    """The merc revived at Tyrael with the carried gold (MERC_REVIVE); whether it is alive after."""
    if not MERC_REVIVE:
        LOG.info('Macro: merc: not revived: MERC_REVIVE is off')
        return False
    if STASH_TOUCHED.exists():
        LOG.info('Macro: merc: not revived: a revive took the stash gold before (%s)', STASH_TOUCHED)
        return False
    coins, bank, cost = repair.gold(run), repair.gold(run, repair.GOLDBANK), revive_cost(LEVELS.get(name))
    level = LEVELS.get(name)
    if coins is None or coins < cost:
        LOG.info('Macro: merc: carried gold %s does not cover the revive (%d for level %s): the belt refilled only, '
                 'the merc not revived', coins, cost, level if level is not None else 'unread')  # fmt: skip
        return False
    try:
        back = resurrect(run)
    except Cancelled, Hand:
        raise
    except LeftFortress as stop:
        LOG.info('Macro: merc: the click took the character out of the Fortress: revive given up for this game (%s)',
                 stop)  # fmt: skip
        back_to_fortress(run)
        back = False
    except Abort as stop:
        LOG.info('Macro: merc: not revived: %s', stop)
        back = False
    left, banked = repair.gold(run), repair.gold(run, repair.GOLDBANK)
    if bank is not None and banked is not None and banked < bank:
        STASH_TOUCHED.write_text(f'{bank} -> {banked}\n')
        LOG.error('Macro: merc: the stash gold went %d -> %d at the revive: revives are off for good (%s)', bank,
                  banked, STASH_TOUCHED)  # fmt: skip
    if back:
        LOG.info('Macro: merc: revived at Tyrael for %s gold (carried %s -> %s, %d expected)',
                 coins - left if left is not None else '?', coins, left, cost)  # fmt: skip
    else:
        LOG.info('Macro: merc: not revived at Tyrael (carried gold %s -> %s)', coins, left)
    return back


def back_to_fortress(run: Run) -> None:
    """The waypoint back to the Fortress after a click took the character away: the package's next goals (the
    waypoint to the portal's town, through the portal) start from there, as they would have."""
    world = run.world()
    if world.player is None or world.player.area == PANDEMONIUM_FORTRESS:
        return
    try:
        travel(run, PANDEMONIUM_FORTRESS)
    except Cancelled, Hand:
        raise
    except Abort as stop:
        LOG.info('Macro: merc: no waypoint back to the Fortress (%s): the trip goes on from level %d', stop,
                 world.player.area)  # fmt: skip


def lifts() -> tuple[float, ...]:
    """Lifts over Tyrael's drawn point to click Resurrect at: the learned one (shop.py `known`), then 0.16 up by half a
    line, nearest the learned one first (as cain.py `lifts`)."""
    scan = tuple(0.16 + step * shop.LINE / 2 for step in range(14))
    learned_lift = shop.known(TYRAEL)
    if learned_lift:
        scan = tuple(sorted(scan, key=lambda lift: abs(lift - learned_lift)))
    return tuple(dict.fromkeys(round(lift, 4) for lift in ((learned_lift,) if learned_lift else ()) + scan))


class LeftFortress(Abort):
    """A line clicked over Tyrael took the character out of the Fortress (his "Travel to Harrogath", for a character
    past act 4): the revive is given up there (`resurrect`)."""


def took_revive(run: Run) -> bool:
    """After a click on a line over Tyrael: whether the merc shows alive within REVIVE_SECONDS. `LeftFortress` the
    moment the character reads in another level, or loading one (the coordinator, 2026-10-21: his menu may hold
    "Travel to Harrogath" beside Talk and Cancel, and the scan of lifts could click it)."""
    seen = run.seen(
        lambda w: w.player is None or w.player.area != PANDEMONIUM_FORTRESS or owned_merc(w) is not None,
        REVIVE_SECONDS,
    )
    if seen is not None and seen.player is None:
        seen = run.seen(lambda w: w.player is not None, LOADING_SECONDS) or run.world()
    if seen is not None and seen.player is not None and seen.player.area != PANDEMONIUM_FORTRESS:
        raise LeftFortress(f'the click took the character to level {seen.player.area}')
    return seen is not None and owned_merc(seen) is not None


def resurrect(run: Run) -> bool:
    """Tyrael's Resurrect line clicked (shop.py `menu_line`, every vendor's line) until the merc shows alive; whether
    it did. Mouse mode only. `Abort` when he is not found; `LeftFortress` when a click took the character away (no
    other line is clicked then). A miss's menu is closed by `menu_line` and opened again by a click on him, as Cain's
    Talk misses are (cain.py): a Talk click's dialogue ends there too."""
    if run.pad is not None:
        raise Abort('the revive needs mouse mode')
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        raise Abort('no game window')
    aspect = rect[2] / rect[3]
    run.say('Merc: revive at Tyrael')
    with shop.serving(TYRAEL):

        def place(world: World) -> tuple[float, float] | None:
            return shop.whereabouts(world) or TYRAEL_PLACE

        shop.walk_until(run, place, HIS_SEEN, 'Tyrael')
        run.seen(lambda w: w.player is not None and w.player.mode not in shop.WALKING, shop.WALK_SECONDS)
        try:
            shop.menu_line(run, aspect, 'Resurrect', lifts(), lambda _lift: took_revive(run), picture=True)
        except LeftFortress:
            raise
        except Abort:
            return False
        finally:
            _close(run)
    return True


def trip(push: Callable[..., None], area: int, why: str, moment: str) -> None:
    """The trip's package pushed (`push`: the loop's agenda's), said at the safe `moment`: the watch tools read the
    line (d2-loop-watch logwords.py EVENT, NOW)."""
    if why == WHY_MERC:
        LOG.info('Macro: merc lost: a town trip to refill the belt and revive the merc (%s)', moment)
    else:
        LOG.info('Macro: belt low: a town trip to refill the belt (%s; %s)', why, moment)
    push(*merc_package(area))
