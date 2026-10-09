"""The Pindleskin routines for an Echoing Strike Warlock (CybergrindAA), built from small steps.

`run_macro` picks by place (plan.md, decisions of 2026-10-06): where a run ends (Nihlathak's
Temple, Frigid Highlands, Bloody Foothills, the Fortress just after act 3, Catacombs Level 4
with Andariel dead) leave the game,
create the next one and prebuff; in the lobby create the next game and prebuff; anywhere else
prebuff where the character stands.
Prebuff: cast Consume anew on a Defiler (a standing one, else a summoned one), leave one
Defiler out, then Hex: Purge and Psychic Ward.
"""

import math
import os

from inventory_tracking.common import LOG
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.skills import (
    CONSUME,
    HEX_PURGE,
    NAMES,
    PSYCHIC_WARD,
    SUMMON_DEFILER,
    SWAP_WEAPONS,
)
from inventory_tracking.macros.world import (
    DEFILER_CLASS as DEFILER,
    TRACE_RVAS,
    Monster,
    Player,
    World,
    next_name,
)
from inventory_tracking.native.layout import HIRELING_CLASS_ID


NIHLATHAKS_TEMPLE = 121
# Where a farming run ends, so Win+X there leaves the game: Pindleskin's Temple, and for the
# Eldritch and Shenk run (user, 2026-10-06) the Frigid Highlands above its waypoint and the
# Bloody Foothills below it. The whole level counts, not only the part near the waypoint.
RUN_ENDS = frozenset((NIHLATHAKS_TEMPLE, 110, 111))
# Mephisto and other act 3 runs end with a step into act 4, so the next game starts there
# (user, 2026-10-06): the Pandemonium Fortress is a run end for a while after the character
# came to it from act 3 (Kurast Docks to Durance of Hate Level 3). A game that started in the
# Fortress, or a return from the act 4 levels, is not.
# An Andariel run ends on her level once she is dead (user, 2026-10-07): the character on the
# level with no live Andariel in the unit table. No corpse is asked for: hers leaves the table
# 19 s after the kill (host). She is in the table from 86 units away; further off, at the
# stairs before the fight, Win+X leaves the game too.
CATACOMBS_4 = 37
ANDARIEL = 156  # as in terror/bosses.py
PANDEMONIUM_FORTRESS = 103
ACT_3 = range(75, 103)
ARRIVAL_SECONDS = 180.0
SKILLS = (SUMMON_DEFILER, CONSUME, HEX_PURGE, PSYCHIC_WARD, SWAP_WEAPONS)
# Character -> base codes of the weapon set the buffs are cast with. CybergrindAA: Heart of the
# Oak (Flail) and Spirit (Monarch), not the Naj's Puzzler set (user, 2026-10-06; codes from the
# collection capture of the equipped items).
CHARACTERS = {'CybergrindAA': frozenset(('fla', 'uit'))}

# Window fractions. The screenshots (2000 x 1125) show the whole 2560 x 1440 output, whose top
# 22 pixels are the desktop bar, not the game window: y = (shot_y * 1.28 - 22) / 1418. Taking
# the screenshot fraction as it is put the click on the lower edge of the name field (host run
# 17:10, 2026-10-06: six clicks, no key taken).
SAVE_AND_EXIT = (0.5, 0.438)
GAME_NAME_FIELD = (0.8, 0.158)  # right of the text, so the caret lands at its end
# Right of the character, where the user summons; then other sides, a Defiler's width apart.
SUMMON_SPOTS = ((0.66, 0.42), (0.36, 0.44), (0.5, 0.26), (0.64, 0.62), (0.4, 0.64))
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
CLEAR = 7.0  # world units around the Defiler that must be empty before Consume
# A tall monster drawn below the Defiler covers it: the bound demon (class 189) stood 8 world
# units off, 3 across and 11 down the screen in iso units (x - y, x + y), and Consume took it
# with the pointer on the Defiler (host, 01:46 on 2026-10-07). So nothing may stand in this
# column either: so far to a side, so far below (its body rises over the aim) and above.
COVER_ACROSS, COVER_BELOW, COVER_ABOVE = 9.0, 26.0, 8.0
CONSUME_ATTEMPTS = 3
# A Defiler walks after it lands, so Consume is aimed at where it stands when the key goes down:
# if it moved this many world units while the pointer travelled, the pointer follows (user, 2026-10-07).
AIM_DRIFT = 1.0
AIM_TRIES = 4
# monstats.txt rows with npc = 1 (installed game, 2026-10-07): townsfolk. Consume cannot take them,
# yet Kashya, Warriv and Cain stand where a new game starts and were in 13 of the 16 logged crowds
# (host, 2026-10-07), which stopped five prebuffs in the Rogue Encampment.
TOWN_NPCS = frozenset((
    146, 147, 148, 150, 152, 154, 155, 175, 176, 177, 178, 185, 195, 196, 197, 198, 199, 200, 201, 202,
    203, 204, 205, 210, 244, 245, 246, 251, 252, 253, 254, 255, 257, 264, 265, 266, 270, 272, 294, 296,
    297, 331, 367, 377, 378, 405, 406, 408, 512, 513, 514, 515, 516, 521, 522, 528, 538, 539, 540,
))  # fmt: skip
FIELD_ATTEMPTS = 6  # about eight seconds for the lobby to come up


