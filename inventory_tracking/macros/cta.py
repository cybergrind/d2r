"""Call to Arms: Battle Command and Battle Orders kept on the character, for any build that wears one ("we need to use
it and keep it's buff active", the player, 2026-10-17).

Battle Orders and Battle Command have no `InTown` (skills.txt), so the town prebuff cannot cast them: an upkeep row
does (`ROWS`), at the first quiet look outside town with Battle Orders not shown (states.txt `battleorders`). At
Battle Orders 12 a cast lasts ~130 s (skills.txt `auralencalc`), longer than a Lower Kurast stay: one cast a game.
Battle Command goes first: its +1 to all skills raises the Battle Orders after it.

A Call to Arms is read from the item (a weapon giving Battle Orders, game/records.py `gives_orders`). The caster swaps
to it, casts, and swaps back to the set it found in hand.
"""

from inventory_tracking.common import LOG
from inventory_tracking.game.memory import CTA_CODE
from inventory_tracking.game.records import World
from inventory_tracking.macros.actuator import Abort, Hand
from inventory_tracking.macros.buffs import STATE_RETRY
from inventory_tracking.macros.build import Buff, BuffFacts, Casting, Tried
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


def orders_shown(world: World) -> bool | None:
    """Whether the character shows Battle Orders; None in town, where it cannot be cast. Not read from the keys: the
    Call to Arms' skills are on keys only while it is in hand."""
    player = world.player
    if player is None or player.area in TOWN_IDS:
        return None
    return player.battle_orders


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


def cast_in_hand(run, key_names) -> bool:
    """At an arrival's input check, with the other weapon set just swapped in (routines.py `took_input`): cast Battle
    Command and Battle Orders when that set is the Call to Arms and Battle Orders is due, before the check swaps back.
    Saves the caster's own swap pair (1.5 s, 2026-10-18)."""
    if run.hands is None or not holding(run):
        return False
    world = run.world()
    if orders_shown(world) is not False:
        return False
    skills = tuple(skill for skill in (BATTLE_COMMAND, BATTLE_ORDERS) if skill in world.slots)
    if BATTLE_ORDERS not in skills:
        return False
    try:
        run.keys.update(key_names(world, skills))
        run.say(
            'Call to Arms at the arrival: '
            + ', '.join('Battle Command' if s == BATTLE_COMMAND else 'Battle Orders' for s in skills)
        )
        pressed = run.clock()
        for skill in skills:
            pressed = cast_free(run, skill)  # the key's down: a cast waits for the one before it to end
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
ROWS: tuple[Buff, ...] = (Buff(BATTLE_ORDERS, 'upkeep', worn_and_in_front, state=orders_shown, caster='cta'),)
CASTERS = {'cta': call_to_arms}
