"""The level run's goal: side drops, potions, the stand-by, chests, clearing the way, the agenda's targets,
passing and taking back. A part of macros/hunt.py `Hunter`, its methods bound there."""

import math
from collections.abc import Callable, Sequence
from dataclasses import replace
from typing import TYPE_CHECKING

from inventory_tracking.automation.priority import reserve
from inventory_tracking.combat import revivers
from inventory_tracking.combat.pack import PACK_SEEN
from inventory_tracking.combat.threats import manaburn
from inventory_tracking.common import LOG
from inventory_tracking.config import HEAL_PRIORITY
from inventory_tracking.game.layout import LYING_DEAD, NO_OWNER, STRIKING_MODES
from inventory_tracking.game.records import (
    GOLD,
    HEALING,
    REJUVENATION,
    VALUABLE,
    Drop,
    Loot,
    Monster,
    Thing,
    World,
    has_room,
)
from inventory_tracking.levels.exits import door_passage
from inventory_tracking.levels.model import UNIQUE_CHEST, Ground, Room, Target
from inventory_tracking.levels.presets import display_name
from inventory_tracking.levels.route import room_at
from inventory_tracking.macros import agenda as goal_agenda, lootpolicy, route, supply, zonenav
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.agenda import (
    BOSS_WAY,
    COVER,
    FULL_CLEAR,
    GROUPS_TAKEN,
    KILL,
    ON_THE_WAY,
    OPEN,
    PICKUP as SIDE,
    PLUS,
    PLUS_WAY,
    SHORT,
    SKIPPED,
    TRANSIT,
    ZONE_LEFT,
    Leader,
    LevelView,
    Objective,
)
from inventory_tracking.macros.bossledger import Boss
from inventory_tracking.macros.build import Intent
from inventory_tracking.macros.drinking import on_belt
from inventory_tracking.macros.drop_ledger import GATHER_TRIES
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.goals import (
    CLEAR_WAY,
    GUARD_NEAR,
    PICK_NEAR,
    PICK_REACH,
    PICK_UP,
    PLACE_NEAR,
    REACH,
    USE_NEAR,
    WAIT,
    Goal,
    clear_way,
    first_fight,
    goal_of,
    in_the_way,
    nearer,
    rest_of_level,
    summoner,
)
from inventory_tracking.macros.hunting.base import (
    ALONE_BOSS_UNITS,
    ARRIVED_SECONDS,
    BLOCK_SECONDS,
    CLEAR_SECONDS,
    DECIDE_SECONDS,
    ENGAGE_STRIKERS,
    FAR_JUDGED,
    GATHER_CLEAR,
    JUDGE_GAP,
    LOOP_PICK_SECONDS,
    OMEN_NEAR,
    OPEN_NEAR,
    PASS_SECONDS,
    PROGRESS_LOOK,
    PROGRESS_SECONDS,
    QUIET_UNITS,
    REMEMBERED_NEAR,
    REST_SECONDS,
    SHACK_TRIES,
    SUPER_NEAR,
    SUPER_TRIES,
    TAKE_BACK,
    VANISH_UNITS,
    WAYS,
    Bearings,
    Judging,
    door_entry,
    hostiles,
    omen_stand,
    passing_key,
    threat,
)
from inventory_tracking.macros.hunting.throne import (
    GIVEN_UP,
    STAND_MARK,
    THRONE,
    THRONE_WAVES,
    seat_of,
    stand_of,
    wave_goal,
)
from inventory_tracking.macros.movement import HOPS
from inventory_tracking.macros.pickup import (
    POTION_UNITS,
    Refused,
    choose,
    gheeds_carried,
    shortages,
    unique_grand_charm,
    unshunned,
    worth_a_stop,
)
from inventory_tracking.macros.pursuit import Pursuit
from inventory_tracking.macros.runmode import AGENDA, DOUBLE, Mode, aim_of, doubles, mode_of, said
from inventory_tracking.macros.shacks import shack_thing
from inventory_tracking.macros.sight import clear_shot
from inventory_tracking.macros.superchests import level_goal, mark_use, super_chests
from inventory_tracking.macros.supply import detour, low, worth
from inventory_tracking.macros.travel import PRESSED, STANDING, Point, clear_line, label, open_reaches, walked_length
from inventory_tracking.macros.tzroutine import Itinerary
from inventory_tracking.models import PotionType
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import FIGHT, USE, Stage
from inventory_tracking.terror.zones import level_population


if TYPE_CHECKING:
    from inventory_tracking.macros.hunt import Hunter


# An act at an object that did not take is remembered under its own goal's key and that goal is made again from nearer
# (`from_nearer`), the run's own look's goal (`cleared`: the agenda's and the level's super chests) too.
# 02:37:00-02:37:08 and 02:39:31-02:39:40 on 2026-10-21 (act loop, Upper and Lower Kurast): the agenda's chest clicked
# three times from 9-10 units outside its hut's wall, each try from the same spot, because the miss went down under the
# route's goal (`Hunter.base`); that goal, made nearer, teleported onto the chest and opened it in 0.28 s
# (rca/2026-10-21/super-chest-misses-findings.md §3.4). A clearing goal's key holds its unit: every agenda chest is
# "agenda: Super chest". Off: the miss under the route's goal alone, as before.
NEARER_CLEARING = True


def missed_key(goal: Goal) -> str:
    """The key `Hunter.missed` remembers `goal`'s act by: its label, with NEARER_CLEARING a clearing goal's unit too."""
    if NEARER_CLEARING and goal.clearing and goal.unit is not None:
        return f'{goal.label} ({goal.unit})'
    return goal.label


def from_nearer(missed: tuple[str, float] | None, goal: Goal | None, now: float) -> Goal | None:
    """`goal` made again from nearer (goals.py `nearer`) while its act's miss (`Hunter.missed`) holds."""
    if goal is not None and missed is not None and missed[0] == missed_key(goal) and now <= missed[1]:
        return nearer(goal)  # its act missed from there: from nearer now
    return goal


# The player, 2026-10-21 ~20:15: "we need to do the best aiming when we're trying to focus mob". In the T5 Herald
# fight of 18:54-18:56 the run left the fight for side goals "on the way" 32 times (24 Teleports toward a super
# healing potion, 8 toward gold), each ending the strike on the held Herald (rca/2026-10-21/herald-aiming-findings.md
# §2.5). True: while the leader the attack holds (builds/warlock/echoing_strike/attack.py HOLD_LEADER, `holding`)
# lives within the strike's reach, gold is no side goal, nor a healing potion while the belt holds more
# rejuvenations than manaburn.KEPT_REJUVENATIONS (the life for the fight, as manaburn.STAY_IN_HERALD_FIGHT rules for
# far ones); valuables and rejuvenations stay. False: as before.
HELD_STAYS = True
# A level the terror zone left under the run (ZONE_LEFT) with a boss of the game's ledger alive on it or on a level
# under it in the zone's graph (macros/bossledger.py) is worked on the way (ON_THE_WAY: the leaders near, the boss
# goals, the route's fight) instead of the run ending at once. The player, 2026-10-22: "we need to kill all bosses,
# no exceptions to that"; Andariel seen 64 units off when Catacombs Level 4 was no longer terrorized (10-21 06:00:00,
# rca/2026-10-22/boss-audit-findings.md §4 cause 6). False: the run ends at once, as before
BOSS_ROTATION = True
# Such a level worked for its bosses alone (agenda.py BOSS_WAY; 2026-10-23, lever 2 of
# rca/2026-10-22/exp-hour-findings.md: 20.2 min of the 10-22 shard game on plain monsters at 11k exp a minute against
# 128k on terrorized ones, the tombs at 19:50-19:59 157 kills for 10k): no leader gone for, none fought on the way but
# what strikes at the party (as a level only crossed, TRANSIT), the bosses of the game's ledger and the route's fight
# still gone to and killed ("Kill every boss", the player, 2026-10-23). False: ON_THE_WAY, its leaders near too, as
# before
BOSSES_ONLY = True
HELD_SAID: set[tuple[int, int]] = set()  # (drop, leader) the wait was said for; (drop, FIGHT_SAID) the fight's
# POTION_HELD (2026-10-22, Sewers Level 1 21:05:10-21:05:53, take 20261022T180453Z-92, and the Disused Fane's tier 5
# Herald 21:04:00-21:04:44, take 20261022T180330Z-95; rca/2026-10-22/potion-flipflop-findings.md): the belt's healing
# potions gone to the mercenary's healer (8 rejuvenations kept, the life full), the run went from the fight to a super
# healing potion and back at every look: 34 "worth its detour", 30 Teleports toward it, 9 Death Marks cast again after
# the hops, while a Horadrim Ancient grew back 41 -> 81 of 128 and raised its Horror three times. From 21:05:33 the
# detour went by turns to two potions 54 apart that were both left ("left: guarded 15 s"): 14 Teleports, no lasting
# kill. Three paths chose a potion, each by its own rules: the near pick (the given-up ones left out), the far detour
# (`scarce`: every potion remembered, left or waiting or not) and the held leader's wait (`wait_for_held`, which
# `scarce` did not hear). True, one choice of the potion side goal:
# - one ledger: a potion left (its tries spent, guarded past BLOCK_SECONDS, or given up by a knot of moves:
#   judging.py STILL_BUDGET, `Hunter.side_left`) or waiting is out of the near pick and of the far detour alike;
# - the fight first: while the fight is live (`fight_live`: a strike within FIGHT_LIVE s, a hostile within the strike's
#   reach) gold and healing potions wait as for a held leader (HELD_STAYS), unless the life is under the safety's floor
#   or the belt keeps no more than manaburn.KEPT_REJUVENATIONS rejuvenations (survival first, as HELD_STAYS);
# - held: the far detour judged is kept at its next judging (4 * DECIDE_SECONDS) while it lies, is not left and the
#   belt wants it; another takes it over only when more than agenda.HELD_REACH times nearer (HELD_GOALS' hysteresis).
# False: the three paths as before.
POTION_HELD = True
FIGHT_LIVE = 3.0  # seconds since the fight's last strike that it is still on (its look-to-look gaps are 1-2 s)
FIGHT_SAID = -1  # HELD_SAID's leader for the live fight's wait


def held_in_reach(self: Hunter, here: Point, foes: Sequence[Monster]) -> int | None:
    """The leader the build's attack holds (its `holding`), while it lives within the strike's reach; None else."""
    holding = getattr(self.build.attack, 'holding', None)
    unit = holding() if holding is not None else None
    if unit is None:
        return None
    found = next((m for m in foes if m.unit_id == unit), None)
    return unit if found is not None and math.dist(here, (found.x, found.y)) <= self.reach else None