def screen_fraction(player: Player, x: float, y: float, aspect: float) -> tuple[float, float]:
    """Where a unit at world (x, y) is drawn, as window fractions; `aspect` is width / height."""
    dx, dy = x - player.x, y - player.y
    return (
        FEET[0] + (dx - dy) * UNIT_PIXELS[0] / aspect,
        FEET[1] + (dx + dy) * UNIT_PIXELS[1] - BODY_LIFT,
    )


def world_point(player: Player, x: float, y: float, aspect: float) -> tuple[float, float]:
    """The ground point drawn at window fraction (x, y): the inverse of `screen_fraction` for feet."""
    across = (x - FEET[0]) * aspect / UNIT_PIXELS[0]
    down = (y - FEET[1]) / UNIT_PIXELS[1]
    return player.x + (across + down) / 2, player.y + (down - across) / 2


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


def bystanders(world: World, but: int | None = None) -> list[Monster]:
    """Every living monster Consume might take in place of the Defiler: the bound demon cannot
    be told from the rest (summons carry no owner), so all count but the mercenary and townsfolk."""
    return [
        m
        for m in world.monsters
        if m.txt_id not in (DEFILER, HIRELING_CLASS_ID) and m.txt_id not in TOWN_NPCS and m.unit_id != but
    ]


def in_the_way(monster: Monster, x: float, y: float) -> bool:
    """Whether the pointer on a Defiler at (x, y) might be on this monster instead."""
    dx, dy = monster.x - x, monster.y - y
    return math.hypot(dx, dy) < CLEAR or (abs(dx - dy) < COVER_ACROSS and -COVER_ABOVE < dx + dy < COVER_BELOW)


def crowd(world: World, x: float, y: float) -> list[Monster]:
    return [m for m in bystanders(world) if in_the_way(m, x, y)]


def log_crowd(world: World, unit: int) -> None:
    """Research: what stands in the Defiler's way, as class and offset from it in world units."""
    target = next((m for m in defilers(world) if m.unit_id == unit), None)
    near = (
        [
            f'class {m.txt_id} at ({m.x - target.x:+.1f}, {m.y - target.y:+.1f})'
            for m in crowd(world, target.x, target.y)
        ]
        if target is not None
        else []
    )
    LOG.info('Macro: the Defiler is crowded by %s; summoning another', ', '.join(near) or 'nothing now')


def open_spots(run: Run, world: World, skip: int = 0) -> list[tuple[float, float]]:
    """SUMMON_SPOTS from the `skip`-th on, those with nobody near first: a Defiler next to the
    bound demon cannot be consumed safely. Skipping used to come after the sorting, which could put
    a crowded spot back in front for a replacement."""
    spots = list(SUMMON_SPOTS[skip % len(SUMMON_SPOTS) :] + SUMMON_SPOTS[: skip % len(SUMMON_SPOTS)])
    rect = run.actuator.keys.focused_window_rect()
    if rect is None or world.player is None:
        return spots
    player, aspect = world.player, rect[2] / rect[3]
    return sorted(spots, key=lambda spot: bool(crowd(world, *world_point(player, *spot, aspect))))


