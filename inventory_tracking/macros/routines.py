"""The Pindleskin routines for an Echoing Strike Warlock (CybergrindAA), built from small steps.

`run_macro` picks by place (plan.md, decisions of 2026-10-06): where a run ends (Nihlathak's
Temple, Frigid Highlands, Bloody Foothills) leave the game, create the next one and prebuff; in
the lobby create the next game and prebuff; anywhere else prebuff where the character stands.
Prebuff: get Consume active and one Defiler out (summoning and consuming only what is missing),
then Hex: Purge and Psychic Ward.
"""

import os

from inventory_tracking.common import LOG
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.skills import CONSUME, HEX_PURGE, NAMES, PSYCHIC_WARD, SUMMON_DEFILER
from inventory_tracking.macros.world import (
    DEFILER_CLASS as DEFILER,
    TRACE_RVAS,
    Monster,
    Player,
    World,
    next_name,
)


NIHLATHAKS_TEMPLE = 121
# Where a farming run ends, so Win+X there leaves the game: Pindleskin's Temple, and for the
# Eldritch and Shenk run (user, 2026-10-06) the Frigid Highlands above its waypoint and the
# Bloody Foothills below it. The whole level counts, not only the part near the waypoint.
RUN_ENDS = frozenset((NIHLATHAKS_TEMPLE, 110, 111))
SKILLS = (SUMMON_DEFILER, CONSUME, HEX_PURGE, PSYCHIC_WARD)
CHARACTERS = frozenset(('CybergrindAA',))

# Window fractions. The screenshots (2000 x 1125) show the whole 2560 x 1440 output, whose top
# 22 pixels are the desktop bar, not the game window: y = (shot_y * 1.28 - 22) / 1418. Taking
# the screenshot fraction as it is put the click on the lower edge of the name field (host run
# 17:10, 2026-10-06: six clicks, no key taken).
SAVE_AND_EXIT = (0.5, 0.438)
GAME_NAME_FIELD = (0.8, 0.158)  # right of the text, so the caret lands at its end
# Right of the character, where the user summons; then nearer, then on the other side.
SUMMON_SPOTS = ((0.66, 0.42), (0.58, 0.5), (0.36, 0.44))
# Where the character's feet are drawn. Host run 17:38, 2026-10-06: two summons landed 0.027 and
# 0.020 of the height above the pointer with 0.47 here, and within 0.003 across.
FEET = (0.5, 0.494)
BODY_LIFT = 0.035  # aim this much of the window height above a unit's feet
# The classic isometric view: a world unit is 16 x 8 pixels at a 600-pixel-high view.
UNIT_PIXELS = (16 / 600, 8 / 600)
AIM_LIMITS = ((0.08, 0.92), (0.08, 0.8))  # stay off the window edge and the skill bar

# Player modes that are an action under way: attacks, casts, skill sequences (classic table).
ACTING = frozenset((7, 8, 10, 11, 12, 13, 14, 15, 16, 18))
DEAD = frozenset((0, 17))
CREATE_LIMIT = 12.0  # seconds from Enter for the new game to exist
LOAD_MIN = 8.5  # seconds from Enter before the first key in a new game
LOAD_LIMIT = 40.0  # seconds from Enter the first summon may take
FIELD_ATTEMPTS = 6  # about eight seconds for the lobby to come up


def screen_fraction(player: Player, x: float, y: float, aspect: float) -> tuple[float, float]:
    """Where a unit at world (x, y) is drawn, as window fractions; `aspect` is width / height."""
    dx, dy = x - player.x, y - player.y
    return (
        FEET[0] + (dx - dy) * UNIT_PIXELS[0] / aspect,
        FEET[1] + (dx + dy) * UNIT_PIXELS[1] - BODY_LIFT,
    )


def on_screen(point: tuple[float, float]) -> bool:
    return all(low <= value <= high for value, (low, high) in zip(point, AIM_LIMITS, strict=True))


def press_skill(run: Run, skill: int) -> None:
    """Press the skill's key once the character is free to act."""
    ready = run.expect('character ready', lambda w: w.player is not None and w.player.mode not in ACTING, 2.5)
    if ready.player is not None and ready.player.mode in DEAD:
        raise Abort('the character is dead')
    run.say(NAMES[skill])
    run.actuator.tap(run.keys[skill])


def defilers(world: World) -> list[Monster]:
    return [monster for monster in world.monsters if monster.txt_id == DEFILER]