def fight_live(self: Hunter, here: Point, foes: Sequence[Monster], now: float) -> int:
    """POTION_HELD: the hostiles within the strike's reach while the fight is on (its last strike within FIGHT_LIVE
    s); 0 else."""
    if not POTION_HELD or now - self.struck_at > FIGHT_LIVE:
        return 0
    return sum(1 for m in foes if math.dist(here, (m.x, m.y)) <= self.reach)


def survival_needs(self: Hunter, loot: Loot) -> bool:
    """Whether a healing potion is the fight's life: the belt read with no more than manaburn.KEPT_REJUVENATIONS
    rejuvenations, or (POTION_HELD) the life under the safety's floor. An unread belt waits for nothing."""
    if not loot.belt_read:
        return True
    if on_belt(loot)[PotionType.REJUVENATION] <= manaburn.KEPT_REJUVENATIONS:
        return True
    floor = self.build.settings.safety.floor
    return POTION_HELD and bool(loot.max_life) and 100.0 * loot.life < floor * loot.max_life


def waiting_kinds(
    self: Hunter, loot: Loot, here: Point, foes: Sequence[Monster], now: float | None = None
) -> tuple[frozenset[str], int | None, int]:
    """(the side goals' kinds that wait now, the held leader they wait for, the hostiles of the live fight in reach):
    gold and (unless `survival_needs`) healing potions, while a held leader lives in reach (HELD_STAYS) or, with
    `now`, while the fight is live (POTION_HELD, `fight_live`)."""
    leader = held_in_reach(self, here, foes) if HELD_STAYS else None
    fighting = fight_live(self, here, foes, now) if leader is None and now is not None else 0
    if leader is None and not fighting:
        return frozenset(), None, 0
    kinds = {GOLD} if survival_needs(self, loot) else {GOLD, HEALING}
    return frozenset(kinds), leader, fighting


def wait_for_held(self: Hunter, loot: Loot, here: Point, foes: Sequence[Monster], now: float | None = None) -> Loot:
    """`loot` without the side goals that wait while a held leader lives in reach (HELD_STAYS) or the fight is live
    (POTION_HELD, with `now`), each said once."""
    kinds, leader, fighting = waiting_kinds(self, loot, here, foes, now)
    if not kinds:
        return loot
    waiting = [found for found in loot.drops if found.kind in kinds]
    for found in waiting:
        key = (found.unit_id, leader if leader is not None else FIGHT_SAID)
        if key not in HELD_SAID:
            if len(HELD_SAID) > 200:
                HELD_SAID.clear()
            HELD_SAID.add(key)
            away = math.dist(here, (found.x, found.y))
            if leader is not None:
                LOG.info(
                    'Macro: pursuit: %s at (%.0f, %.0f), %.0f away, waits: the leader %d held is in reach',
                    found.label, found.x, found.y, away, leader,
                )  # fmt: skip
            else:
                LOG.info(
                    'Macro: pursuit: %s at (%.0f, %.0f), %.0f away, waits: the fight first (%d in reach, struck '
                    '%.1f s ago; POTION_HELD)',
                    found.label, found.x, found.y, away, fighting, (now or 0.0) - self.struck_at,
                )  # fmt: skip
    return replace(loot, drops=tuple(found for found in loot.drops if found.kind not in kinds)) if waiting else loot


def side_drop(
    self: Hunter,
    run: Run,
    here: Point,
    foes: Sequence[Monster] = (),
    world: World | None = None,
    *,
    restocking: bool = False,
) -> Drop | None:
    """What a level run takes on its way (pickup.py `choose`): a valuable within PICK_NEAR, gold within a jump, a
    potion the belt wants; not one given up (GATHER_TRIES). A valuable off the way hides nothing nearer. A wanted
    potion's guards are the fight first (goals.py `in_the_way`); one guarded BLOCK_SECONDS is left. Else `restock`,
    then `scarce`. `restocking`: attack mode's own look, the restock only."""
    if run.loot is None:
        return None
    now = run.clock()
    loot = unshunned(run.loot(), now)
    self.again(run, loot.drops, here, world)
    # Given-up drops leave the choice, said once each
    given_up = {unit: self.drops.given_up(unit) for unit in self.drops.gathered if self.drops.spent(unit)}
    given_up |= {
        unit: f'left: guarded {BLOCK_SECONDS:.0f} s'
        for unit, since in self.guarded_since.items()
        if now - since > BLOCK_SECONDS
    }
    if POTION_HELD:
        given_up |= self.side_left  # given up by a knot of moves (judging.py STILL_BUDGET)
    for found in loot.drops:
        if found.unit_id in given_up:
            self.refused_potion(found, here, given_up[found.unit_id])
            self.left(found, here, given_up[found.unit_id], 'the level run')
            if self.given_up_charm(run, found, given_up[found.unit_id]):
                return None  # the run ends for the Gheed's swap
    loot = replace(loot, drops=tuple(found for found in loot.drops if found.unit_id not in given_up))
    if restocking:
        return self.restock(run, loot, here, foes, world)
    if self.buffs.quiet_by_the_boss and any(self.boss(m) and math.dist(here, (m.x, m.y)) <= self.reach for m in foes):
        # Only potions while the run's boss is in reach: her death first (QUIET_BY_THE_BOSS,
        # rca/2026-10-18/andariel-cadence-findings.md §5 F3).
        loot = replace(loot, drops=tuple(found for found in loot.drops if found.kind in (HEALING, REJUVENATION)))
    waits, _, _ = waiting_kinds(self, loot, here, foes, now if POTION_HELD else None)
    loot = wait_for_held(self, loot, here, foes, now if POTION_HELD else None)
    # POTION_HELD's one ledger: what is left or waits now is out of the far detour too (`scarce`)
    out = frozenset(given_up) if POTION_HELD else frozenset()
    plan = choose(loot, here)
    drop = plan.drop if plan is not None else None
    looped = self.pursuit is not None and self.pursuit.looped
    while drop is not None and drop.kind == VALUABLE and not self.on_the_way(run, here, drop, world, looped=looped):
        # Out of the choice, hiding nothing nearer (run-1932-findings.md issue 2)
        loot = replace(loot, drops=tuple(found for found in loot.drops if found.unit_id != drop.unit_id))
        plan = choose(loot, here)
        drop = plan.drop if plan is not None else None
    if drop is not None and drop.kind == VALUABLE and looped and not self.walked_near(run, here, drop, world):
        # The loop's far valuable hides no nearer wanted potion: that one first
        supplies = choose(replace(loot, drops=tuple(found for found in loot.drops if found.kind != VALUABLE)), here)
        potion = supplies.drop if supplies is not None else None
        nearer = potion is not None and math.dist(here, (potion.x, potion.y)) < math.dist(here, (drop.x, drop.y))
        if potion is not None and potion.kind in (HEALING, REJUVENATION) and nearer:
            drop = potion
    if drop is not None and drop.kind in (HEALING, REJUVENATION):
        guards = threat(run)(here, (drop.x, drop.y))
        if not guards:
            self.guarded_since.pop(drop.unit_id, None)
            return drop
        if len(self.guarded_since) > 200:
            self.guarded_since.clear()
        self.guarded_since.setdefault(drop.unit_id, now)
        if self.potions.refuse(drop.unit_id, 'guarded: its guards are the fight first'):
            LOG.info(
                'Macro: pursuit: %s at (%.0f, %.0f), %.0f away: %d hostiles within %.0f of it or the '
                'character are the fight first',
                drop.label, drop.x, drop.y, math.dist(here, (drop.x, drop.y)), guards, GATHER_CLEAR,
            )  # fmt: skip
        return drop
    if drop is not None:
        return drop
    return self.restock(run, loot, here, foes, world) or self.scarce(
        run, loot, here, world, out=out, waiting=POTION_HELD and HEALING in waits
    )


def restock(
    self: Hunter, run: Run, loot: Loot, here: Point, foes: Sequence[Monster], world: World | None
) -> Drop | None:
    """A potion a low belt takes before the goal, in the quiet (no hostile within QUIET_UNITS; supply.py `low`,
    `restock`; the player, 2026-10-14; run-1932-findings.md issue 2). Said once a potion."""
    if any(math.dist(here, (m.x, m.y)) <= QUIET_UNITS for m in foes) or not low(loot):
        return None
    world = world if world is not None else run.world()
    level = self.known_level(world.player) if world.player is not None else None
    found = supply.restock(loot, here, Ground(level.ground) if level is not None else None, world.doors)
    if found is not None and found.unit_id not in self.restock_said:
        if len(self.restock_said) > 200:
            self.restock_said.clear()
        self.restock_said.add(found.unit_id)
        belt = on_belt(loot)
        LOG.info(
            'Macro: pursuit: restock: %s at (%.0f, %.0f), %.0f away, before the goal: the belt is low (healing '
            '%d, rejuvenations %d), no hostile within %.0f',
            found.label, found.x, found.y, math.dist(here, (found.x, found.y)), belt[PotionType.HEALING],
            belt[PotionType.REJUVENATION], QUIET_UNITS,
        )  # fmt: skip
    return found


def given_up_charm(self: Hunter, run: Run, drop: Drop, why: str) -> bool:
    """The Gheed's swap backstop: a unique Grand Charm given up on with a Gheed's Fortune carried is the carry-one
    refusal (pickup.py `Refused`), whatever its tries ended as (2026-10-18 13:56:41). Asked once a drop; whether the
    swap starts (the run then ended)."""
    if self.carry_one is None or drop.kind != VALUABLE or drop.unit_id in self.drops.swap_asked:
        return False
    if not unique_grand_charm(drop) or not gheeds_carried(run):
        return False
    self.drops.first(self.drops.swap_asked, drop.unit_id)
    refused = Refused(drop, f"{drop.label} {why}, a Gheed's Fortune carried")
    return self.carry_one_swap(run, refused)


def carry_one_swap(self: Hunter, run: Run, refused: Refused) -> bool:
    """Whether the runner starts the Gheed's swap for `refused`; the level run then ends (runner.py `_run_over`)."""
    if self.carry_one is None or not self.carry_one(refused):
        return False
    self.end_run(run, f"{refused}: the Gheed's swap")
    return True


def forget_given_up(self: Hunter) -> None:
    """Every give-up forgotten (`DropLedger.forget`): the Gheed's swap's GHEED_STASH (runner.py)."""
    self.drops.forget()


