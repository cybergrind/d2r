"""Call to Arms: Battle Command and Battle Orders kept on the character, for any build that wears one ("we need to use
it and keep it's buff active", the player, 2026-10-17).

Battle Orders and Battle Command have no `InTown` (skills.txt), so the town prebuff cannot cast them: an upkeep row
does (`ROWS`), at a look outside town with Battle Orders not shown (states.txt `battleorders`), and before it ends
(RENEW_ORDERS: `renew_orders`, and at an arrival's swap `cast_in_hand`). A cast lasts ORDERS_LASTS (its time left is
not read: it is counted from the last cast that took, `Run.lasting`). Battle Command goes first: its +1 to all skills
raises the Battle Orders after it.

A Call to Arms is read from the item (a weapon giving Battle Orders, game/records.py `gives_orders`). The caster swaps
to it, casts, and swaps back to the set it found in hand.
"""

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from inventory_tracking.combat.threats import dolls
from inventory_tracking.common import LOG
from inventory_tracking.game.memory import CTA_CODE
from inventory_tracking.game.records import World
from inventory_tracking.macros.actuator import Abort, Hand
from inventory_tracking.macros.buffs import HURT_SECONDS, STATE_RETRY
from inventory_tracking.macros.build import Buff, BuffFacts, Casting, Tried
from inventory_tracking.macros.goals import CLEAR_WAY
from inventory_tracking.macros.routines import ACTING, cast as cast_free, swap_until
from inventory_tracking.macros.skills import SWAP_WEAPONS, register_names
from inventory_tracking.native.layout import BATTLE_ORDERS_SKILL, TOWN_IDS