def summon_defiler(run: Run, *, until: float | None = None, skip: int = 0) -> Monster:
    """Summon one Defiler. `until` (a clock time) keeps trying that long: a game that has just
    come up takes no input for a while, and the summon appearing is what shows it does.
    `skip` starts that many spots further on, for a Defiler that replaces a crowded one."""
    start = run.world()
    before = {monster.unit_id for monster in defilers(start)}
    # A spot that cannot be walked on takes no summon (user, 2026-10-06): try the next one.
    world, spot = None, SUMMON_SPOTS[0]
    spots = open_spots(run, start, skip)
    while world is None and spots:
        spot = spots.pop(0)
        run.actuator.move(*spot, scatter=(40, 25))
        press_skill(run, SUMMON_DEFILER)
        world = run.seen(lambda w: any(m.unit_id not in before for m in defilers(w)), 1.5)
        if world is None and not spots and until is not None and run.clock() < until:
            spots = open_spots(run, run.world())[:1]
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


def aim_at(run: Run, unit: int) -> bool:
    """Put the pointer on this Defiler where it stands now, following it while it walks. False
    when it never stood still: the pointer is then somewhere it was, where the bound demon may
    be, and Consume must not be pressed."""
    for _ in range(AIM_TRIES):
        world = run.world()
        target = next((m for m in defilers(world) if m.unit_id == unit), None)
        if target is None or world.player is None:
            raise Abort('the Defiler is gone before Consume')
        rect = run.actuator.keys.focused_window_rect()
        if rect is None:
            raise Abort('no game window')
        point = screen_fraction(world.player, target.x, target.y, rect[2] / rect[3])
        if not on_screen(point):
            raise Abort('the Defiler is out of view')
        run.actuator.move(*point, scatter=(5, 5))
        now = next((m for m in defilers(run.world()) if m.unit_id == unit), None)
        if now is None:
            raise Abort('the Defiler is gone before Consume')
        drift = math.hypot(now.x - target.x, now.y - target.y)
        if drift <= AIM_DRIFT:
            return True
        LOG.info('Macro: the Defiler moved %.1f units during the aim; aiming again', drift)
    return False


def log_miss(run: Run, world: World, unit: int) -> None:
    """Research: the scene when a pressed Consume showed nothing, everything as an offset from the
    Defiler in world units (the mercenary and townsfolk too: they may cover it)."""
    target = next((m for m in defilers(world) if m.unit_id == unit), None)
    player = world.player
    if target is None or player is None:
        LOG.info('Macro: Consume showed nothing; Defiler %s is gone, player %s', unit, player)
        return
    near = [
        f'class {m.txt_id} mode {m.mode} at ({m.x - target.x:+.1f}, {m.y - target.y:+.1f})'
        for m in world.monsters
        if m.unit_id != unit and math.hypot(m.x - target.x, m.y - target.y) < 40
    ]
    LOG.info(
        'Macro: Consume showed nothing; Defiler mode %s, player mode %s at (%+.1f, %+.1f), '
        'Consume %s, pointer %s; near: %s',
        target.mode,
        player.mode,
        player.x - target.x,
        player.y - target.y,
        player.consume,
        run.actuator.keys.pointer(),
        ', '.join(near) or 'nothing',
    )


def consume(run: Run, defiler: Monster) -> None:
    """Consume this Defiler and nothing else. Consume once took the bound demon with the pointer
    on the Defiler (host, 20:51 on 2026-10-06, and again 01:46 on 2026-10-07), so the key is
    pressed only while nothing else stands near the Defiler or where its body would be drawn
    over it (`in_the_way`); if it stays crowded, another Defiler is summoned
    somewhere open (that cancels an active Consume, which is about to be cast anew anyway). Afterwards the Defiler
    must be the one gone. Each replacement goes to another spot: three in a row at the first
    one were all crowded, twice over (host, 13:08 on 2026-10-07, Rogue Encampment).
    A press that changes nothing (the Defiler stands, no buff: host, 20:04 on 2026-10-07, and
    about one press in thirty before it) is made again, under the same checks."""
    missed = False
    for attempt in range(CONSUME_ATTEMPTS):

        def clear(w: World, unit: int = defiler.unit_id) -> bool:
            target = next((m for m in defilers(w) if m.unit_id == unit), None)
            return target is None or not crowd(w, target.x, target.y)

        if run.seen(clear, 1.0) is None:
            log_crowd(run.world(), defiler.unit_id)
            defiler = summon_defiler(run, skip=attempt + 1)
            continue
        # Ready first, then aim: the key follows the pointer at once, on the Defiler as it stands.
        run.expect('character ready', lambda w: w.player is not None and w.player.mode not in ACTING, 2.5)
        if not aim_at(run, defiler.unit_id):
            continue
        if run.research is not None:  # which bytes name the unit under the pointer (a later check)
            LOG.info(
                'Macro: Defiler %s under the pointer; type and id at %s', defiler.unit_id, run.research(defiler.unit_id)
            )
        if not clear(run.world()):  # somebody walked up during the pointer move
            continue
        press_skill(run, CONSUME)

        def consumed(w: World, unit: int = defiler.unit_id) -> bool:
            return bool(w.player and w.player.consume) and all(m.unit_id != unit for m in defilers(w))

        if run.seen(consumed, 2.5) is not None:
            run.pause('key')
            return
        world = run.world()
        log_miss(run, world, defiler.unit_id)
        untouched = world.player is not None and world.player.consume is False
        if not untouched or all(m.unit_id != defiler.unit_id for m in defilers(world)):
            raise Abort('Consume: not seen in 2.5s')  # something happened, and not what was meant
        missed = True
    if missed:
        raise Abort(f'Consume: not seen in 2.5s, {CONSUME_ATTEMPTS} times over')
    raise Abort('something stays too close to the Defiler, or it keeps walking; Consume was not pressed')


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