def again(self: Hunter, run: Run, drops: Sequence[Drop], here: Point, world: World | None = None) -> None:
    """A given-up valuable is tried once more (once a drop) when the character comes within PICK_REACH of it on a
    clear line (rca/2026-10-14/run-1214-findings.md §3.2). What the player put down is never among `drops`
    (game/kept.py `PutDown`)."""
    spent = [
        d
        for d in drops
        if d.kind == VALUABLE
        and self.drops.spent(d.unit_id)
        and d.unit_id not in self.drops.retried
        and math.dist(here, (d.x, d.y)) <= PICK_REACH
    ]
    if not spent:
        return
    world = world if world is not None else run.world()
    level = self.known_level(world.player) if world.player is not None else None
    if level is None:
        return
    ground = Ground(level.ground)
    for drop in spent:
        if not clear_line(ground, world.doors, here, (drop.x, drop.y)):
            continue
        self.drops.first(self.drops.retried, drop.unit_id)
        why = self.drops.given_up(drop.unit_id)
        self.drops.gathered[drop.unit_id] = GATHER_TRIES - 1
        self.drops.tried.pop(drop.unit_id, None)
        self.drops.left_said.discard(drop.unit_id)
        LOG.info(
            'Macro: pickup: one more try at %s at (%.0f, %.0f), %.0f away on a clear line now (%s)',
            drop.label, drop.x, drop.y, math.dist(here, (drop.x, drop.y)), why,
        )  # fmt: skip
        run.say(f'One more try at {drop.label}')


def left(self: Hunter, drop: Drop, here: Point, why: str, who: str) -> None:
    """A valuable or gold `who` gives up on, said once a drop (a potion says its own: `refused_potion`)."""
    if drop.kind in (HEALING, REJUVENATION) or not self.drops.first(self.drops.left_said, drop.unit_id):
        return
    LOG.info(
        'Macro: %s leaves %s at (%.0f, %.0f), %.0f away: %s',
        who, drop.label, drop.x, drop.y, math.dist(here, (drop.x, drop.y)), why,
    )  # fmt: skip


def refused_potion(self: Hunter, drop: Drop, here: Point, why: str) -> None:
    """A potion the run leaves, said once a potion and reason (potions-findings.md M4: it was silent)."""
    if drop.kind in (HEALING, REJUVENATION) and self.potions.refuse(drop.unit_id, why):
        LOG.info(
            'Macro: pursuit: %s at (%.0f, %.0f), %.0f away, %s',
            drop.label, drop.x, drop.y, math.dist(here, (drop.x, drop.y)), why,
        )  # fmt: skip


def scarce(
    self: Hunter,
    run: Run,
    loot,
    here: Point,
    world: World | None,
    *,
    out: frozenset[int] = frozenset(),
    waiting: bool = False,
) -> Drop | None:
    """A healing potion beyond POTION_UNITS worth its detour (supply.py `worth`, `detour`) while the belt is below
    the reserve: the potions short at harm's price against the eta there and back. Judged once in 4 *
    DECIDE_SECONDS over the nearest two; the one found stays the goal until then. POTION_HELD: none of `out` (the
    potions left: `side_drop`'s ledger), none while healing potions wait for the fight (`waiting`; the one judged
    kept for after it), and the one judged last is kept at the next judging unless another is more than
    agenda.HELD_REACH times nearer (`held_first`)."""
    if not loot.belt_read:
        return None  # unknown, not low: the next look reads it again
    if POTION_HELD and waiting:
        return None  # the fight first (`waiting_kinds`); `fetching` is kept for after it
    now = run.clock()
    rejuvenations = on_belt(loot)[PotionType.REJUVENATION]
    fighting = manaburn.herald_fight(here, world.monsters, rejuvenations) if world is not None else 0
    if fighting:  # STAY_IN_HERALD_FIGHT: the belt's rejuvenations are the life for it
        self.fetching = (now, None)
        why = f'the Herald fight first: {fighting} of its pack within {PACK_SEEN:.0f}, {rejuvenations} rejuvenations'
        for potion in self.potions.lying(HEALING, here)[:2]:
            if math.dist(here, (potion.x, potion.y)) > POTION_UNITS:
                self.refused_potion(Drop(potion.unit, potion.x, potion.y, potion.label, potion.kind), here, why)
        return None
    judged, found = self.fetching
    if found is not None and POTION_HELD and found.unit_id in out:
        found = None  # left since it was judged: no longer the goal, nor the one held
    if now - judged < 4 * DECIDE_SECONDS:
        return found if found is not None and found.unit_id in self.potions.seen else None
    self.fetching = (now, None)
    settings = self.build.settings.safety
    belt = on_belt(loot)
    healing, rejuvenations = belt[PotionType.HEALING], belt[PotionType.REJUVENATION]
    allowed = worth(healing, reserve(loot.max_life, rejuvenations, HEAL_PRIORITY), settings.healing_seconds)
    if not allowed or not shortages(loot)[1] or world is None or world.player is None:
        return None
    rect = run.actuator.keys.focused_window_rect()
    level = self.known_level(world.player)
    if rect is None or level is None:
        return None
    ground = Ground(level.ground)
    far = [
        p
        for p in self.potions.lying(HEALING, here)
        if math.dist(here, (p.x, p.y)) > POTION_UNITS and not (POTION_HELD and p.unit in out)
    ]
    for potion in held_first(far, found, here) if POTION_HELD else far[:2]:
        if self.drops.spent(potion.unit):
            continue
        there = self.travel.eta(run, world, ground, rect[2] / rect[3], (potion.x, potion.y), PRESSED, level.rooms)
        cost = detour(there, settings.operate_dwell)
        if cost > allowed:
            self.refused_potion(
                Drop(potion.unit, potion.x, potion.y, potion.label, potion.kind),
                here,
                f'not worth its detour: {cost:.1f} s against {allowed:.0f} s (belt healing {healing})',
            )
            continue
        LOG.info(
            'Macro: pursuit: %s at (%.0f, %.0f) is worth its detour: %.1f s against %.0f s (belt healing %d)',
            potion.label, potion.x, potion.y, cost, allowed, healing,
        )  # fmt: skip
        drop = Drop(potion.unit, potion.x, potion.y, potion.label, potion.kind)
        self.fetching = (now, drop)
        return drop
    return None


def held_first(far: Sequence[supply.Seen], held: Drop | None, here: Point) -> list[supply.Seen]:
    """POTION_HELD: the far detour's candidates in order: the nearest two, the one `held` (judged last) first unless
    another is more than agenda.HELD_REACH times nearer; `held` comes in even if not among the nearest two."""
    nearest = list(far[:2])
    kept = next((p for p in far if held is not None and p.unit == held.unit_id), None)
    if kept is None:
        return nearest
    others = [p for p in nearest if p.unit != kept.unit]
    away = math.dist(here, (kept.x, kept.y))
    nearer = [p for p in others if math.dist(here, (p.x, p.y)) * goal_agenda.HELD_REACH < away]
    return [*nearer, kept, *[p for p in others if p not in nearer]]


def stay_by(
    self: Hunter,
    run: Run,
    here: Point,
    *,
    wanted: bool = True,
    foes: Sequence[Monster] = (),
    world: World | None = None,
) -> Drop | None:
    """A wanted valuable within PICK_NEAR with no room for it: the run stands by it (goals.py `WAIT`; the player,
    2026-10-13: "when valuable doesn't fit: we need to stop near it"). Not equipment taken only because the filter
    shows it ("allow moving when the item isn't very valuable", 2026-10-12), but a shown unique or set item, yes
    (2026-10-14); not one a press went on from (`waived`). The card warns meanwhile. Not `wanted`: only the warning
    is taken back. Out of the KP_6 loop, while a trip could be made (`trips_by_hand`), the shared no-room routine
    (`no_room`: the cube, then a trip) stands by what a trip is made for too (lootpolicy.py `trip_for`; the player,
    2026-10-19: "EVERY loop and activity should have the same routines"); the cube is tried for the rest. The loop's
    stand is its stops' (runner.py `poll`)."""
    loot = unshunned(run.loot(), run.clock()) if run.loot is not None and wanted else None
    found = None
    quiet = all(math.dist(here, (m.x, m.y)) > QUIET_UNITS for m in foes)
    hand = loot is not None and self.trips_by_hand(run)
    if loot is not None:
        near = [d for d in loot.drops if d.kind == VALUABLE and math.dist(here, (d.x, d.y)) <= PICK_NEAR]
        roomless = [d for d in near if not has_room(loot.room, d.size) and d.unit_id not in self.waived]
        left = [
            d for d in near
            if lootpolicy.verdict(
                d, lootpolicy.RUN, room=has_room(loot.room, d.size), shown=d.unit_id in loot.shown,
                given_up=d.unit_id in self.waived,
            ).hold
            or (hand and d in roomless and lootpolicy.trip_for(d, shown=d.unit_id in loot.shown))
        ]  # fmt: skip
        found = min(left, key=lambda d: math.dist(here, (d.x, d.y))) if left else None
        if found is None and not self.looping() and roomless:
            # An identify candidate or shown gear the run goes on from: the cube still makes its room once
            other = min(roomless, key=lambda d: math.dist(here, (d.x, d.y)))
            self.no_room(run, world, other, loot, quiet=quiet, trip=False)
    if found is None or loot is None:
        if self.warned is not None:
            self.warned = None
            run.warn(None)
        return None
    if self.no_room(run, world, found, loot, quiet=quiet):
        if self.warned is not None:
            self.warned = None
            run.warn(None)
        return None
    if self.warned != found.unit_id:
        self.warned = found.unit_id
        cube = loot.cube is not None and has_room(loot.cube, found.size)
        told = ' (the cube has room for it)' if cube else ''
        LOG.info(
            'Macro: pursuit: the inventory has no room for %s at (%.0f, %.0f), %.0f away: the run stands by it%s',
            found.label, found.x, found.y, math.dist(here, (found.x, found.y)), told,
        )  # fmt: skip
        run.stand_by(f'Inventory full: {found.label} here — make room{told}')
    return found


def trips_by_hand(self: Hunter, run: Run) -> bool:
    """Whether the hunt by hand holds what the shared no-room routine makes a trip for (lootpolicy.py `trip_for`):
    the KP_6 loop off, mouse mode, and a trip possible in this game (the runner's `can_trip`). Without one the sites'
    own rules stand: shown gear and plain valuables are gone on from, as the player ruled when no trip followed a
    stand (2026-10-12: "allow moving when the item isn't very valuable"; 2026-10-18: "moved on from by hand")."""
    return not self.looping() and run.pad is None and self.can_trip is not None and self.can_trip()


def no_room(
    self: Hunter, run: Run, world: World | None, found: Drop, loot: Loot, *, quiet: bool, trip: bool = True
) -> bool:
    """The shared no-room routine's first steps for `found`, a valuable with no inventory room (macros/running/room.py),
    only in the quiet: the cube once a drop (`room_maker`: the loop's items by the protected cells, never the
    player's; "if we have cube space - we should move items there", the player, 2026-10-17), then, with the cube tried
    or full and `trip`, the trip's ask (`room_trip`: an activity by hand; it cancels the run when due). Whether room
    was made in the cube: the next look takes it."""
    if not quiet:
        return False
    cube = loot.cube is not None and has_room(loot.cube, found.size)
    if (cube or loot.cube is None) and self.room_maker is not None and self.room_tried != found.unit_id:
        self.room_tried = found.unit_id
        try:
            moved = self.room_maker(run)
        except Abort as stop:
            if run.stops(stop):
                raise
            LOG.info('Macro: pursuit: no room made in the cube for %s: %s', found.label, stop)
            moved = 0
        if moved:
            LOG.info('Macro: pursuit: %d items into the cube: room for %s', moved, found.label)
            return True
    tried = self.room_tried == found.unit_id or not (cube or loot.cube is None)
    if trip and tried and self.room_trip is not None:
        self.room_trip(run, found, world if world is not None else run.world(), loot)
    return False