BATTLE_ORDERS = BATTLE_ORDERS_SKILL
BATTLE_COMMAND = 155
register_names({BATTLE_ORDERS: 'Battle Orders', BATTLE_COMMAND: 'Battle Command'})
# Seconds before a try that found no Call to Arms, or its skills on no key, is made again
MISSING_WAIT = 300.0
# Seconds before a try is made again whose swaps did not take or that the player's own input stopped: the Call to Arms
# is worn (`worn_and_in_front`), so the swaps were dropped (the player teleporting by hand every 0.6 s through a terror
# zone dropped all three, and the next try came 300 s later, 18:45 on 2026-10-19: "clear tz is not doing battle orders")
DROPPED_WAIT = 10.0
CAST_OVER = 1.0  # seconds at most for a cast to end before the weapons are swapped
# Seconds from the last cast's key before a weapon swap is taken, though the mode reads the cast over: 0.4 s was
# refused 25 in 26, 0.6 s taken 44 in 44 (2026-10-18 01:05-01:56)
SWAP_AFTER_CAST = 0.6
# 2026-10-22: Battle Orders ran out in the fight that killed the character (23:35:32.66 on 2026-10-21, the Disused
# Fane: max life 2943 -> 1896 with 57% of it left, the death 1.3 s later; 244 ran out in a level that day, 154 with a
# hostile within 20, 507 s fought without it; rca/2026-10-21/battle-orders-findings.md). It was cast only once it was
# gone. The player: "we must have top priority to no die ourselves and prevent loosing experience". True: cast again
# before it ends: in the quiet under QUIET_LEFT s left (or the boss fight ahead, `BuffFacts.ahead`) or with its cast
# not known (a restart); in a fight under FIGHT_LEFT s left, not hurt within HURT_SECONDS and with Teleport the
# character's own (no swap takes it away); at an arrival's swap under ARRIVAL_LEFT s or not known. False: cast only
# when it is not shown, as before.
RENEW_ORDERS = True
# The player, 2026-10-22, of danger-durance-1956 (seed 9: a tier 1 Herald's unique doll, one melee blow of 2982 against
# 2907 life, while the macro stood for Battle Orders and then blade-warped for its rebuff beside it): "you just aggro
# doll herald with death mark and then kill him VERY fast, because it has relatively low life even T5"
# True: while such a doll (combat/threats/dolls.py `herald_doll`) is alive within DOLL_HERALD_NEAR and Battle Orders is
# shown with its time left not known or over DOLL_KILL_SECONDS (quicker to kill the doll than for it to run out), it
# is not renewed (`renew_orders`) and not due for the safety (`orders_look`: no rebuff retreat beside the doll): the
# doll is killed first, marked before the first strike (builds/warlock/mark.py `mark_ahead`,
# `unmarked_herald`) and the strike's first target (echoing_strike/attack.py HOLD_LEADER). Run out, the rebuff's own
# rules (macros/safety.py REBUFF_RETREAT, REACH_BAR). False: as before.
DOLL_HERALD_FIRST = True
DOLL_HERALD_NEAR = 40.0  # units: a doll runs in at ~16 a second (combat/threats/dolls.py RUN_SPEED)
DOLL_KILL_SECONDS = 8.0
# Seconds a cast lasts: skills.txt `auralencalc` 750 + 250 a level after the first, in frames of 25 a second (the
# Shout and Battle Command synergies count hard points only: none on a Warlock): 180 s at level 16, the 180.6 s seen
# from the cast at 23:32:32.08 to its end on 2026-10-21. A shorter one (fewer + skills) runs out before its renewal and
# is cast when gone, as before; a longer one is renewed early.
ORDERS_LASTS = 180.0
# Seconds left under which it is cast again in the quiet. 30 would have missed the death: the service before the
# restart left Kurast Bazaar's quiet looks at 23:34:58 with 34 s left, and the next one went through the door into the
# Fane's pack with no upkeep; from 23:34:36 its quiet looks had under 60 s left. A cast every ~120 s, not ~180.
QUIET_LEFT = 60.0
FIGHT_LEFT = 10.0  # seconds left under which it is cast again in a fight
ARRIVAL_LEFT = 60.0  # seconds left under which it is cast at an arrival's swap (the set is in hand already)
QUIET_UNITS = CLEAR_WAY  # no hostile this near: the quiet (macros/hunting/base.py QUIET_UNITS)
FIGHT_WAIT = 2.0  # seconds before a renewal refused in a fight (Teleport on the swapped set) is asked again
# 2026-10-22: Battle Orders kept through a fight, the player's design ("probably we need to keep track of battle order
# and predict when it runs off, retreat and rebuff"). In the Fane's arena (tests/.../situations/fane_death.py, drawn,
# seed 15) it ran out at 8.68 s after 3.2 s unhurt at full life, and one blow of 2056 killed at 1896 most life: the
# strike bout never asked the upkeep, and a cast not known (a restart) was never renewed in a fight
# (rca/2026-10-21/fane-death-sim-findings.md §4). True:
# - tracked at every look (`Orders`, `orders_look`): the time left from the last cast that took (`Run.lasting`; the
#   client's state node holds an expiry, ai_d2_StateNode +0x24 in rca/2026-10-13/re/types.h, not read yet), not
#   known after a restart, and the most life it gives (`factor`);
# - with under FIGHT_LEFT s left, its age not known, or run out: cast in place when safe (no hostile within
#   ORDERS_CLEAR, not hurt within HURT_SECONDS; `cast_safe`), else the safety's retreat to a clear spot first
#   (macros/safety.py REBUFF_SAID) and the cast at its landing (REBUFF_GRACE);
# - the safety prices the fight with the most life after it runs out (macros/safety.py ORDERS_PREDICT);
# - the strike bout yields for it (macros/hunt.py `fight`).
# False: the renewal as before (FIGHT_LEFT, unhurt, its age known; an expiry cast at once wherever it is).
REBUFF = True
ORDERS_CLEAR = 10.0  # units: no hostile this near the character: safe to swap and cast in place (a swap and two casts)
REBUFF_GRACE = 2.0  # seconds after the safety chose a rebuff retreat: its landing casts, though just hurt
# Seconds after a run-out seen in a fight that the cast waits for the retreat; then it is cast where the character
# stands, as before (the cast gives the life back: 1896 -> 2943 most at the Fane)
EXPIRED_WAIT = 3.0
EXPIRED_RETRY = 0.3  # seconds before a cast held for the retreat is asked again
# Seconds at most the swap waits while the safety bars it (macros/safety.py CAST_REACH, `threat_hold`); then it goes
# where the character stands, as a run-out does after EXPIRED_WAIT
CAST_HOLD_MOST = 6.0
# The most life with it over the most without, until this game measures its own: the Fane's 2943 / 1896
# (23:35:32.67 on 2026-10-21)
ORDERS_FACTOR = 2943 / 1896
FACTOR_RANGE = (1.05, 3.0)  # a measured factor outside it (a gear change between the readings) is not taken
ORDERS_SAID = 'buff: Battle Orders'  # the start of the lines of this rule (the loop-watch's logwords.py ORDERS)