def summon_defiler(run: Run, *, until: float | None = None) -> Monster:
    """Summon one Defiler. `until` (a clock time) keeps trying that long: a game that has just
    come up takes no input for a while, and the summon appearing is what shows it does."""
    before = {monster.unit_id for monster in defilers(run.world())}
    # A spot that cannot be walked on takes no summon (user, 2026-10-06): try the next one.
    world, spot = None, SUMMON_SPOTS[0]
    spots = list(SUMMON_SPOTS)
    while world is None and spots:
        spot = spots.pop(0)
        run.actuator.move(*spot, scatter=(40, 25))
        press_skill(run, SUMMON_DEFILER)
        world = run.seen(lambda w: any(m.unit_id not in before for m in defilers(w)), 1.5)
        if world is None and not spots and until is not None and run.clock() < until:
            spots = [SUMMON_SPOTS[0]]
            run.pause('screen')
    if world is None:
        raise Abort('Defiler: not seen at any spot')
    defiler = next(m for m in defilers(world) if m.unit_id not in before)
    # Research: which field ties a summon to its player (the mercenary's owner field does not).
    LOG.info(
        'Macro: Defiler is unit %s (player unit %s); unit and data: %s',
        defiler.unit_id,
        world.player.unit_id if world.player else None,
        defiler.raw.hex(),
    )
    # Research: is the pointer move honoured? The summon should land where the pointer was sent.
    rect = run.actuator.keys.focused_window_rect()
    if rect is not None and world.player is not None:
        landed = screen_fraction(world.player, defiler.x, defiler.y, rect[2] / rect[3])
        LOG.info(
            'Macro: aimed at (%.3f, %.3f), Defiler drawn at (%.3f, %.3f); pointer %s in window %s',
            *spot,
            landed[0],
            landed[1] + BODY_LIFT,
            run.actuator.keys.pointer(),
            rect,
        )
    run.pause('key')
    return defiler


def consume(run: Run, defiler: Monster) -> None:
    """Consume this Defiler and nothing else: aim at it, then require that it is the one gone.
    A Consume that took the bound demon leaves the Defiler standing, which stops the macro."""
    world = run.world()
    target = next((m for m in defilers(world) if m.unit_id == defiler.unit_id), None)
    if target is None or world.player is None:
        raise Abort('the Defiler is gone before Consume')
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        raise Abort('no game window')
    point = screen_fraction(world.player, target.x, target.y, rect[2] / rect[3])
    if not on_screen(point):
        raise Abort('the Defiler is out of view')
    run.actuator.move(*point, scatter=(5, 5))
    press_skill(run, CONSUME)

    def consumed(w: World) -> bool:
        return bool(w.player and w.player.consume) and all(m.unit_id != defiler.unit_id for m in defilers(w))

    run.expect('Consume', consumed, 2.5)
    run.pause('key')


def cast(run: Run, skill: int) -> None:
    """A self or area cast with no known mark in memory yet: the cast animation is the evidence."""
    press_skill(run, skill)
    if run.seen(lambda w: w.player is not None and w.player.mode in ACTING, 0.8) is None:
        LOG.warning('Macro: no cast seen after %s', NAMES[skill])
    run.pause('key')


class LoadTrace:
    """Research: when each traced byte changed after Enter, logged once the first summon works."""

    def __init__(self, run: Run) -> None:
        self.run, self.started = run, run.clock()
        self.last: bytes | None = None
        self.changes: list[str] = []

    def __call__(self, world: World) -> None:
        if self.last is not None and world.trace != self.last and len(world.trace) == len(self.last):
            at = self.run.clock() - self.started
            self.changes += [
                f'{at:.2f}s {rva:#x} {old}->{new}'
                for rva, old, new in zip(TRACE_RVAS, self.last, world.trace, strict=True)
                if old != new
            ]
        self.last = world.trace

    def finish(self) -> None:
        self.run.observe = None
        LOG.info(
            'Macro: first summon %.2fs after Enter; byte changes: %s',
            self.run.clock() - self.started,
            '; '.join(self.changes[-60:]) or 'none',
        )


def prebuff(run: Run, *, fresh: LoadTrace | None = None) -> None:
    """End with Consume active and one Defiler out, pressing only what is missing. A second
    Defiler summoned while one stands cancels Consume (user, 2026-10-06), so a standing Defiler
    is used or kept, never summoned over."""
    world = run.world()
    if fresh is not None:  # a new game: nothing is out, and the first summon may have to wait
        defiler = summon_defiler(run, until=fresh.started + LOAD_LIMIT)
        fresh.finish()
        consume(run, defiler)
    elif not (world.player and world.player.consume):
        standing = defilers(world)
        consume(run, standing[0] if standing else summon_defiler(run))
    if not defilers(run.world()):
        summon_defiler(run)
    cast(run, HEX_PURGE)
    cast(run, PSYCHIC_WARD)