def shack_goal(self: Hunter, run: Run, world: World, player, route: str) -> Goal | None:
    """On the KP_6 loop, a closed container in sight beside one of the camp's chests (shacks.py;
    routes/lower-kurast-loop-plan.md phase 6c), a side goal of `route`; left after SHACK_TRIES."""
    level = self.known_level(player)
    if level is None or run.things is None:
        return None
    ground, here = Ground(level.ground), (player.x, player.y)
    if len(self.shack_tries) > 200:
        self.shack_tries.clear()  # units of games long left
    skip = frozenset(unit for unit, tries in self.shack_tries.items() if tries >= SHACK_TRIES)
    found = shack_thing(
        run.things(), level.rooms, here, lambda origin, at: clear_shot(ground, origin, at, world.doors), skip
    )
    if found is None:
        return None
    thing, name = found
    mark = Target(player.area, (), (thing.x / TILE_UNITS, thing.y / TILE_UNITS), name, 'target', use=UNIQUE_CHEST)
    label = f'{name}, in the shack'
    return Goal(label, (thing.x, thing.y), USE, USE_NEAR, self.looped, unit=thing.unit_id, mark=mark, route=route)


def super_chest_goal(
    self: Hunter, run: Run, player, here: Point, route: str, spend: Intent, rooms: Sequence[Room] = ()
) -> Goal | None:
    """A full clear's nearest closed super chest within SUPER_NEAR; left after SUPER_TRIES."""
    if run.things is None:
        return None
    chests = [
        thing
        for thing in super_chests(run.things(), rooms)  # the glowing ones and the unique-chest spots' (superchests.py)
        if thing.mode == 0
        and thing.selectable is not False
        and self.shack_tries.get(thing.unit_id, 0) < SUPER_TRIES
        and math.dist(here, (thing.x, thing.y)) <= SUPER_NEAR
        and passing_key((thing.x, thing.y), thing.unit_id, rooms) not in self.passed
    ]
    if not chests:
        return None
    thing = min(chests, key=lambda t: math.dist(here, (t.x, t.y)))
    place = (thing.x / TILE_UNITS, thing.y / TILE_UNITS)
    mark = Target(player.area, (), place, 'Super chest', 'target', use=mark_use(thing))
    return Goal('full clear: Super chest', (thing.x, thing.y), USE, USE_NEAR, spend, unit=thing.unit_id, mark=mark,
                route=route, clearing=True)  # fmt: skip


def at_hand(self: Hunter, found: Goal | None, player, world: World) -> bool:
    """Whether the route's `found` is a chest opened from where the character stands: then before the shack's
    container (rca/2026-10-17/slow-legs-findings.md)."""
    level = self.known_level(player)
    if found is None or found.do != USE or level is None:
        return False
    return open_reaches(Ground(level.ground), world.doors, (player.x, player.y), found.place, OPEN_NEAR)


def blockers(self: Hunter, goal: Goal | None, foes: Sequence[Monster], now: float) -> list[Monster]:
    """Living hostiles the hands found in the way of `goal`'s act (`Covered`), for BLOCK_SECONDS."""
    blocking = self.blocking
    if blocking is None or goal is None:
        return []
    label, units, until = blocking
    found = [m for m in foes if m.unit_id in units]
    if label != goal.label or now > until or not found:
        self.blocking = None
        return []
    return found


UNEXPLORED = 'an unexplored room'  # what a tour stop is called (`next_room`, `elsewhere`)


def seal_of(bearings: Bearings, area: int, here: Point, stage: Stage) -> tuple[Point, str] | None:
    """(place in world units, label) of the seal that calls a markless fight stage's boss on level `area` (goals.py
    `summoner`), its card mark nearest `here`; None for another stage or with the mark not on the card."""
    script = bearings.script(area)
    before = summoner(script.stages, stage) if script is not None else None
    if before is None or bearings.marks is None:
        return None
    places = [(x * TILE_UNITS, y * TILE_UNITS) for x, y in bearings.marks(before.mark)]
    if not places:
        return None
    return min(places, key=lambda place: math.dist(here, place)), before.mark


# 17:48:34-17:49:17 on 2026-10-23 (take 20261023T144821Z-27): the Outer Cloister's way into the Monastery Gate marked
# on roof at (15177.5, 5005.0), the door (class 24) in the edge's gap at (15141, 5002); the 45 s watchdog stopped the
# loop. True: a door on the edge an open passage crosses is the passage (levels/exits.py `door_passage`): the card's
# passage moves past it, and the walk opens it (moves.py `door_across`). False: the computed passage only.
PASSAGE_DOOR = True


def goal(
    self: Hunter, run: Run, world: World, foes: list[Monster], pressed: bool, posted: Pursuit | None
) -> Goal | None:
    """The goal the key means now (goals.py `goal_of`) from the route's stage, the card, the hostiles and memory.
    A press takes a valuable beside the character first (pickup.py `worth_a_stop`, once a press); a level run its
    side drop. Hostiles barring the act make their fight the goal (`first_fight`). `posted`: the mailbox as read."""
    player = world.player
    assert player is not None
    here, area, bearings = (player.x, player.y), player.area, self.bearings
    running = posted is not None and posted.runs
    staged = route.staged(bearings.progress, area)
    card = bearings.card() if bearings.card is not None else None
    if card is not None and card.area != area:
        card = None  # the card is still the level just left
    if card is not None and card.passage is not None and PASSAGE_DOOR:
        # A door on the level edge is the open passage (levels/exits.py `door_passage`): the goal itself goes there,
        # so the decision and the move agree (18:20:06-21:33 on 2026-10-23, the Outer Cloister: a move-only redirect
        # hopped door, mark, door for 90 s and the zone was skipped)
        mark = (card.passage[0] * TILE_UNITS, card.passage[1] * TILE_UNITS)
        if (via := door_passage(world.doors, card.rooms, mark)) is not None:
            card = replace(card, passage=(via[0] / TILE_UNITS, via[1] / TILE_UNITS))
    if (
        card is not None
        and staged is None
        and posted is not None
        and posted.agenda
        and not (pressed and posted.advance)
    ):
        # A terror zone run with no route stage here (a pending red portal, a `clear`): the card's first mark is
        # another level's door, no goal of the zone's (21:05:44 on 2026-10-19: "Ancients' Way" on the Frozen
        # Tundra; rca/2026-10-19/tz-coverage-findings.md F2). The player's own teleport press keeps it.
        card = None
    drop = side = stay = None
    if pressed and posted is not None and posted.advance:
        if self.stopped_for[0] != posted.pressed_at:
            self.stopped_for = (posted.pressed_at, worth_a_stop(run))
        drop = self.stopped_for[1]
    elif running:
        side = self.side_drop(run, here, foes, world)
        stay = self.stay_by(run, here, wanted=side is None, foes=foes, world=world)
    elif self.pursuing and not pressed:
        # Attack mode's own goal: a restock potion first
        side = self.side_drop(run, here, foes, world, restocking=True)
    known = self.remembered(area) if self.remembered is not None else []
    live = {m.unit_id for m in foes}
    self.vanished |= {unit for unit, x, y, _ in known if unit not in live and math.dist(here, (x, y)) <= VANISH_UNITS}

    def elsewhere() -> tuple[Point, str] | None:
        # Nothing known of the boss: the nearest hostile known, else the nearest unexplored room (as seek does).
        quarry = self.quarry(area, here, foes, any_hostile=True)
        if quarry is not None:
            return quarry
        level, rect = self.known_level(player), run.actuator.keys.focused_window_rect()
        frontier = self.frontier(level, player, rect) if level is not None and rect is not None else None
        if frontier is None:
            return None
        _, _, (x, y) = frontier
        return ((x + 0.5) * TILE_UNITS, (y + 0.5) * TILE_UNITS), 'an unexplored room'

    opens = None
    if running and posted is not None and posted.rush and side is None and stay is None:
        # The KP_6 loop: a shack's container in sight first
        opens = self.shack_goal(run, world, player, staged[0] if staged is not None else '')
    found = goal_of(
        here,
        spend=self.looped_now(run.clock())
        if posted is not None and posted.rush
        else PRESSED
        if pressed or running
        else STANDING,
        reach=self.reach,
        stage=staged[1] if staged is not None else None,
        route=staged[0] if staged is not None else '',
        card=card,
        # Every hostile, the `untouchable` too: a boss the strikes did nothing to is still where the fight is.
        foes=hostiles(world),
        remembered=known,
        supers=bearings.supers(area) if bearings.supers is not None else (),
        gone=frozenset(self.vanished | set(self.untouchable)),
        # Only a press or a level run seeks an unknown boss (a potential over the whole level).
        elsewhere=elsewhere if pressed or running else None,
        entry=door_entry(card),
        drop=drop,
        side=side,
        stay=stay,
        appears=seal_of(bearings, area, here, staged[1]) if staged is not None else None,
    )
    if (
        found is not None
        and staged is not None
        and staged[1].mark
        and found.stage is None
        and found.mark is not None
        and found.mark.label != staged[1].mark
        and posted is not None
        and posted.agenda
        and not (pressed and posted.advance)
    ):
        # A terror zone run whose stage's way out is not on the card yet: the card's first mark is another level's
        # door (01:01:26 on 2026-10-20, Lost City: "at Ancient Tunnels (Valley of Snakes is not marked yet)" again
        # and again, the game left). The nearest unexplored room instead, where the way out comes in sight
        level, rect = self.known_level(player), run.actuator.keys.focused_window_rect()
        frontier = self.frontier(level, player, rect) if level is not None and rect is not None else None
        if frontier is None:
            found = None
        else:
            _, _, (x, y) = frontier
            place = ((x + 0.5) * TILE_UNITS, (y + 0.5) * TILE_UNITS)
            label = f'seek {staged[1].mark} (not marked yet): an unexplored room'
            found = Goal(label, place, REACH, PLACE_NEAR, found.spend, known=False, route=staged[0], clearing=True)
    if (
        THRONE_WAVES
        and area == THRONE
        and staged is not None
        and posted is not None
        and (posted.agenda or posted.looped)
        and (found is None or found.stage == staged[1])
        and (world.game_name, area, staged[1].boss) not in self.marks_empty
    ):
        # The Throne's waves, then the portal (the player, 2026-10-20 ~09:33: "tz leveling should do baal and trone
        # fight"; hunting/throne.py). The KP_6 loop's runs too since 2026-10-25: the Baal kind's (macros/loop.py
        # `baal_leg`; the player: "build a baal runner, very similar to andariel runner"); a KP_1 press keeps the route
        found = throne_goal(self, run, world, here, staged, found)
    if (
        found is not None
        and found.do == FIGHT
        and found.unit is None
        and found.stage is not None
        and (world.game_name, area, found.stage.boss) in self.marks_empty
    ):
        found = None  # its boss was not by its place (judging.py `empty_mark`): the level is explored or the run ends
    if opens is not None and not self.at_hand(found, player, world):
        found = opens
    found = from_nearer(self.missed, found, run.clock())
    if found is not None and found.do == FIGHT and found.unit in self.nearing:
        # strikes did nothing from there: fight from within the engage ring
        found = replace(found, near=min(found.near, self.attack.engage))
    self.base = found
    barring = self.blockers(found, foes, run.clock())
    if found is not None and running and (not self.pursuing or found.guarded):
        # The run's own move: what stands where the act is made is fought first (a pack on a seal, a potion's
        # guards); a press is never refused so (architecture §1).
        known = {m.unit_id for m in barring}
        barring += [m for m in in_the_way(found, foes, here) if m.unit_id not in known]
    return first_fight(found, here, barring, self.reach) if found is not None and barring else found