@dataclass
class Orders:
    """Battle Orders as tracked across looks (`track_of`): when it was last seen run out, the most life read with it
    on and with it off (its `factor`), the last rebuff retreat the safety chose, and the last line said."""

    shown: bool | None = None
    expired_at: float | None = None
    with_life: float | None = None
    bare_life: float | None = None
    rebuffed_at: float = -math.inf
    said: tuple[str, str] | None = None
    # Why the Call to Arms may not be swapped to now (macros/safety.py CAST_REACH), set by the hunt; None: not asked
    threat: Callable[[World], str | None] | None = field(default=None, repr=False)
    threat_since: float | None = None  # clock the swap was first held for it (`threat_hold`)

    @property
    def factor(self) -> float:
        """The most life with Battle Orders over without: measured this game, else ORDERS_FACTOR."""
        if self.with_life and self.bare_life:
            measured = self.with_life / self.bare_life
            if FACTOR_RANGE[0] <= measured <= FACTOR_RANGE[1]:
                return measured
        return ORDERS_FACTOR


@dataclass(frozen=True)
class OrdersLook:
    """What one look knows of Battle Orders: on or not, seconds left (None: not known), its factor on the most life,
    why it is cast again now (None: not due) and whether casting here is safe (`cast_safe`)."""

    shown: bool
    left: float | None
    factor: float
    due: str | None
    safe: bool
    at: float = 0.0  # the look's clock


def track_of(run) -> Orders:
    """The run's Battle Orders track, made at the first ask."""
    found = getattr(run, 'orders_track', None)
    if found is None:
        found = Orders()
        run.orders_track = found
    return found


def nearest_foe(world: World, foes) -> float:
    """Units from the character to the nearest of `foes`; inf with none."""
    player = world.player
    if player is None:
        return math.inf
    return min((math.dist((player.x, player.y), (m.x, m.y)) for m in foes), default=math.inf)


def cast_safe(world: World, foes, hurt: bool, rebuffed: float, now: float) -> bool:
    """Whether Battle Orders may be swapped to and cast here now (REBUFF): no hostile within ORDERS_CLEAR, and not
    `hurt` within HURT_SECONDS unless the safety chose a rebuff retreat within REBUFF_GRACE s (its landing)."""
    if nearest_foe(world, foes) <= ORDERS_CLEAR:
        return False
    return not hurt or now - rebuffed <= REBUFF_GRACE


def orders_state(shown: bool, left: float | None, expired_at: float | None, now: float) -> str:
    """The lines' first part: 'N s left', 'age not known' or 'expired N s ago'."""
    if not shown:
        return 'expired' if expired_at is None else f'expired {max(now - expired_at, 0.0):.1f} s ago'
    return 'age not known' if left is None else f'{max(left, 0.0):.0f} s left'


def say_orders(run, state: str, action: str) -> None:
    """Log `buff: Battle Orders: <state>: <action>` (retreat, cast in place, a retreat first), once while the words
    stay the same but for the seconds."""
    track = track_of(run)
    key = (re.sub(r'[\d.]+', 'N', state), action.split(' (', 1)[0])
    if track.said == key:
        return
    track.said = key
    LOG.info('Macro: %s: %s: %s', ORDERS_SAID, state, action)


def orders_look(
    run, world: World, foes, *, hurt: bool, max_life: float | None, worn: bool | None, barred: str | None = None
) -> OrdersLook | None:
    """Battle Orders at this look (REBUFF): the track updated (a run-out seen, the most life with it and without),
    its time left, its factor, why it is due (`due_now`) and whether a cast here is safe (not with `barred`: the
    safety's CAST_REACH, macros/safety.py `Safety.cast_threat`). None in town, unread, or with no Call to Arms worn."""
    shown = orders_shown(world)
    track = track_of(run)
    now = run.clock()
    if shown is None:
        return None
    if track.shown is True and not shown:
        track.expired_at = now
    if shown:
        track.expired_at = None
    track.shown = shown
    if max_life:
        if shown:
            track.with_life = float(max_life)
        else:
            track.bare_life = float(max_life)
    if worn is False:
        return None
    left = orders_left(run) if shown else 0.0
    safe = barred is None and cast_safe(world, foes, hurt, track.rebuffed_at, now)
    due = None if doll_first(world, foes, shown, left) is not None else due_now(shown, left)
    return OrdersLook(shown, left, track.factor, due, safe, now)


