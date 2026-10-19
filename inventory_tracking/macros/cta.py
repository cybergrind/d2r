"""Call to Arms: Battle Command and Battle Orders kept on the character, for any build that wears one.

The player, 2026-10-17: "now we have call to arms, so we need to use it and keep it's buff active ... we determine if
there is cta and use it if we have it ... probably cta cannot be used in town". The game's skills.txt agrees: Battle
Orders (149), Battle Command (155) and Battle Cry (146) have no `InTown`, where the Warlock's own buffs (Consume,
Psychic Ward, Hex: Purge) have it. So the town's prebuff cannot cast them: a row of the upkeep does (`ROWS`), the first
quiet look outside a town with Battle Orders not shown on the character (states.txt `battleorders` 32, game/
BATTLE_ORDERS_BIT, seen to read in the game at 23:41:01 on 2026-10-17).

A cast at Battle Orders 12 (CybergrindAA's CTA +4 and +8 to all skills, 22:58 on 2026-10-17) lasts 750 + 250 per level
past the first frames (skills.txt `auralencalc` ln12, Param1 and Param2): 130 s, longer than a Lower Kurast game's
stay, so one cast a game, at its arrival. Battle Command (the same length) goes first: its +1 to all skills raises the
Battle Orders cast after it.

What is a Call to Arms is read from the item, not named: a weapon that gives Battle Orders as a skill
(game/records.py `gives_orders`), which the weapon set in hand reads as CTA_CODE (`GameMemory.hands`). The caster swaps
to it, casts, and swaps back to the set it found in hand: a game is never left holding it (routines.py
`take_battle_weapons`).
"""

from inventory_tracking.common import LOG
from inventory_tracking.game.memory import CTA_CODE
from inventory_tracking.game.records import World
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.buffs import STATE_RETRY
from inventory_tracking.macros.build import Buff, BuffFacts, Casting, Tried
from inventory_tracking.macros.routines import ACTING, cast as cast_free, swap_until
from inventory_tracking.macros.skills import SWAP_WEAPONS, register_names
from inventory_tracking.native.layout import BATTLE_ORDERS_SKILL, TOWN_IDS


BATTLE_ORDERS = BATTLE_ORDERS_SKILL
BATTLE_COMMAND = 155
register_names({BATTLE_ORDERS: 'Battle Orders', BATTLE_COMMAND: 'Battle Command'})
# Seconds before a try that found no Call to Arms, or its skills on no key, is made again: it is said each time
MISSING_WAIT = 300.0
CAST_OVER = 1.0  # seconds at most for a cast to end before the weapons are swapped
# Seconds from the last cast's key before a weapon swap is taken: the arrival's swap back 0.39-0.42 s after Battle
# Orders' key was refused 25 times in 26, though the character's mode read the cast over (01:41-01:56 on 2026-10-18);
# the caster's own, 0.56-0.61 s after it, was taken 44 times in 44 (2026-10-18 01:05-01:36)
SWAP_AFTER_CAST = 0.6


def orders_shown(world: World) -> bool | None:
    """What the character shows of Battle Orders; None (not kept up) in a town, where it cannot be cast. Not asked of
    the keys: the Call to Arms' skills are on keys only while it is in hand (the player, 23:40 on 2026-10-17: "swap
    weapon and there are 7 and 8 bound to skills")."""
    player = world.player
    if player is None or player.area in TOWN_IDS:
        return None
    return player.battle_orders


def worn_and_in_front(facts: BuffFacts) -> bool:
    """A Call to Arms is worn (`BuffFacts.cta`, read from the items), and the game is in front: a swap pressed into
    another window does nothing."""
    return facts.cta is True and facts.focused()


def holding(run) -> bool | None:
    """Whether the Call to Arms is in hand; None when the hands cannot be read."""
    held = run.hands() if run.hands is not None else ()
    return CTA_CODE in held if held else None


def call_to_arms(cast: Casting) -> Tried:
    """Battle Command (when on a key), then Battle Orders, with the Call to Arms in hand, and the set found in hand back
    after. No Call to Arms after the swaps, or Battle Orders on no key: said, and asked again in MISSING_WAIT."""
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
                raise Abort('no Call to Arms in the other weapon set')
        # Its keys as the set in hand has them
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
        LOG.info('Macro: no Battle Orders (%s); asked again in %.0fs', stop, MISSING_WAIT)
        return Tried.again(started, STATE_RETRY, MISSING_WAIT)
    finally:
        if swapped and run.hands() != before and not swap_until(run, lambda: run.hands() == before):
            LOG.warning('Macro: Call to Arms: the weapons found in hand are not back after the swaps')
    return Tried(started, cast=True)


def cast_in_hand(run, key_names) -> bool:
    """At an arrival's input check, with the other weapon set just swapped in (routines.py `took_input`): Battle Command
    and Battle Orders when that set is the Call to Arms and Battle Orders is due out of town (`orders_shown`), before
    the check swaps back. The upkeep row then finds it shown. At Lower Kurast's arrival the check's swap pair and the
    caster's own came one after the other: 1.5 s for the cast with its own pair (01:15:49-52 on 2026-10-18)."""
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
        # The cast over before the check's swap back (SWAP_AFTER_CAST): one pressed 0.4 s after Battle Orders' key was
        # not taken, and the next 0.6 s later was (01:36:21 on 2026-10-18)
        run.seen(lambda w: w.player is not None and w.player.mode not in ACTING, CAST_OVER)
        run.pace.sleep(max(0.0, pressed + SWAP_AFTER_CAST - run.clock()))
    except (Abort, ValueError) as stop:
        if run.stops(stop):
            raise
        LOG.info('Macro: Call to Arms at the arrival: not cast (%s); the upkeep casts it', stop)
        return False
    return True


# The rows a build adds to its plan, and the caster they name (`Build.casters`)
ROWS: tuple[Buff, ...] = (Buff(BATTLE_ORDERS, 'upkeep', worn_and_in_front, state=orders_shown, caster='cta'),)
CASTERS = {'cta': call_to_arms}