def throne_goal(self: Hunter, run: Run, world: World, here: Point, staged, found: Goal | None) -> Goal | None:
    """The Throne's goal for the route's stage `staged` (route, stage) from goal_of's `found` (hunting/throne.py
    `wave_goal`): the hall, the stand, the wait for Baal to leave, the portal. A wait that ends with no wave leaves
    the stage as an empty mark does (judging.py `empty_mark`): the level is explored, then the run ends."""
    route_name, stage = staged
    marks = self.bearings.marks(STAND_MARK) if self.bearings.marks is not None else ()
    seat = seat_of(world.monsters)
    now = run.clock()
    self.waves.begin(world.game_name)
    found_now = wave_goal(
        self.waves,
        area=THRONE,
        stage=stage,
        route=route_name,
        found=found,
        here=here,
        hostiles=hostiles(world),
        seat=seat,
        stand=stand_of([(x * TILE_UNITS, y * TILE_UNITS) for x, y in marks], seat),
        reach=self.reach,
        spend=found.spend if found is not None else PRESSED,
        now=now,
        passed=lambda m: m.unit_id in self.passed,
    )
    if found_now is GIVEN_UP:
        if len(self.marks_empty) > 200:
            self.marks_empty.clear()
        self.marks_empty.add((world.game_name, THRONE, stage.boss))
        self.wayless.add((world.game_name, THRONE))
        return None
    assert found_now is None or isinstance(found_now, Goal)
    return found_now


def cleared(
    self: Hunter, run: Run, world: World, foes: list[Monster], ground: Ground, found: Goal | None
) -> Goal | None:
    """A level run's goal by its mode (runmode.py; the player, 2026-10-14): the hostiles on the way (goals.py
    `clear_way`), on a full clear the rest of the level (`rest_of_level`), then the route's `found`. A fight, drop
    or stand-by of `found`'s is kept. Out of a full clear only a way through (WAYS) is cleared, not the way to an
    object: a seal calls its pack (fighting Vizier seal 1's pack first left the Vizier alive in ten arena plays).
    A goal with no strike or progress for CLEAR_SECONDS is passed (`goes_on`); see `taken_back`."""
    mode = self.mode
    if mode is not None and mode.agenda and self.agenda is not None:
        return self.agenda_cleared(run, world, foes, ground, found)
    clear = mode is not None and mode.clear
    if found is not None and (found.do in (PICK_UP, WAIT, FIGHT) or found.guarded):
        return found
    # Nor on the KP_6 loop's rushed run: "don't fight what isn't attacking" (the player, 2026-10-16;
    # rca/2026-10-18/freeze-near-mobs-findings.md)
    if not clear and (self.rushing or found is None or not found.route or found.do not in WAYS):
        return found
    player = world.player
    assert player is not None
    here, now = (player.x, player.y), run.clock()
    level = self.known_level(player)
    rooms = level.rooms if level is not None else ()
    self._forget_passed(now)
    spend = found.spend if found is not None else PRESSED

    herald = bool(self.omens) or any(m.tier and m.leader for m in foes)
    route = found.route if found is not None else ''
    chest = self.super_chest_goal(run, player, here, route, spend, rooms) if clear and not herald else None

    def candidate(skip: frozenset[object]) -> Goal | None:
        rest = self.rest_of(run, world, foes, here, skip, rooms) if clear and chest is None else None
        base = chest or (rest_of_level(rest, found, self.reach, spend) if rest is not None else found)
        near = self._on_the_way(world, ground, foes, here, skip)
        return clear_way(base, here, near, self.reach) if base is not None and near else base

    return self._clear_through(candidate, run, world, ground, rooms, found, now)


def _forget_passed(self: Hunter, now: float) -> None:
    """The passes and the goals left for another that are over (`goes_on`, `taken_back`)."""
    self.passed = {key: until for key, until in self.passed.items() if until > now}
    self.left_for = {key: left for key, left in self.left_for.items() if left[0] > now}


def _on_the_way(
    self: Hunter,
    world: World,
    ground: Ground,
    foes: Sequence[Monster],
    here: Point,
    skip: frozenset[object],
    which: Callable[[Monster], bool] = lambda m: True,
) -> list[Monster]:
    """The hostiles on the way (of `which`): within CLEAR_WAY with a clear line, not passed nor skipped."""
    return [
        m
        for m in foes
        if m.unit_id not in self.passed
        and m.unit_id not in skip
        and which(m)
        and math.dist(here, (m.x, m.y)) <= CLEAR_WAY
        and clear_shot(ground, here, (m.x, m.y), world.doors)
    ]


def _clear_through(
    self: Hunter,
    candidate: Callable[[frozenset[object]], Goal | None],
    run: Run,
    world: World,
    ground: Ground,
    rooms: Sequence[Room],
    found: Goal | None,
    now: float,
) -> Goal | None:
    """`candidate`'s goal (`taken_back`); one passed now (`goes_on`) yields to the next, at most three times."""
    chosen = found
    for _ in range(3):
        goal = self.taken_back(candidate, rooms, found)
        if goal is None or not goal.clearing or self.goes_on(run, world, ground, goal, rooms, now):
            chosen = goal
            break
    self.went_for(chosen, rooms, now)
    return chosen


# ROUTE_BOSS_FIRST (2026-10-22, Sewers Level 3, 23:15:49-23:20:30, take 20261022T201417Z-49; rca/2026-10-22/
# walled-boss-findings.md §2): with Radament (unit 881231773) in the read the run's goal went round the route's own
# "Radament" fight, the agenda's "full clear: the elite 229 (881231773)" (the same unit, a leader to it) and "agenda:
# Super chest": the agenda's was passed five times by STILL_BUDGET, the route's fight took over (a boss stage: no
# budget), the pass ran out and the agenda's came back, the chest between. True: the route's boss fight with its boss
# in the read is the run's goal; the agenda's targets wait for it (`cleared` keeps a route fight so off a zone kind).
# False: the agenda first, as before
ROUTE_BOSS_FIRST = True


# GUARD_AT_DROP (2026-10-23, rca/2026-10-23/fight-efficiency-findings.md shape d; the player: "your goal is to maximize
# exp/hour"): the agenda's target for a drop's look was taken as the drop's guard whatever it was. Its order puts a
# Herald before the drop (agenda.py `in_level`), so at 16:11:13-39 (take 20261023T130907Z-67) the character 0.7 units
# from a Flawless Topaz went for "Flawless Topaz: the fight first", a Herald 80 away, and back: 46 jumps, 0 kills; of
# 268 such moves 15:00-17:31, 175 went for a "guard" more than 12 from both the drop and the character. True: the
# agenda's kill target is the drop's guard only by the agenda's own guard rule (within GUARD_NEAR of the drop or of the
# character, agenda.py DROP_GUARD); another goes after the drop. False: any kill target, as before.
GUARD_AT_DROP = True  # on 2026-10-23 ~19:50 (the player: "Turn both on"), gated: 0 new deaths over 1860 pairs
GUARD_AT_DROP_SAID = 'GUARD_AT_DROP'
# GUARD_STALL (2026-10-23, the same): a drop's guard fight that makes no progress kept the drop waiting: 145 s of
# deferrals 15:00-17:31 past 5 s with no kill (15:17:27, Rare Battle Gauntlets: 31 s, 0 kills, the guard behind the
# mana burn keep range). True: a guard fight with no kill or damage (NET_PROGRESS's rules) among the hostiles in the
# strike's reach or by the drop for GUARD_STALL_SECONDS frees the drop of its guards for PASS_SECONDS: the pickup is
# the goal, priced by the safety as any unguarded drop. False: the fight first however long, as before.
GUARD_STALL = False
GUARD_STALL_SECONDS = 5.0
GUARD_STALL_GAP = 2.0  # seconds between the drop's looks after which its watch begins again
GUARD_SAID: set[tuple[int | None, int]] = set()  # (drop, guard) said


def at_the_drop(guard: Monster, drop: Goal, here: Point) -> bool:
    """Whether `guard` guards `drop` by the agenda's rule: within GUARD_NEAR of the drop or of the character."""
    at = (guard.x, guard.y)
    return min(math.dist(at, drop.place), math.dist(at, here)) <= GUARD_NEAR


def said_guard(drop: Goal, guard: Monster, here: Point, why: str) -> None:
    """Says once a drop and guard why the drop goes before its guard fight."""
    key = (drop.unit, guard.unit_id)
    if key in GUARD_SAID:
        return
    if len(GUARD_SAID) > 200:
        GUARD_SAID.clear()
    GUARD_SAID.add(key)
    LOG.info(
        "Macro: run: %s at (%.0f, %.0f): %s %.0f from it, %.0f from the character: %s",
        drop.label, *drop.place, label(guard), math.dist((guard.x, guard.y), drop.place),
        math.dist((guard.x, guard.y), here), why,
    )  # fmt: skip