def due_now(shown: bool, left: float | None) -> str | None:
    """Why Battle Orders is cast again now in a fight (REBUFF); None: not due."""
    if not REBUFF:
        return None
    if not shown:
        return 'run out'
    if left is None:
        return 'its age is not known'
    return f'{max(left, 0.0):.0f} s left' if left < FIGHT_LEFT else None


def orders_shown(world: World) -> bool | None:
    """Whether the character shows Battle Orders; None in town, where it cannot be cast. Not read from the keys: the
    Call to Arms' skills are on keys only while it is in hand."""
    player = world.player
    if player is None or player.area in TOWN_IDS:
        return None
    return player.battle_orders


def doll_first(world: World, foes, shown: bool | None, left: float | None) -> str | None:
    """Why Battle Orders waits for a doll Herald's kill (DOLL_HERALD_FIRST): shown, its time left not known or over
    DOLL_KILL_SECONDS, such a doll alive within DOLL_HERALD_NEAR. None: not for that."""
    player = world.player
    if not DOLL_HERALD_FIRST or player is None or shown is not True:
        return None
    if left is not None and left <= DOLL_KILL_SECONDS:
        return None
    here = (player.x, player.y)
    near = [m for m in foes if dolls.herald_doll(m) and math.dist(here, (m.x, m.y)) <= DOLL_HERALD_NEAR]
    if not near:
        return None
    nearest = min(math.dist(here, (m.x, m.y)) for m in near)
    return f'a doll Herald {nearest:.0f} off: killed first'


def quiet(world: World, foes) -> bool:
    """No hostile of `foes` within QUIET_UNITS of the character (macros/hunt.py `quiet`); False with none seen."""
    player = world.player
    return player is not None and all(math.dist((player.x, player.y), (m.x, m.y)) > QUIET_UNITS for m in foes)


def orders_left(run) -> float | None:
    """Seconds left of the last Battle Orders that took (`Run.lasting`); None when none is known."""
    lasting = getattr(run, 'lasting', None)
    at = lasting.get(BATTLE_ORDERS) if lasting else None
    return None if at is None else ORDERS_LASTS - (run.clock() - at)


def renew_orders(facts: BuffFacts, left: float | None) -> str | None:
    """Why Battle Orders, shown still, is cast again now (RENEW_ORDERS, `Buff.renew`); None: not now. `left`: seconds
    left of its last cast that took, None when none is known."""
    if not RENEW_ORDERS or orders_shown(facts.world) is not True:
        return None
    if doll_first(facts.world, facts.foes, True, left) is not None:
        return None  # the doll Herald first (DOLL_HERALD_FIRST)
    if quiet(facts.world, facts.foes):
        if left is None:
            return 'its cast is not known (a restart or a cast by hand): cast in the quiet'
        within = max(QUIET_LEFT, facts.ahead)
        return (
            f'{max(left, 0.0):.0f} s left of {ORDERS_LASTS:.0f}, under {within:.0f} in the quiet'
            if left < within
            else None
        )
    if REBUFF:
        if due_now(True, left) is None:
            return None
        hurt = facts.hurt is None or facts.hurt()
        if facts.cast_barred is not None or not cast_safe(facts.world, facts.foes, hurt, facts.rebuffed, facts.now):
            return None  # the safety's retreat first (macros/safety.py REBUFF_SAID, CAST_REACH)
        state = orders_state(True, left, None, facts.now)
        how = 'at the rebuff landing' if hurt else f'not hurt within {HURT_SECONDS:.0f} s'
        return f'{state}: cast in place (nothing within {ORDERS_CLEAR:.0f}, {how})'
    if left is None or left >= FIGHT_LEFT or facts.hurt is None or facts.hurt():
        return None
    return f'{max(left, 0.0):.0f} s left of {ORDERS_LASTS:.0f} in a fight, not hurt within {HURT_SECONDS:.0f} s'