def take_prebuff_weapons(run: Run, *, until: float | None = None) -> None:
    """Have the set the buffs are cast with in hand (user, 2026-10-06), swapping if the other
    one is. The set is left in hand afterwards. `until` as in `summon_defiler`."""
    wanted = run.prebuff_hands
    if run.hands is None or not wanted:
        return

    def in_hand(timeout: float) -> bool:
        deadline = run.clock() + timeout
        while True:
            run.world()  # a cancel stops here
            if wanted & set(run.hands()):
                return True
            if run.clock() >= deadline:
                return False
            run.pace.sleep(0.03)

    if in_hand(0):
        return
    while True:
        press_skill(run, SWAP_WEAPONS)
        if in_hand(1.2):
            break
        if until is None or run.clock() >= until:
            raise Abort('the prebuff weapons are not in hand after a swap')
        run.pause('screen')
    run.pause('key')


def log_consume(run: Run, when: str) -> None:
    """Research: the buff's record, to find where it keeps the time it has left."""
    player = run.world().player
    if player is not None and player.consume_node:
        LOG.info('Macro: Consume record %s (clock %.2f): %s', when, run.clock(), player.consume_node.hex())


def prebuff(run: Run, *, fresh: LoadTrace | None = None) -> None:
    """End with a newly cast Consume and one Defiler out. Consume is always cast, never taken
    as good because it is active: how long it has left is not known, and it ran out in the
    middle of a run (user, 2026-10-06). A second Defiler summoned while one stands cancels
    Consume (user, 2026-10-06), so a standing Defiler is the one consumed, never summoned over."""
    take_prebuff_weapons(run, until=None if fresh is None else fresh.started + LOAD_LIMIT)
    log_consume(run, 'before')
    if fresh is not None:  # a new game: nothing is out, and the first summon may have to wait
        defiler = summon_defiler(run, until=fresh.started + LOAD_LIMIT)
        fresh.finish()
    else:
        standing = defilers(run.world())
        defiler = standing[0] if standing else summon_defiler(run)
    consume(run, defiler)
    log_consume(run, 'after')
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
    run.prebuff_hands = CHARACTERS[world.player.name]
    return key_names(world)


def run_ended(run: Run, world: World) -> bool:
    if world.player is None:
        return False
    if world.player.area in RUN_ENDS:
        return True
    if world.player.area == CATACOMBS_4:
        return all(monster.txt_id != ANDARIEL for monster in world.monsters)
    if world.player.area != PANDEMONIUM_FORTRESS or run.arrival is None:
        return False
    previous, seconds = run.arrival()
    LOG.info('Macro: in the Fortress, %.0fs after level %s', seconds, previous)
    return previous in ACT_3 and seconds <= ARRIVAL_SECONDS


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
        if run_ended(run, world):
            leave_game(run)
            trace = create_next_game(run, world.game_name)
            if key_names(run.world()) != run.keys:
                raise Abort('the skill keys changed')
            prebuff(run, fresh=trace)
        else:
            prebuff(run)
    run.say('Prebuff done')