def guard_stalled(self: Hunter, world: World, drop: Goal, here: Point, now: float) -> bool:
    """GUARD_STALL: whether the drop is freed of its guards: freed before and still, or now, after GUARD_STALL_SECONDS
    with no progress among the hostiles in the strike's reach or within GUARD_NEAR of the drop."""
    if not GUARD_STALL or drop.unit is None:
        return False
    if now < self.guards_freed.get(drop.unit, -math.inf):
        return True
    from inventory_tracking.macros.hunting import judging  # judging imports this module

    near = [
        m
        for m in world.monsters
        if not m.ally
        and m.owner == NO_OWNER
        and (math.dist(here, (m.x, m.y)) <= self.reach or math.dist(drop.place, (m.x, m.y)) <= GUARD_NEAR)
    ]
    dead = frozenset(m.unit_id for m in near if m.mode in (0, LYING_DEAD))
    lives = {m.unit_id: m.life for m in near if m.mode not in (0, LYING_DEAD) and m.life > 0}
    raised = self.slain[1] if judging.NET_PROGRESS else frozenset()
    watch = self.guard_watch
    if (
        watch is None
        or watch[0] != drop.unit
        or now - watch[2] > GUARD_STALL_GAP
        or judging.progressed(dead, lives, watch[3], watch[4], raised)
    ):
        self.guard_watch = (drop.unit, now, now, dead, lives)  # the clock starts at the last progress
        return False
    # The clock's snapshot of each life stays (NET_PROGRESS: what grew back is no bar raised); new ones added
    self.guard_watch = (drop.unit, watch[1], now, watch[3] | dead, {**lives, **watch[4]})
    if now - watch[1] < GUARD_STALL_SECONDS:
        return False
    if len(self.guards_freed) > 200:
        self.guards_freed.clear()
    self.guards_freed[drop.unit] = now + PASS_SECONDS
    self.guard_watch = None
    LOG.info(
        'Macro: run: %s at (%.0f, %.0f): its guard fight made no progress in %.0f s: the drop first for %.0f s '
        '(GUARD_STALL)',
        drop.label, *drop.place, now - watch[1], PASS_SECONDS,
    )  # fmt: skip
    return True


def boss_in_sight(found: Goal | None, foes: Sequence[Monster]) -> bool:
    """Whether `found` is the route's boss fight (a FIGHT stage's) with its boss in `foes` (ROUTE_BOSS_FIRST)."""
    if found is None or found.do != FIGHT or found.unit is None or found.stage is None or found.stage.kind != FIGHT:
        return False
    return any(m.unit_id == found.unit for m in foes)


def agenda_cleared(
    self: Hunter, run: Run, world: World, foes: list[Monster], ground: Ground, found: Goal | None
) -> Goal | None:
    """The terror zone kinds' run (goals-plan.md §3): the agenda's next target (agenda.py `Agenda.in_level`), then
    the route's `found`; passing and the way cleared as a full clear's (leaders only, unless a Full clear TZ). A
    drop's guards are the fight first ("we may need some kill action near pickup item, then pickup")."""
    player = world.player
    assert player is not None
    here, now, area = (player.x, player.y), run.clock(), player.area
    level = self.known_level(player)
    rooms = level.rooms if level is not None else ()
    self._forget_passed(now)
    if found is not None and (found.do == WAIT or found.guarded):
        return found
    if ROUTE_BOSS_FIRST and boss_in_sight(found, foes):
        return found
    if found is not None and found.do == PICK_UP:
        side = Objective(SIDE, found.label, 3, area, found.place, found.unit)
        target = self.agenda_target(run, world, foes, here, frozenset(), rooms, side)
        guard = next((m for m in foes if target is not None and target.kind == KILL and m.unit_id == target.unit), None)
        if guard is None:
            return found
        if GUARD_AT_DROP and not at_the_drop(guard, found, here):
            said_guard(found, guard, here, f'no guard of it: the drop first ({GUARD_AT_DROP_SAID})')
            return found
        if guard_stalled(self, world, found, here, now):
            return found
        # `clearing`: on a level with no route a plain fight goal ended the run (Great Marsh, 2026-10-19 09:01:51)
        return replace(first_fight(found, here, [guard], self.reach), clearing=True)
    spend = found.spend if found is not None else PRESSED
    policy = level_policy(self, world, area) if self.agenda_policy is not None else None
    if policy == ZONE_LEFT:
        if self.zone_left != (world.game_name, area):
            self.zone_left = (world.game_name, area)
            LOG.info('Macro: run: %s is no longer terrorized: the level run ends', display_name(area))
        return None
    if policy == SKIPPED:
        return None  # not worth playing on (macros/zonenav.py `worth`, said by tzloop.py `worth_skip`): the run ends
    everyone, crossed = policy == FULL_CLEAR, policy == TRANSIT
    bosses_only = policy == BOSS_WAY  # BOSSES_ONLY: what strikes at the party alone fought on the way
    things = run.things() if run.things is not None else ()  # read once a look

    # The route's next object on this level (a seal, a chest; not a portal): beside the character it goes before a
    # farther room (agenda.py USE_FIRST)
    use_at = (
        found.place
        if found is not None
        and found.do == USE
        and found.stage is not None
        and found.stage.kind == USE
        and not found.stage.to
        and not found.stage.pending
        and not (found.mark is not None and found.mark.warp)
        else None
    )
    if use_at is None and found is not None and self.agenda is not None:
        # Zone navigation: a child's way in beside the run goes before a farther room ("Enter when passing", the
        # player, 2026-10-21 ~09:35; macros/zonenav.py `enter_at`, ENTER_PASSING): in, cleared, climbed out of, then
        # the parent's rooms
        use_at = zonenav.enter_at(self.agenda.plan, found.stage, found.place)

    def candidate(skip: frozenset[object]) -> Goal | None:
        target = self.agenda_target(run, world, foes, here, skip, rooms, None, things, use_at)
        if target is None:
            # The level's super chests before the route's own goal, a crossed level's left (superchests.py LEVEL_SPOTS)
            base = (None if crossed else level_chest(self, run, world, rooms, things, skip, found, spend)) or found
        elif target.kind == OPEN:
            base = self.agenda_chest(area, target, found, spend, things)
        else:
            unit = target.unit if target.kind == KILL else None
            assert target.place is not None
            base = rest_of_level((target.place, target.label, unit), found, self.reach, spend)
        if base is None or (base is found and found is not None and found.do == FIGHT):
            return base

        # A level only crossed (TRANSIT) fights nothing on its way but what strikes at the party; on TZ+ a remnant
        # is no fight on the way, whatever it does (agenda.py REMNANTS_LEFT): struck in reach, never gone to
        def leading(m: Monster) -> bool:
            return bool(everyone or m.leader or m.tier) and m.unit_id not in left

        near = [] if crossed or bosses_only else self._on_the_way(world, ground, foes, here, skip, leading)
        if not near and (ENGAGE_STRIKERS or crossed or bosses_only):
            # What strikes at the party is met, not waited for (ENGAGE_STRIKERS)
            near = self._on_the_way(
                world, ground, foes, here, skip, lambda m: m.mode in STRIKING_MODES and m.unit_id not in left
            )
        return clear_way(base, here, near, self.reach) if near else base

    left = remnants_of(foes, policy or '', lambda m: m.unit_id not in self.untouchable and on_rooms(rooms, m))
    return self._clear_through(candidate, run, world, ground, rooms, found, now)


def level_policy(self: Hunter, world: World, area: int) -> str:
    """How the level run works `area` (running/legs.py `_agenda_policy`), a level the zone left with a boss of the
    ledger alive on it or under it worked on the way (BOSS_ROTATION), said once a level a game."""
    assert self.agenda_policy is not None
    policy = self.agenda_policy(area)
    if policy != ZONE_LEFT or not BOSS_ROTATION or self.agenda is None:
        return policy
    alive = boss_held(self.agenda, area)
    if not alive:
        return policy
    if self.zone_left != (world.game_name, -area):
        self.zone_left = (world.game_name, -area)
        # The watch tools may read it (d2-loop-watch logwords.py)
        LOG.info('Macro: run: %s is no longer terrorized, %s alive: the level run goes on for them', display_name(area),
                 ', '.join(boss.name for boss in alive))  # fmt: skip
    return BOSS_WAY if BOSSES_ONLY else ON_THE_WAY


def boss_held(agenda: goal_agenda.Agenda, area: int) -> list[Boss]:
    """The ledger's bosses alive on `area` or on a level it holds in the zone's graph (zonenav.py `boss_reach`: under
    it, the tour side level it leads into)."""
    plan = agenda.plan
    if not isinstance(plan, Itinerary) or not zonenav.on(plan):
        return agenda.bosses.alive_in(area)
    return agenda.bosses.alive(zonenav.boss_reach(zonenav.graph_of(plan), area))


def on_rooms(rooms: Sequence[Room], monster: Monster) -> bool:
    """Whether `monster` stands in one of `rooms` (this level's read; none read: no)."""
    return room_at(rooms, (monster.x / TILE_UNITS, monster.y / TILE_UNITS)) is not None


def remnants_of(foes: Sequence[Monster], policy: str, mine: Callable[[Monster], bool]) -> frozenset[int]:
    """The remnants among `foes` of this level (`mine`) on TZ+ (agenda.py `remnants`, REMNANTS_LEFT): in a group of
    fewer than GROUP_MIN with no leader in it. None on another policy, or with the switch off."""
    if not (goal_agenda.REMNANTS_LEFT and policy in GROUPS_TAKEN):
        return frozenset()
    level = [m for m in foes if mine(m)]
    return goal_agenda.remnants([(m.unit_id, (m.x, m.y)) for m in level], {m.unit_id for m in level if m.leader})


# AGENDA_SAID_ONCE (2026-10-22, walled-boss-findings.md): only the look's own ask says the agenda's target. False: every
# ask, `taken_back`'s too, as before
AGENDA_SAID_ONCE = True