def worn_and_in_front(facts: BuffFacts) -> bool:
    """A Call to Arms is worn and the game is in front (a swap pressed into another window does nothing)."""
    return facts.cta is True and facts.focused()


def holding(run) -> bool | None:
    """Whether the Call to Arms is in hand; None when the hands cannot be read."""
    held = run.hands() if run.hands is not None else ()
    return CTA_CODE in held if held else None


def call_to_arms(cast: Casting) -> Tried:
    """Battle Command (when on a key), then Battle Orders, with the Call to Arms in hand, and the set found in hand back
    after. Swaps that did not take, or the player's input: asked again in DROPPED_WAIT; Battle Orders on no key: said,
    and asked again in MISSING_WAIT."""
    run, world = cast.run, cast.world
    assert world is not None
    assert cast.key_names is not None
    started = run.clock()
    if RENEW_ORDERS and fight_renewal(world) and run.reads.own_teleport() is not True:
        LOG.info(
            'Macro: Call to Arms: Battle Orders not renewed in a fight: Teleport is not the character\'s own (the swap '
            'would take it); asked again in %.0fs', FIGHT_WAIT,
        )  # fmt: skip
        return Tried.again(started, STATE_RETRY, FIGHT_WAIT)
    if REBUFF and orders_shown(world) is False:
        held = expired_hold(run, world, started)
        if held is not None:
            return held
    held = threat_hold(run, world, started)
    if held is not None:
        return held
    if run.hands is None or holding(run) is None:
        LOG.info('Macro: Call to Arms: the weapons in hand cannot be read; asked again in %.0fs', MISSING_WAIT)
        return Tried.again(started, STATE_RETRY, MISSING_WAIT)
    before, swapped = run.hands(), False
    try:
        run.keys.update(cast.key_names(world, (SWAP_WEAPONS,)))
        if not holding(run):
            swapped = True
            if not swap_until(run, lambda: bool(holding(run))):
                raise Hand('the swaps to the Call to Arms did not take')
        held = run.world()
        skills = tuple(skill for skill in (BATTLE_COMMAND, BATTLE_ORDERS) if skill in held.slots)
        if BATTLE_ORDERS not in skills:
            raise Abort('Battle Orders is on no key with the Call to Arms in hand')
        run.keys.update(cast.key_names(held, skills))
        run.say(
            'Call to Arms: ' + ', '.join('Battle Command' if s == BATTLE_COMMAND else 'Battle Orders' for s in skills)
        )
        for skill in skills:
            cast_free(run, skill)
    except (Abort, ValueError) as stop:
        if run.stops(stop):
            raise
        wait = DROPPED_WAIT if isinstance(stop, Hand) else MISSING_WAIT
        LOG.info('Macro: no Battle Orders (%s); asked again in %.0fs', stop, wait)
        return Tried.again(started, STATE_RETRY, wait)
    finally:
        if swapped and run.hands() != before and not swap_until(run, lambda: run.hands() == before):
            LOG.warning('Macro: Call to Arms: the weapons found in hand are not back after the swaps')
    return Tried(started, cast=True)


def expired_hold(run, world: World, started: float) -> Tried | None:
    """Battle Orders run out with a hostile within ORDERS_CLEAR (REBUFF): the cast waits EXPIRED_RETRY s for the
    safety's retreat (REBUFF_SAID), up to EXPIRED_WAIT s after the run-out; then, or clear of them, None: cast now."""
    from inventory_tracking.macros.hunting.base import hostiles  # late: the hunt's modules import this one

    track = track_of(run)
    now = run.clock()
    state = orders_state(False, None, track.expired_at, now)
    if nearest_foe(world, hostiles(world)) > ORDERS_CLEAR:
        say_orders(run, state, f'cast in place (nothing within {ORDERS_CLEAR:.0f})')
        return None
    if track.expired_at is not None and now - track.expired_at < EXPIRED_WAIT:
        say_orders(run, state, f'a retreat first (a hostile within {ORDERS_CLEAR:.0f})')
        return Tried.again(started, STATE_RETRY, EXPIRED_RETRY, touched=False)
    say_orders(run, state, f'cast in place (no retreat in {EXPIRED_WAIT:.0f} s)')
    return None