def leave_game(run: Run) -> None:
    world = run.world()
    for _ in range(3):  # Escape closes an open panel first
        if not world.open_panels:
            break
        run.actuator.tap('Escape')
        run.pause('key')
        world = run.world()
    if world.open_panels:
        raise Abort(f'{world.open_panels[0]} stays open')
    run.say('Save and Exit')
    run.actuator.tap('Escape')
    run.expect('quit menu', lambda w: w.quit_menu, 2)
    run.pause('screen')
    run.actuator.move(*SAVE_AND_EXIT, scatter=(60, 8))
    run.actuator.click()
    run.expect('leaving the game', lambda w: not w.in_game, 10)


def create_next_game(run: Run, last: str) -> LoadTrace:
    try:
        name = next_name(last)
    except ValueError as exc:
        raise Abort(str(exc)) from exc
    run.say(f'Creating {name}')
    # The name in memory is the lobby field's own text (record probe: it shrank and grew as the
    # user typed), so every edit is checked there. The lobby takes a moment to accept input and
    # nothing in memory says when (plan.md, R3): the first Backspace that shortens the name does.
    run.pause('screen')
    world = run.world()
    if world.in_game or world.game_name != last:
        raise Abort('not in the lobby')
    for _ in range(FIELD_ATTEMPTS):
        run.actuator.move(*GAME_NAME_FIELD, scatter=(25, 4))
        run.actuator.click()
        run.pause('key')
        run.actuator.tap('End')
        run.actuator.tap('BackSpace')
        if run.seen(lambda w: w.game_name == last[:-1], 0.6) is not None:
            break
        run.pause('screen')
        run.pause('screen')
    else:
        raise Abort('the game name field did not take the keys')
    # Only the end that differs is retyped (user, 2026-10-06): cyber36 -> one Backspace and `7`.
    kept = len(os.path.commonprefix((last, name)))
    for _ in range(len(last) - kept - 1):
        run.pause('type')
        run.actuator.tap('BackSpace')
    run.expect('shortened game name', lambda w: w.game_name == last[:kept], 1)
    run.pause('key')
    run.actuator.type_text(name[kept:])
    run.expect(f'game name {name}', lambda w: w.game_name == name, 1)  # never Enter on another name
    run.pause('key')
    run.actuator.tap('Return')
    trace = LoadTrace(run)
    run.observe = trace
    # The game exists within a second or two of Enter; without it there is an error dialog
    # (host, 18:35 on 2026-10-06), which the macro leaves for the player.
    if run.seen(lambda w: w.in_game and w.game_name == name, CREATE_LIMIT) is None:
        raise Abort(f'{name} was not created (is there an error on screen?)')
    # The character and the town's units exist while the loading screen is still up. The view
    # byte (world.VIEW_RVA) is 0 while the game loads and comes back when it can be played. If
    # it never shows the loading at all, the measured LOAD_MIN from Enter stands in; either way
    # the first summon is tried until it appears (prebuff, `fresh`).
    marked = run.seen(lambda w: w.view == 0, 3) is not None
    run.expect('town', lambda w: w.player is not None and w.player.in_town and bool(w.monsters), 45)
    if marked:
        run.expect('loaded game', lambda w: w.view != 0, LOAD_LIMIT)
    else:
        LOG.warning('Macro: no loading mark; waiting %ss from Enter', LOAD_MIN)
        while run.clock() - trace.started < LOAD_MIN:
            run.world()
            run.pace.sleep(0.1)
    LOG.info('Macro: game loaded %.2fs after Enter', run.clock() - trace.started)
    run.pause('screen')
    return trace


def character_keys(run: Run, key_names) -> dict[int, str]:
    world = run.world()
    if world.player is None:
        raise Abort('not in a game')
    if world.player.name not in CHARACTERS:
        raise Abort(f'no macro for {world.player.name}')
    return key_names(world)


def run_macro(run: Run, key_names) -> None:
    """`key_names(world)` gives the key per skill for the character in the game (skills.py)."""
    world = run.world()
    if not world.in_game:
        # The lobby (user, 2026-10-06): make the next game and prebuff. Which character it is
        # shows only in the game, so it and its keys are checked there, before any skill key.
        # On any other screen out of a game the name field never answers and the macro stops.
        run.actuator.wait_released()
        trace = create_next_game(run, world.game_name)
        run.keys = character_keys(run, key_names)
        prebuff(run, fresh=trace)
    else:
        run.keys = character_keys(run, key_names)
        run.actuator.wait_released()
        if world.player is not None and world.player.area in RUN_ENDS:
            leave_game(run)
            trace = create_next_game(run, world.game_name)
            if key_names(run.world()) != run.keys:
                raise Abort('the skill keys changed')
            prebuff(run, fresh=trace)
        else:
            prebuff(run)
    run.say('Prebuff done')