def agenda_target(
    self: Hunter,
    run: Run,
    world: World,
    foes: Sequence[Monster],
    here: Point,
    skip: frozenset[object],
    rooms: Sequence[Room],
    side: Objective | None,
    things: Sequence[Thing] = (),
    use_at: Point | None = None,
) -> Objective | None:
    """The agenda's next target on this level (agenda.py `Agenda.in_level`) from what this look knows: leaders,
    hostiles, omens, the side drop, super chests, the next unexplored room (lazily), the goals passed, the route's
    next object (`use_at`)."""
    agenda, player = self.agenda, world.player
    assert agenda is not None
    assert player is not None
    area, now = player.area, run.clock()
    policy = level_policy(self, world, area) if self.agenda_policy is not None else FULL_CLEAR
    if policy in (ON_THE_WAY, PLUS_WAY, BOSS_WAY, SHORT) and (world.game_name, area) in self.wayless:
        # no way to the route's goal: the rooms are explored for it (`judge`); a shortened level too (SHORT_LEVELS)
        policy = PLUS if policy in (PLUS_WAY, SHORT) else COVER
    everyone = policy == FULL_CLEAR
    population = level_population(area, len(rooms) or None)
    agenda.worked_as(area, policy, population)
    out = skip | set(self.passed)

    def here_on(x: float, y: float) -> bool:
        # A leader of this level only: the client holds the level before's for a moment after a crossing, and a River
        # of Flame elite chased from the Chaos Sanctuary's side took the run back across before its map was read
        # (08:43:48 on 2026-10-20, rca/2026-10-20/crossing-teleport-back-findings.md F1). No rooms read: none
        return room_at(rooms, (x / TILE_UNITS, y / TILE_UNITS)) is not None

    # A Herald's minion is a leader to go for unless it is a remnant (agenda.py REMNANTS_LEFT): its Herald dead, a
    # pair left (2026-10-21 21:37:51, Frigid Highlands: 11 Teleports in 12 s between two Demon Rascals for 1 kill)
    left = remnants_of(foes, policy, lambda m: m.unit_id not in self.untouchable and here_on(m.x, m.y))
    live = [m for m in foes if (everyone or m.leader or (m.tier and m.unit_id not in left)) and here_on(m.x, m.y)]
    if agenda.plan is not None and policy != TRANSIT:
        # The game's boss ledger (macros/bossledger.py): the super uniques this level's rooms place, and the one in
        # the read taken for each. A level only crossed is no boss's (the player, 2026-10-22: "no need to kill hepasto
        # if it is just travel through")
        agenda.bosses.rooms(area, rooms)
        agenda.bosses.sight(area, [m for m in foes if here_on(m.x, m.y)])
    raising = revivers.raising((m.unit_id, m.txt_id, (m.x, m.y), m.flags) for m in foes)
    leaders = [
        Leader(m.unit_id, (m.x, m.y), label(m), bool(m.tier and m.leader), reviver=m.unit_id in raising) for m in live
    ]
    seen = {m.unit_id for m in foes}
    gone = seen | self.vanished | set(self.untouchable)
    known = self.remembered(area) if self.remembered is not None else []
    leaders += [
        Leader(unit, (x, y), 'the remembered monster', live=False)
        for unit, x, y, leader in known
        if unit not in gone and (everyone or leader) and here_on(x, y)
    ]
    omens = tuple((spot, omen_stand(spot, here, rooms)) for spot in self.omens_now(run, area, now))

    def frontier() -> tuple[Point, str] | None:
        room = self.next_room(run, player, area, now)
        return (room[0], room[1]) if room is not None else None

    view = LevelView(
        area,
        here,
        tuple(leaders),
        tuple((m.unit_id, (m.x, m.y)) for m in foes),
        omens,
        side,
        frontier,
        policy,
        lambda place, unit: passing_key(place, unit, rooms) in out or (unit is not None and unit in out),
        OMEN_NEAR,
        *self.agenda_chests(things, rooms),
        use_at=use_at,
        # TZ+'s groups (agenda.py `groups_near`): this level's hostiles in the read, none left alone for now
        crowd=tuple((m.unit_id, (m.x, m.y)) for m in foes if m.unit_id not in self.untouchable and here_on(m.x, m.y))
        if policy in GROUPS_TAKEN
        else (),
        population=population,
        # agenda.py HELD_GOALS: the level's hostiles remembered alive out of the read (the tracker forgets one not where
        # it was seen), at their last places: the held group's members on its way round
        unseen=tuple((unit, (x, y)) for unit, x, y, _ in known if unit not in gone and here_on(x, y))
        if policy in GROUPS_TAKEN and goal_agenda.HELD_GOALS
        else (),
        present=frozenset(m.unit_id for m in hostiles(world)),  # bossledger.py BOSS_ABSENT: untouchable ones too
    )
    target = agenda.in_level(view)
    said = (target.kind, target.unit, target.label) if target is not None else None
    # The look's own target only: `taken_back`'s second ask (a goal left for another skipped) is no change of target;
    # said, it flipped the log 20 times in 13 s at 23:09:55 on 2026-10-22 with one goal held (walled-boss-findings.md)
    if said != self.agenda_said and not (AGENDA_SAID_ONCE and skip):
        self.agenda_said = said
        if target is None:
            LOG.info("Macro: agenda: no target here: the route's own goal")
        else:
            LOG.info('Macro: agenda: target %s (%s, tier %d, %d leaders known here)', target.label, target.kind,
                     target.tier, agenda.known(area))  # fmt: skip
    return target


def level_chest(
    self: Hunter,
    run: Run,
    world: World,
    rooms: Sequence[Room],
    things: Sequence[Thing],
    skip: frozenset[object],
    found: Goal | None,
    spend: Intent,
) -> Goal | None:
    """The level's next super chest or chest spot (superchests.py `level_goal`), its tries and passes the run's."""
    player = world.player
    assert player is not None
    out = skip | set(self.passed)
    return level_goal(
        world.game_name, player.area, (player.x, player.y), rooms, things, self.shack_tries,
        lambda place, unit: passing_key(place, unit, rooms) in out or (unit is not None and unit in out),
        run.clock(), spend, found.route if found is not None else '',
    )  # fmt: skip


def agenda_chests(
    self: Hunter, things: Sequence[Thing], rooms: Sequence[Room] = ()
) -> tuple[tuple[tuple[int, Point], ...], frozenset[int]]:
    """Super chests among `things` for the agenda's CHEST tier ("open them along the way", the player, 2026-10-19):
    (closed (unit, place)s, units open or tried SUPER_TRIES times). The glowing ones and, on `rooms`, the chests at
    the unique-chest spots (superchests.py: the Maggot Lair's, "we need to open superchests when we encountering
    them", the player, 2026-10-20)."""
    closed, spent = [], set()
    for thing in super_chests(things, rooms):
        if thing.mode != 0 or self.shack_tries.get(thing.unit_id, 0) >= SUPER_TRIES:
            spent.add(thing.unit_id)
        elif thing.selectable is not False:
            closed.append((thing.unit_id, (thing.x, thing.y)))
    # Tried out though out of sight: a goal's unit the client has since named anew is left all the same
    spent.update(unit for unit, tries in self.shack_tries.items() if tries >= SUPER_TRIES)
    return tuple(closed), frozenset(spent)


def agenda_chest(
    self: Hunter, area: int, target: Objective, found: Goal | None, spend: Intent, things: Sequence[Thing] = ()
) -> Goal:
    """The agenda's OPEN `target` as a clearing goal, opened as `super_chest_goal`'s; `found`'s route kept for the
    log. `things`: this look's objects, the chest's class among them (superchests.py `mark_use`)."""
    assert target.place is not None
    x, y = target.place
    use = mark_use(next((thing for thing in things if thing.unit_id == target.unit), None))
    mark = Target(area, (), (x / TILE_UNITS, y / TILE_UNITS), 'Super chest', 'target', use=use)
    route = found.route if found is not None else ''
    return Goal(f'agenda: {target.label}', (x, y), USE, USE_NEAR, spend, unit=target.unit, mark=mark, route=route,
                clearing=True)  # fmt: skip


def goal_key(self: Hunter, goal: Goal | None, rooms: Sequence[Room]) -> object | None:
    """The key a level run's goal is judged and left by: a clearing goal's `passing_key`, the route's by itself."""
    if goal is None:
        return None
    return passing_key(goal.place, goal.unit, rooms) if goal.clearing else ('the run', goal.label, goal.do)


def taken_back(
    self: Hunter, candidate: Callable[[frozenset[object]], Goal | None], rooms: Sequence[Room], found: Goal | None
) -> Goal | None:
    """The run's next goal, unless it is a clearing goal left for another within TAKE_BACK that would still be the
    goal without it: then that other. The other gone, the goal left is taken back."""
    goal = candidate(frozenset())
    key = self.goal_key(goal, rooms)
    left = self.left_for.get(key) if goal is not None and goal.clearing else None
    if left is None:
        return goal
    other = candidate(frozenset((key,)))
    if other is not None and self.goal_key(other, rooms) == left[1]:
        return other
    return goal


def went_for(self: Hunter, chosen: Goal | None, rooms: Sequence[Room], now: float) -> None:
    """Note this look's goal: the last look's clearing goal is left for this one (TAKE_BACK) unless passed. The
    route's own goal is never left so."""
    key = self.goal_key(chosen, rooms)
    went, self.went = self.went, key
    if went is None or chosen is None or not chosen.clearing or went == key or went in self.passed:
        return
    if isinstance(went, tuple) and went[:1] == ('the run',):
        return  # the route's own goal: what the run is for
    if len(self.left_for) > 200:
        self.left_for.clear()
    self.left_for[went] = (now + TAKE_BACK, key)


def goes_on(
    self: Hunter, run: Run, world: World, ground: Ground, goal: Goal, rooms: Sequence[Room], now: float
) -> bool:
    """Whether a clearing goal is still gone for: False (and passed) after CLEAR_SECONDS with no strike and no eta
    progress of PROGRESS_SECONDS, ARRIVED_SECONDS once a place goal is reached. The eta is asked once in PROGRESS_LOOK
    and before a pass (a cold field is costly: rca/2026-10-14/run-2040-findings.md)."""
    key = passing_key(goal.place, goal.unit, rooms)
    judging = self.judging.get(key)
    if judging is None:
        if len(self.judging) > 400:
            self.judging = {k: j for k, j in self.judging.items() if now - j.last <= PASS_SECONDS}
        judging = self.judging[key] = Judging(0.0, math.inf, now)
    gap = now - judging.last
    struck = self.struck_at > judging.last
    judging.last = now
    if struck:
        judging.idle = 0.0
        return True
    if self.went == key or gap <= JUDGE_GAP:  # the last look's goal too, or another's a moment
        judging.idle += gap
    if now - judging.checked >= PROGRESS_LOOK or judging.idle > CLEAR_SECONDS:
        rect = run.actuator.keys.focused_window_rect()
        aspect = rect[2] / rect[3] if rect is not None else 16 / 9
        eta = self.travel.eta(run, world, ground, aspect, goal.place, goal.spend, tuple(rooms))
        judging.checked = now
        if eta <= judging.best - PROGRESS_SECONDS:
            judging.idle, judging.best = 0.0, eta
            return True
    player = world.player
    # A room's stop stood at with nothing struck shows nothing more: ARRIVED_SECONDS, not CLEAR_SECONDS (10 s by
    # hostiles at 21:05:24 and 22:00:32 on 2026-10-19; rca/2026-10-19/tz-leveling-findings.md C1)
    # Not a Herald's stand, which is waited at
    at = goal.label.endswith(UNEXPLORED) and player is not None and goal.gap((player.x, player.y)) <= goal.near
    if judging.idle <= (ARRIVED_SECONDS if at else CLEAR_SECONDS):
        return True
    why = (
        f'stood at it {ARRIVED_SECONDS:.0f} s with no strike'
        if at
        else f'no strike and no progress by the way in {CLEAR_SECONDS:.0f} s on the way to it'
    )
    self.pass_by(goal, why, now, rooms)
    return False