def threat_hold(run, world: World, started: float) -> Tried | None:
    """The swap held for the safety's retreat while blows that take the life can come within the cast's time
    (macros/safety.py CAST_REACH, `Orders.threat`), asked again in EXPIRED_RETRY s, up to CAST_HOLD_MOST s; None: cast
    now."""
    track = track_of(run)
    now = run.clock()
    why = track.threat(world) if track.threat is not None else None
    if why is None:
        track.threat_since = None
        return None
    if track.threat_since is None:
        track.threat_since = now
    state = orders_state(orders_shown(world) is True, orders_left(run), track.expired_at, now)
    if now - track.threat_since < CAST_HOLD_MOST:
        say_orders(run, state, f'a retreat first ({why})')
        return Tried.again(started, STATE_RETRY, EXPIRED_RETRY, touched=False)
    say_orders(run, state, f'cast in place (held {CAST_HOLD_MOST:.0f} s: {why})')
    return None


def fight_renewal(world: World) -> bool:
    """Whether a cast now renews a Battle Orders still shown with a hostile within QUIET_UNITS."""
    from inventory_tracking.macros.hunting.base import hostiles  # late: the hunt's modules import this one

    return orders_shown(world) is True and not quiet(world, hostiles(world))


def arrival_due(run, world: World) -> bool:
    """Whether Battle Orders is cast at an arrival's swap: not shown, or (RENEW_ORDERS) under ARRIVAL_LEFT s left or
    its cast not known."""
    shown = orders_shown(world)
    if shown is None:
        return False
    if not shown:
        return True
    left = orders_left(run)
    return RENEW_ORDERS and (left is None or left < ARRIVAL_LEFT)


def cast_in_hand(run, key_names) -> bool:
    """At an arrival's input check, with the other weapon set just swapped in (routines.py `took_input`): cast Battle
    Command and Battle Orders when that set is the Call to Arms and Battle Orders is due (`arrival_due`), before the
    check swaps back. Saves the caster's own swap pair (1.5 s, 2026-10-18). The cast is counted in `Run.lasting`."""
    if run.hands is None or not holding(run):
        return False
    world = run.world()
    if not arrival_due(run, world):
        return False
    left = orders_left(run)
    skills = tuple(skill for skill in (BATTLE_COMMAND, BATTLE_ORDERS) if skill in world.slots)
    if BATTLE_ORDERS not in skills:
        return False
    try:
        run.keys.update(key_names(world, skills))
        run.say(
            'Call to Arms at the arrival: '
            + ', '.join('Battle Command' if s == BATTLE_COMMAND else 'Battle Orders' for s in skills)
        )
        if orders_shown(world):
            LOG.info(
                'Macro: Call to Arms at the arrival: Battle Orders cast again (%s)',
                'its cast not known' if left is None else f'{max(left, 0.0):.0f} s left of {ORDERS_LASTS:.0f}',
            )
        pressed = run.clock()
        for skill in skills:
            pressed = cast_free(run, skill)  # the key's down: a cast waits for the one before it to end
            if skill == BATTLE_ORDERS and getattr(run, 'lasting', None) is not None:
                run.lasting[BATTLE_ORDERS] = pressed  # its age for the renewal (`orders_left`, `Buffs.took`)
        # The cast over before the check's swap back (SWAP_AFTER_CAST)
        run.seen(lambda w: w.player is not None and w.player.mode not in ACTING, CAST_OVER)
        run.pace.sleep(max(0.0, pressed + SWAP_AFTER_CAST - run.clock()))
    except (Abort, ValueError) as stop:
        if run.stops(stop):
            raise
        LOG.info('Macro: Call to Arms at the arrival: not cast (%s); the upkeep casts it', stop)
        return False
    return True


# The rows a build adds to its plan, and their caster (`Build.casters`)
ROWS: tuple[Buff, ...] = (
    Buff(
        BATTLE_ORDERS,
        'upkeep',
        worn_and_in_front,
        state=orders_shown,
        caster='cta',
        lasts=ORDERS_LASTS,
        renew=renew_orders,
    ),
)
CASTERS = {'cta': call_to_arms}