def on_the_way(self: Hunter, run: Run, here: Point, drop: Drop, world: World | None, *, looped: bool = False) -> bool:
    """Whether a valuable is on the way: PICK_NEAR walked, not straight (straight made the run warp back and forth:
    rca/2026-10-14/run-1932-findings.md §1.2.3). `looped`: the KP_6 loop also takes what Teleport brings it to."""
    if self.walked_near(run, here, drop, world):
        return True
    return looped and self.teleport_reach(run, here, drop, world)


def walked_near(self: Hunter, run: Run, here: Point, drop: Drop, world: World | None) -> bool:
    """Whether `drop` is within PICK_NEAR of `here` by walking (travel.py `walked_length`)."""
    place = (drop.x, drop.y)
    if math.dist(here, place) > PICK_NEAR:
        return False
    world = world if world is not None else run.world()
    level = self.known_level(world.player) if world.player is not None else None
    ground = Ground(level.ground) if level is not None else None
    return walked_length(ground, world.doors, here, place) <= PICK_NEAR


def teleport_reach(self: Hunter, run: Run, here: Point, drop: Drop, world: World | None) -> bool:
    """Whether the way to `drop` is Teleport hops within LOOP_PICK_SECONDS (a Ko Rune 117 walked was left,
    2026-10-18 18:22:17). Judged once in FAR_JUDGED a drop, said on change."""
    now = run.clock()
    judged = self.far_judged.get(drop.unit_id)
    if judged is not None and 0.0 <= now - judged[0] < FAR_JUDGED:
        return judged[1]
    world = world if world is not None else run.world()
    player, rect = world.player, run.actuator.keys.focused_window_rect()
    level = self.known_level(player) if player is not None else None
    found, eta = False, math.inf
    if level is not None and rect is not None:
        ground, aspect, place = Ground(level.ground), rect[2] / rect[3], (drop.x, drop.y)
        intent = self.looped_now(now)
        if self.travel.means(run, world, ground, aspect, place, intent, level.rooms) == HOPS:
            eta = self.travel.eta(run, world, ground, aspect, place, intent, level.rooms)
            found = eta <= LOOP_PICK_SECONDS
    if len(self.far_judged) > 200:
        self.far_judged.clear()
    said = judged is not None and judged[1] == found
    self.far_judged[drop.unit_id] = (now, found)
    if not said:
        LOG.info(
            'Macro: run: %s at (%.0f, %.0f), %.0f away: %s',
            drop.label, drop.x, drop.y, math.dist(here, (drop.x, drop.y)),
            f'Teleport brings it in {eta:.1f} s: taken now, the run waits'
            if found
            else f'not taken from here: no Teleport way within {LOOP_PICK_SECONDS:g} s (eta {eta:.1f} s)',
        )  # fmt: skip
    return found


def pass_by(self: Hunter, goal: Goal, why: str, now: float, rooms: Sequence[Room] = ()) -> None:
    """A level run's clearing goal is passed for PASS_SECONDS from `now` (`cleared`), said."""
    if len(self.passed) > 400:
        self.passed.clear()
    key = passing_key(goal.place, goal.unit, rooms)
    self.passed[key] = now + PASS_SECONDS
    self.judging.pop(key, None)
    self.rest = None  # the tour's next stop is looked for again (`next_room`)
    LOG.info('Macro: run: passing %s at (%.0f, %.0f): %s', goal.label, *goal.place, why)


def rest_of(
    self: Hunter,
    run: Run,
    world: World,
    foes: list[Monster],
    here: Point,
    skip: frozenset[object] = frozenset(),
    rooms: Sequence[Room] = (),
) -> tuple[Point, str, int | None] | None:
    """A full clear's next (place, what, unit): a Herald, an omen's pack or stand, the nearest hostile in sight, the
    nearest remembered alive, the next unexplored room (unit None), the rest remembered. None: clear as far as
    known. Passed goals and `skip` (`passing_key`s) are not gone for."""
    player = world.player
    assert player is not None
    area, now = player.area, run.clock()
    out = skip | set(self.passed)
    live = [m for m in foes if m.unit_id not in out]
    heralds = [m for m in live if m.tier and m.leader]
    if heralds:  # a Herald first, wherever the others stand (HERALD_OMEN)
        herald = min(heralds, key=lambda m: math.dist(here, (m.x, m.y)))
        return (herald.x, herald.y), label(herald), herald.unit_id
    spots = self.omens_now(run, area, now)
    if spots:
        spot = min(spots, key=lambda s: math.dist(here, s))
        near = [m for m in live if math.dist(spot, (m.x, m.y)) <= OMEN_NEAR]
        if near:
            nearest = min(near, key=lambda m: math.dist(here, (m.x, m.y)))
            return (nearest.x, nearest.y), label(nearest), nearest.unit_id
        stand = omen_stand(spot, here, rooms)
        if passing_key(stand, None, rooms) not in out:
            return stand, 'the stand for the Herald coming', None
    if live:
        nearest = min(live, key=lambda m: math.dist(here, (m.x, m.y)))
        return (nearest.x, nearest.y), label(nearest), nearest.unit_id
    known = self.remembered(area) if self.remembered is not None else []
    seen = {m.unit_id for m in foes}
    gone = seen | self.vanished | set(self.untouchable) | out
    kept = [(x, y, unit) for unit, x, y, _leader in known if unit not in gone]
    near = [k for k in kept if math.dist(here, (k[0], k[1])) <= REMEMBERED_NEAR]
    if near:
        x, y, unit = min(near, key=lambda k: math.dist(here, (k[0], k[1])))
        return (x, y), 'the remembered monster', unit
    room = self.next_room(run, player, area, now)
    if room is not None and passing_key(room[0], None, rooms) not in out:
        return room
    if kept:
        x, y, unit = min(kept, key=lambda k: math.dist(here, (k[0], k[1])))
        return (x, y), 'the remembered monster', unit
    return None


REFUSED_ROOM = 30.0  # units round a refused fight's places no tour stop is taken within (judging.py REFUSED_PASS)


def refused_near(self: Hunter, place: Point, now: float) -> bool:
    """REFUSED_PASS (judging.py): whether `place` is within REFUSED_ROOM of a fight the safety kept refusing, while it
    is passed (`Hunter.refused_places`; empty with the switch off)."""
    return any(now < until and math.dist(place, at) <= REFUSED_ROOM for at, until in self.refused_places)


def next_room(self: Hunter, run: Run, player, area: int, now: float) -> tuple[Point, str, int | None] | None:
    """The first stop of the tour of the rooms not explored yet (`frontier`) that is not passed, looked for once in
    REST_SECONDS (a pass looks again, `pass_by`)."""
    cached = self.rest
    if cached is not None and cached[1] == area and now - cached[0] < REST_SECONDS:
        room = cached[2]
    else:
        level, rect = self.known_level(player), run.actuator.keys.focused_window_rect()
        rooms = level.rooms if level is not None else ()

        def passed(place: Point) -> bool:
            return passing_key(place, None, rooms) in self.passed or refused_near(self, place, now)

        kept = self.stop_kept[1] if self.stop_kept is not None and self.stop_kept[0] == area else None
        stop = self.frontier(level, player, rect, passed, kept) if level is not None and rect is not None else None
        room = None
        self.stop_kept = None
        if stop is not None:
            _, chosen, (x, y) = stop
            room = ((x + 0.5) * TILE_UNITS, (y + 0.5) * TILE_UNITS), 'an unexplored room', None
            self.stop_kept = (area, (chosen.x, chosen.y, chosen.width, chosen.height))
        # None is not kept: a look with no stop (no window, the card not up) ended the run on the next looks
        # (rca/2026-10-19/tz-coverage-findings.md item 5)
        self.rest = (now, area, room) if room is not None else None
    return room


def run_mode(self: Hunter, run: Run, area: int, posted: Pursuit | None) -> Mode:
    """The run mode on `area` (runmode.py): a closed double press of the pickup key switches it for this level; a
    switch on another level lapses. Said on change."""
    now = run.clock()
    if self.switched is not None and self.switched[0] != area:
        self.switched = None
    with self.mailbox:
        pairs, self.taps = doubles(self.taps, now)
    # No TZ full clear on KP_6 loops: "focus on reaching chests as fast as possible" (the player, 2026-10-16);
    # "andy loop shouldn't focus on full clearing level. we're going to have separate mods" (2026-10-19)
    terror = self.bearings.terror(area) and not (posted is not None and (posted.rush or posted.looped))
    for first, last in pairs:
        # Every double press, also one no look saw in its window (runmode.py `owed`)
        before = mode_of(area, terror, self.switched)
        self.switched = (area, not before.clear)
        was, then = ('full clear', 'goal') if before.clear else ('goal', 'full clear')
        closed = now - last - DOUBLE  # seconds its window had been closed at this look
        late = '' if closed <= DOUBLE else f', its window closed {closed:.2f} s before this look'
        LOG.info(
            'Macro: run: a double press of the pickup key (%.2f s apart%s): %s -> %s', last - first, late, was, then
        )
    if posted is not None and posted.agenda:
        mode = Mode(True, AGENDA, agenda=True)
    else:
        mode = mode_of(area, terror, self.switched)
    self.mode = mode
    if posted is not None and posted.leashed:
        line = said(mode, aim_of(self.bearings.script(area)))
        if self.mode_said != (area, line):
            self.mode_said = (area, line)
            LOG.info('Macro: run: %s', line)
            run.say(f'Run: {line}')
    return mode


def carry_on(self: Hunter, run: Run, left: Pursuit, onward: Pursuit) -> None:
    """The run walked across an open passage and goes on as the next level's ("it should carry into the Chaos
    Sanctuary run", the player, 2026-10-15). A switched-to full clear carries; a switch to the goal does not. The
    left level's pace is said, the next counts anew."""
    assert left.area is not None
    assert onward.area is not None
    if self.switched is not None and self.switched[0] == left.area:
        self.switched = (onward.area, True) if self.switched[1] else None
    name, now = display_name(onward.area), run.clock()
    LOG.info('Macro: run: on into %s: the run of %s goes on across its way out', name, display_name(left.area))
    self.travel.paced(now, f'on into {name}')
    self.told.new(None)
    run.say(f'Run: on into {name}')


def nearby(self: Hunter, goal: Goal | None, here: Point) -> Goal | None:
    """Attack mode's own goal: a boss's fight only within ALONE_BOSS_UNITS ("only nearby", the player,
    2026-10-15), said once a goal."""
    if goal is None or goal.do != FIGHT or not goal.known or goal.gap(here) <= ALONE_BOSS_UNITS:
        return goal
    if self.far_said != goal.label:
        self.far_said = goal.label
        LOG.info(
            'Macro: attack mode: %s is %.0f away from (%.1f, %.1f), beyond %.0f: not gone to without a press '
            '(KP_1 runs the level to it, KP_4 steps toward it)',
            goal.label, goal.gap(here), *here, ALONE_BOSS_UNITS,
        )  # fmt: skip
    return None
