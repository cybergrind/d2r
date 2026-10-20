"""The Warlock's casts that are more than one aim and one key (macros/build.py `Build.casters`): the
Defiler's summon, Consume on a Defiler, the two together at a game's start and in the middle of a run,
Engorge on a corpse, and the sigil's own answer when its place is off the screen. Each is called by the
buff executor (macros/buffs.py) with a `Casting` and answers with a `Tried`.
"""

import math
import struct
import weakref
from collections.abc import Sequence
from dataclasses import replace

from inventory_tracking.builds.warlock.buffs import (
    CONSUME_RETRY,
    CONSUME_SOON,
    ENGORGE_LOOKS,
    ENGORGE_REACH,
    ENGORGE_RETRY,
    SIGIL_GAP,
    SIGIL_LOOK,
    SIGIL_MISSILES,
    SIGIL_SECONDS,
    SIGIL_SHOWS,
    SIGIL_UNSHOWN,
    UNSHOWN,
    SigilWatch,
    demon_hurt,
    engorge_every,
    keep_reason,
    kept,
)
from inventory_tracking.builds.warlock.defiler import DEFILER_RETRY
from inventory_tracking.builds.warlock.skills import CONSUME, ENGORGE, SUMMON_DEFILER
from inventory_tracking.common import LOG
from inventory_tracking.game.layout import DEFILER_CLASS as DEFILER, ITEM_UNIT, MONSTER_UNIT, NO_OWNER
from inventory_tracking.game.records import Monster, Player, World
from inventory_tracking.game.view import BODY_LIFT, FEET
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.buffs import keys_of
from inventory_tracking.macros.build import Caster, Casting, Tried
from inventory_tracking.macros.cta import CASTERS as CTA_CASTERS
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.pad import heading_degrees, turned
from inventory_tracking.macros.routines import (
    ACTING,
    LOAD_LIMIT,
    TOWN_NPCS,
    on_screen,
    press_skill,
    screen_fraction,
    standable,
    take_prebuff_weapons,
    world_point,
)
from inventory_tracking.macros.teleport import HOVER_SECONDS, ground_fraction
from inventory_tracking.macros.travel import label
from inventory_tracking.native.layout import HIRELING_CLASS_ID


# Right of the character, where the user summons; then other sides, a Defiler's width apart.
SUMMON_SPOTS = ((0.66, 0.42), (0.36, 0.44), (0.5, 0.26), (0.64, 0.62), (0.4, 0.64))
# The same sides at half the distance, for known narrow ground (Cave Level 1: nothing at the far ones, 2026-10-12).
NEAR_SPOTS = tuple((round((x + FEET[0]) / 2, 3), round((y + FEET[1]) / 2, 3)) for x, y in SUMMON_SPOTS)
CLEAR = 7.0  # world units around the Defiler that must be empty before Consume
# A tall monster drawn below the Defiler covers it (Consume took the bound demon with the pointer on the Defiler,
# 2026-10-07 01:46), so nothing may stand in this screen column either: across, below and above, in iso units.
COVER_ACROSS, COVER_BELOW, COVER_ABOVE = 9.0, 26.0, 8.0
CONSUME_ATTEMPTS = 3
# A townsperson this near the Defiler is under the pointer on it: Consume cannot take one, so the press shows nothing.
# 22:35:05-13 on 2026-10-19 (Kurast Docks): Meshif (class 264) 0.9-2.8 from the Defiler, three presses showed nothing
# and the game was left. Kashya 14 off (2026-10-07) never was. Such a miss has another Defiler summoned elsewhere.
TOWN_COVER = 4.0
CONSUME_PAD_WAIT = 10.0  # seconds: Consume due in controller mode is asked again this often (`consume_again`)
# World units a Defiler may walk while the pointer travels before the pointer follows it (user, 2026-10-07).
AIM_DRIFT = 1.0
AIM_TRIES = 4
PANEL_OPEN = 'a panel is open'  # what stops a summon with the player's panel open (`hand_off`)


def defilers(world: World) -> list[Monster]:
    return [monster for monster in world.monsters if monster.txt_id == DEFILER]


def bystanders(world: World, but: int | None = None) -> list[Monster]:
    """Every living monster Consume might take in place of the Defiler: the character's own and any whose stats
    could not be read, but the mercenary and townsfolk. Not a hostile: Consume cannot take it, and counting them made
    every Defiler "crowded" mid-level (2026-10-10 18:48)."""
    return [
        m
        for m in world.monsters
        if m.txt_id not in (DEFILER, HIRELING_CLASS_ID)
        and m.txt_id not in TOWN_NPCS
        and m.unit_id != but
        and (m.ally or m.owner != NO_OWNER or not m.max_life)
    ]


class Unconsumed(Abort):
    """Consume did not take on any Defiler tried (`consume`): nothing else happened, so the prebuff goes on without it
    (`defiler_dance`)."""


def townsfolk_over(world: World, x: float, y: float) -> list[Monster]:
    """The townsfolk within TOWN_COVER of a Defiler at (x, y): the pointer on it may be on them."""
    return [m for m in world.monsters if m.txt_id in TOWN_NPCS and math.hypot(m.x - x, m.y - y) < TOWN_COVER]


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


def open_spots(
    run: Run, world: World, skip: int = 0, tried: Sequence[tuple[float, float]] = ()
) -> list[tuple[float, float]]:
    """SUMMON_SPOTS from the `skip`-th on, those with nobody near first (a Defiler next to the bound demon cannot be
    consumed safely). With the ground known (`run.ground`), only spots a summon can stand on, NEAR_SPOTS last;
    all of them when none can. A replacement (`skip`): spots `tried` last, then the farthest from a bystander first."""
    spots = list(SUMMON_SPOTS[skip % len(SUMMON_SPOTS) :] + SUMMON_SPOTS[: skip % len(SUMMON_SPOTS)])
    rect = run.actuator.keys.focused_window_rect()
    if rect is None or world.player is None:
        return spots
    player, aspect = world.player, rect[2] / rect[3]
    ground = run.reads.ground()
    if ground:
        here = (player.x, player.y)
        known = [*spots, *NEAR_SPOTS]
        found = [spot for spot in known if standable(ground, here, world_point(player, *spot, aspect))]
        if len(found) < len(spots):
            LOG.info('Macro: %d of %d summon spots are on ground a Defiler can stand on', len(found), len(known))
        spots = found or spots
    near = bystanders(world)

    def order(spot: tuple[float, float]) -> tuple[bool, bool, bool, float]:
        x, y = world_point(player, *spot, aspect)
        # 22:00:25-29 on 2026-10-19: three Defilers in a row at the side the bound demon (class 189) stood, 4.4 s
        # mid-fight (rca/2026-10-19/tz-leveling-findings.md C8)
        apart = min((math.hypot(m.x - x, m.y - y) for m in near), default=math.inf) if skip else 0.0
        # Nor beside a townsperson, who takes the pointer (TOWN_COVER; 22:35:05 on 2026-10-19)
        return spot in tried, bool(crowd(world, x, y)), bool(townsfolk_over(world, x, y)), -apart

    return sorted(spots, key=order)


def summon_defiler(
    run: Run, *, until: float | None = None, skip: int = 0, tried: list[tuple[float, float]] | None = None
) -> Monster:
    """Summon one Defiler. `until` (a clock time) keeps trying that long: a new game takes no input for a while.
    `skip` starts that many spots further on, for a Defiler that replaces a crowded one; `tried` (kept by the
    caller) gets the spot it took and is taken last again."""
    start = run.world()
    before = {monster.unit_id for monster in defilers(start)}
    # A spot that cannot be walked on takes no summon (user, 2026-10-06): try the next one.
    world, spot = None, SUMMON_SPOTS[0]
    spots = open_spots(run, start, skip, tried or ())
    looked = [start]  # the last world looked at: the panel check reads no world of its own

    def came(seen: World) -> bool:
        looked[0] = seen
        return any(m.unit_id not in before for m in defilers(seen))

    while world is None and spots:
        spot = spots.pop(0)
        hand_off(looked[0])
        rect = run.actuator.keys.focused_window_rect()
        if run.pad is not None and start.player is not None and rect is not None:
            # Controller mode: a heading toward the spot (macros/pad.py); the game puts it at its own distance.
            here = (start.player.x, start.player.y)
            run.pad.aim_place(here, world_point(start.player, *spot, rect[2] / rect[3]))
        else:
            run.actuator.move(*spot, scatter=(40, 25))
        press_skill(run, SUMMON_DEFILER)
        world = run.seen(came, 1.5)
        if world is None and not spots and until is not None and run.clock() < until:
            looked[0] = run.world()
            spots = open_spots(run, looked[0])[:1]
            run.pause('screen')
    if world is None:
        raise Abort('Defiler: not seen at any spot')
    if tried is not None:
        tried.append(spot)
    defiler = next(m for m in defilers(world) if m.unit_id not in before)
    if run.pad is not None and start.player is not None:
        window = run.actuator.keys.focused_window_rect()
        if window is not None:
            log_landing(start.player, world_point(start.player, *spot, window[2] / window[3]), defiler)
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


def hand_off(world: World) -> None:
    """No summon into a panel the player has open (rca/2026-10-14/run-1932-findings.md issue 3): stopped as a key of
    the player's stops a routine; the caller tries again soon. `world` is the caller's latest look: no read of its
    own under the strike (golden loop_counts.json)."""
    panels = world.open_panels
    if panels:
        raise Abort(f'{PANEL_OPEN} ({", ".join(panels)}): no summon into it')


def log_landing(player: Player, toward: tuple[float, float], defiler: Monster) -> None:
    """Controller mode: where Summon Defiler (controllerskillsettings.json usageType 0, distance 2) put the Defiler
    against the heading the stick gave it (rca/2026-10-13/controller-gaps.md step 1)."""
    heading = (toward[0] - player.x, toward[1] - player.y)
    went = (defiler.x - player.x, defiler.y - player.y)
    LOG.info(
        'Pad consume: Summon Defiler toward %.0f degrees: the Defiler (unit %d) landed at (%+.1f, %+.1f) from the '
        'character, %.1f away at %.0f degrees (off %+.0f degrees)',
        heading_degrees(heading), defiler.unit_id, *went, math.hypot(*went), heading_degrees(went),
        turned(heading_degrees(went), heading_degrees(heading)),
    )  # fmt: skip


def mine(world: World) -> dict[int, int]:
    """unit id -> class of the units Consume's target group may take (controllerskillsettings.json targetGroup 6):
    the Defilers, the bound demon and the other summons, the mercenary."""
    return {
        m.unit_id: m.txt_id
        for m in world.monsters
        if m.txt_id in (DEFILER, HIRELING_CLASS_ID) or m.ally or m.owner != NO_OWNER
    }


def log_pad_consume(run: Run, unit: int, before: dict[int, int], began: float, shown: World | None) -> None:
    """Controller mode: which of the character's units Consume took and whether its state appeared."""
    after = mine(run.world())
    gone = [f'unit {u} (class {c}{", the Defiler" if u == unit else ""})' for u, c in before.items() if u not in after]
    LOG.info(
        "Pad consume: Consume pressed with the client's target on the Defiler (unit %d); consumed %s; the state %s",
        unit, ', '.join(gone) or 'nothing',
        f'shown after {run.clock() - began:.2f}s' if shown is not None else 'not shown in 2.5s',
    )  # fmt: skip


FOLLOW_SECONDS = 2.0  # for a Defiler left behind to come into view (summons follow the character)


def in_view(run: Run) -> Monster | None:
    """A standing Defiler drawn in the window, waited for FOLLOW_SECONDS when one stands out of it; None with none
    (not the first standing one: it may be out of view, which stopped the KP_6 loop on 2026-10-17)."""
    rect = run.actuator.keys.focused_window_rect()

    def shown(world: World) -> Monster | None:
        if rect is None or world.player is None:
            return None
        player = world.player
        drawn = [m for m in defilers(world) if on_screen(screen_fraction(player, m.x, m.y, rect[2] / rect[3]))]
        return drawn[0] if drawn else None

    world = run.world()
    found = shown(world)
    if found is not None or not defilers(world):
        return found
    LOG.info('Macro: the standing Defiler is out of view: waited for it to follow')
    if run.seen(lambda w: shown(w) is not None, FOLLOW_SECONDS) is None:
        LOG.info('Macro: no Defiler came into view: another is summoned')
        return None
    return shown(run.world())


def aim_at(run: Run, unit: int) -> bool:
    """Put the pointer on this Defiler where it stands now, following it while it walks. False when it never stood
    still: Consume must not be pressed (the bound demon may be under the pointer)."""
    for _ in range(AIM_TRIES):
        world = run.world()
        target = next((m for m in defilers(world) if m.unit_id == unit), None)
        if target is None or world.player is None:
            raise Abort('the Defiler is gone before Consume')
        rect = run.actuator.keys.focused_window_rect()
        if rect is None:
            raise Abort('no game window')
        if run.pad is not None:
            # Controller mode: the client's target has to name it (macros/pad.py); nothing else is consumed.
            here = (world.player.x, world.player.y)
            return run.pad.aim_unit(MONSTER_UNIT, unit, here, (target.x, target.y), 'the Defiler')
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


def consume(run: Run, defiler: Monster, tried: list[tuple[float, float]] | None = None) -> None:
    """Consume this Defiler and nothing else (it once took the bound demon, 2026-10-06/07): the key is pressed only
    while nothing stands near the Defiler or over its drawn body (`in_the_way`); if it stays crowded, another
    Defiler is summoned at another open spot. Afterwards the Defiler must be the one gone. A press that changes
    nothing (about one in thirty) is made again under the same checks."""
    missed, tried = False, tried if tried is not None else []
    for attempt in range(CONSUME_ATTEMPTS):

        def clear(w: World, unit: int = defiler.unit_id) -> bool:
            target = next((m for m in defilers(w) if m.unit_id == unit), None)
            return target is None or not crowd(w, target.x, target.y)

        if run.seen(clear, 1.0) is None:
            log_crowd(run.world(), defiler.unit_id)
            defiler = summon_defiler(run, skip=attempt + 1, tried=tried)
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
        before, began = (mine(run.world()) if run.pad is not None else {}), run.clock()
        press_skill(run, CONSUME)
        if run.pad is not None and not run.pad.pressed:
            continue  # the client's target left the Defiler before the press: nothing cast (`Pad target:`)

        def consumed(w: World, unit: int = defiler.unit_id) -> bool:
            return bool(w.player and w.player.consume) and all(m.unit_id != unit for m in defilers(w))

        done = run.seen(consumed, 2.5)
        if run.pad is not None:
            log_pad_consume(run, defiler.unit_id, before, began, done)
        if done is not None:
            run.pause('key')
            return
        world = run.world()
        log_miss(run, world, defiler.unit_id)
        untouched = world.player is not None and world.player.consume is False
        if not untouched or all(m.unit_id != defiler.unit_id for m in defilers(world)):
            raise Abort('Consume: not seen in 2.5s')  # something happened, and not what was meant
        missed = True
        target = next((m for m in defilers(world) if m.unit_id == defiler.unit_id), None)
        over = townsfolk_over(world, target.x, target.y) if target is not None else []
        if over and attempt + 1 < CONSUME_ATTEMPTS:
            LOG.info(
                'Macro: Consume showed nothing, a townsperson (class %d) %.1f from the Defiler: another is summoned',
                over[0].txt_id, math.hypot(over[0].x - defiler.x, over[0].y - defiler.y),
            )  # fmt: skip
            defiler = summon_defiler(run, skip=attempt + 1, tried=tried)
    if missed:
        raise Unconsumed(f'Consume: not seen in 2.5s, {CONSUME_ATTEMPTS} times over')
    raise Unconsumed('something stays too close to the Defiler, or it keeps walking; Consume was not pressed')


def log_consume(run: Run, when: str) -> None:
    """Research: the buff's record, to find where it keeps the time it has left."""
    player = run.world().player
    if player is not None and player.consume_node:
        LOG.info('Macro: Consume record %s (clock %.2f): %s', when, run.clock(), player.consume_node.hex())


def defiler_dance(cast: Casting) -> Tried:
    """End with a newly cast Consume and one Defiler out. Consume is always cast, never taken as good because it is
    active: its time left is not known (user, 2026-10-06). Two demon slots besides the bound demon, an active
    Consume holding one (user, 2026-10-10): a summon with both taken ends the oldest. So a standing Defiler is the
    one consumed, and the one that stays out is summoned after."""
    run, fresh = cast.run, cast.fresh
    log_consume(run, 'before')
    if fresh is not None:  # a new game: nothing is out, and the first summon may have to wait
        defiler = summon_defiler(run, until=fresh.started + LOAD_LIMIT)
        fresh.finish()
    else:
        defiler = in_view(run) or summon_defiler(run)
    try:
        consume(run, defiler)
    except Unconsumed as stop:
        if run.stops(stop):
            raise
        # The prebuff goes on without it: attack mode casts it in the field (buffs.py `consume_due`). 22:35:13 on
        # 2026-10-19: the game was left for it (~15 s)
        LOG.info('Macro: prebuff: no Consume (%s): the prebuff goes on without it; attack mode casts it later', stop)
        if not defilers(run.world()):
            summon_defiler(run)
        return Tried(run.clock())
    log_consume(run, 'after')
    if not defilers(run.world()):
        summon_defiler(run)
    return Tried(run.clock(), cast=True)


def renew_consume(run: Run) -> None:
    """Consume cast anew mid-run when the buff has run out (user, 2026-10-12: "auto-attack doesn't refresh consume
    buff right now"): a Defiler summoned for it is the one consumed, and another is summoned after. Not the standing
    one: it follows the character with the bound demon beside it."""
    take_prebuff_weapons(run)
    tried: list[tuple[float, float]] = []
    consume(run, summon_defiler(run, tried=tried), tried)
    if not defilers(run.world()):
        summon_defiler(run)


def consume_again(cast: Casting) -> Tried:
    """Consume cast again (`renew_consume`); a try that fails is logged and the mode goes on. The try
    counts from its start, also when it is stopped half way."""
    run = cast.run
    assert cast.world is not None
    assert cast.key_names is not None
    started = run.clock()
    if run.pad is not None:
        # Not by the pad: a pad summon lands beside the bound demon whatever the heading, and Consume failed on all of
        # four (rca/2026-10-14/run-1904-findings.md §3.6). Renewed in keyboard mode.
        LOG.info(
            'Macro: Consume: not renewed by the pad (its Defiler lands at the feet, by the bound demon); renewed in '
            'keyboard mode, asked again in %.0fs', CONSUME_PAD_WAIT,
        )  # fmt: skip
        return Tried.again(started, CONSUME_RETRY, CONSUME_PAD_WAIT, touched=False)
    cast.buffs.remember(cast.row, started)
    on = cast.world.player is not None and cast.world.player.consume is True
    run.say('Consume renewed before the boss' if on else 'Consume ran out: casting it again')
    try:
        run.keys.update(cast.key_names(cast.world, keys_of(cast.row)))
        renew_consume(run)
    except (Abort, ValueError) as stop:
        if run.stops(stop):
            raise
        # A key of the player's stopped it: no failure of the cast, so the next try comes soon.
        wait = CONSUME_RETRY
        tried = Tried(started)
        if 'a key was pressed' in str(stop) or PANEL_OPEN in str(stop):
            wait = CONSUME_SOON
            tried = Tried.again(run.clock(), CONSUME_RETRY, wait)
        LOG.info('Macro: no Consume (%s); again in %.0fs', stop, wait)
        return tried
    return Tried(started, cast=True)


def defiler_out(cast: Casting) -> Tried:
    """A Defiler summoned where none is alive (so it ends no Consume). In the quiet by `summon_defiler`; under the held
    strike one key at the first open spot (`Buffs.key`), the next look showing whether it came. A failed try is said
    and asked again after DEFILER_RETRY."""
    run, world = cast.run, cast.world
    assert world is not None
    assert cast.key_names is not None
    started = run.clock()
    try:
        run.keys.update(cast.key_names(world, (SUMMON_DEFILER,)))
        if cast.row.phase == 'fight':
            hand_off(world)
            spot = open_spots(run, world)[0]
            rect = run.actuator.keys.focused_window_rect()
            if run.pad is not None and world.player is not None and rect is not None:
                here = (world.player.x, world.player.y)
                run.pad.aim_place(here, world_point(world.player, *spot, rect[2] / rect[3]))
            else:
                run.actuator.aim(*spot, scatter=(40, 25))
            cast.buffs.key(run, SUMMON_DEFILER)
            LOG.info('Macro: Defiler: summoned under the strike at (%.2f, %.2f) of the window', *spot)
            return Tried(run.clock(), cast=True)
        LOG.info('Macro: Defiler: none out; summoning one')
        run.say('Summoning a Defiler')
        summon_defiler(run)
    except (Abort, ValueError) as stop:
        if run.stops(stop):
            raise
        LOG.info('Macro: no Defiler (%s); again in %.0fs', stop, DEFILER_RETRY)
        return Tried(started)
    return Tried(started, cast=True)


# Under the held strike the game's record of the unit under the pointer (`Run.hovered`) stays on what it named before,
# mostly the strike's own target, wherever the pointer goes: all 276 Engorge misses of the takes 20261020T2* came with
# the strike held, the live monster named stood a median 8.6 units off the corpse aimed at (96 of 172 more than 8),
# and 217 of 253 pairs of misses named the same unit at two corpses. So the record read before the pointer moves says
# what the read after it would. True (the player, 2026-10-20 ~23:20, of the batch identify: "we're not wasting time
# identifying individually every separate item but doing batch when we actually need it", "I'd like to see more this
# kind of mindset in other areas"; rca/2026-10-20/lazy-work-findings.md §2): with the strike held, a record that names
# a live monster or an item is a try not made, nothing touched, the next in ENGORGE_HOVER_RETRY; for a hurt demon
# (buffs.py `demon_hurt`) the strike is let go first instead, so that the record follows the pointer. A unit among the
# corpses read now is no live monster (26 of those misses named one the strike had just killed). False: the pointer
# put on the corpses and the record read there, the look's live monsters as they were.
ENGORGE_HOVER_FIRST = False
ENGORGE_HOVER_RETRY = 1.0  # seconds to the next look at the record while the held strike keeps it


def covers(over: tuple[int, int] | None, alive: set[int]) -> bool:
    """Whether the unit the record names keeps Engorge off the corpse: a live monster or an item's label."""
    return over is not None and (over[0] == ITEM_UNIT or (over[0] == MONSTER_UNIT and over[1] in alive))


def engorge(cast: Casting) -> Tried:
    """Engorge on the nearest corpse in view within ENGORGE_REACH. With no corpse there nothing is
    touched; with one that the pointer could not be kept on, the pointer was moved and no cast made.
    Under the held strike the record of what is under the pointer is read first (ENGORGE_HOVER_FIRST)."""
    run, world, aspect = cast.run, cast.world, cast.aspect
    assert world is not None
    assert aspect is not None
    assert cast.key_names is not None
    player = world.player
    assert player is not None
    assert run.corpses is not None
    here = (player.x, player.y)
    corpses = run.corpses()
    near = [
        corpse
        for corpse in corpses
        if math.dist(here, corpse[1:]) <= ENGORGE_REACH and on_screen(ground_fraction(player, *corpse[1:], aspect))
    ]
    every = engorge_every(world)
    if not near:
        return Tried.again(run.clock(), every, ENGORGE_RETRY, touched=False)
    alive = {m.unit_id for m in world.monsters}
    if ENGORGE_HOVER_FIRST:
        alive -= {unit for unit, _, _ in corpses}
        let_go = getattr(cast.buffs, 'let_go', None)
        if run.pad is None and run.hovered is not None and let_go is not None:
            over = run.hovered()
            if covers(over, alive):
                if not demon_hurt(world):
                    LOG.info('Macro: no Engorge: the held strike keeps the pointer record on %s; not moved', over)
                    return Tried.again(run.clock(), every, ENGORGE_HOVER_RETRY, touched=False)
                LOG.info('Macro: Engorge for a hurt demon: the strike let go, the pointer record on %s', over)
                let_go()
    run.keys.update(cast.key_names(world, (ENGORGE,)))
    # The nearest corpse the pointer really has under it (a live monster often stands on one).
    for unit, x, y in sorted(near, key=lambda corpse: math.dist(here, corpse[1:]))[:ENGORGE_LOOKS]:
        if run.pad is not None:
            # Controller mode: the client's target has to name the corpse (macros/pad.py).
            if not run.pad.aim_unit(MONSTER_UNIT, unit, here, (x, y), f'the corpse {unit}'):
                continue
            cast.buffs.key(run, ENGORGE)
            # Whether Engorge's target (controllerskillsettings.json targetGroup 0, the monsters) can name a corpse
            # at all: the aim's own `Pad target:` lines, and this one for a press (controller-gaps.md step 3).
            LOG.info(
                'Pad target: Engorge on the corpse %d at (%.1f, %.1f), %.1f away, by %s: %s',
                unit, x, y, math.dist(here, (x, y)), run.keys.get(ENGORGE),
                "pressed with the client's target on it" if run.pad.pressed else 'not pressed (the target moved off)',
            )  # fmt: skip
            return Tried(run.clock(), cast=run.pad.pressed)
        run.actuator.aim(*ground_fraction(player, x, y, aspect), scatter=(3, 3))
        over = None
        if run.hovered is not None:
            run.pace.sleep(HOVER_SECONDS)
            over = run.hovered()
            # Not cast with a live monster or an item's label under the pointer; with nothing
            # there it is (whether the record shows a corpse at all is not known yet).
            if covers(over, alive):
                LOG.info('Macro: no Engorge at (%.1f, %.1f): under the pointer %s, not the corpse %d', x, y, over, unit)
                continue
        cast.buffs.key(run, ENGORGE)
        at = run.clock()
        LOG.info(
            'Macro: Engorge on the corpse %d at (%.1f, %.1f), %.1f away; under the pointer %s',
            unit, x, y, math.dist(here, (x, y)), over,
        )  # fmt: skip
        return Tried(at, cast=True)
    # the pointer was moved: the strike's aim is put back
    return Tried.again(run.clock(), every, ENGORGE_RETRY)


# The sigil goes under the monster where it stands at the key, read again then (the player, 2026-10-20 ~23:05): the
# fight's rows are asked with the look before the strike, and a Death Mark cast first makes that 0.3-0.5 s old. Diablo,
# walking up at 10 units a second, had his sigil at 23:01:55 laid where he had stood, 11 units off him (the take
# 20261020T195849Z-108: the sigil at (7794.5, 5293.5), Diablo at (7803.0, 5287.0) as it showed). False: the look's.
SIGIL_AIM_AFRESH = True
# The sigils' memory per executor (`SigilWatch`): the executor (macros/buffs.py `Buffs`) holds no caster's own.
WATCHES: weakref.WeakKeyDictionary[object, SigilWatch] = weakref.WeakKeyDictionary()


def watch_of(executor: object) -> SigilWatch:
    """The memory of the sigil that lies, of this executor's casts."""
    found = WATCHES.get(executor)
    if found is None:
        found = WATCHES[executor] = SigilWatch()
    return found


def afresh(cast: Casting) -> Casting:
    """The cast with the world read now, the target where it stands now (SIGIL_AIM_AFRESH); as it was when the target
    is not read again."""
    if not SIGIL_AIM_AFRESH or cast.target is None:
        return cast
    world = cast.run.world()
    found = next((m for m in world.monsters if m.unit_id == cast.target.unit_id), None)
    if world.player is None or found is None:
        return cast
    return replace(cast, world=world, target=found)


def in_flight(run: Run, world: World | None) -> tuple[bool, tuple[float, float, float] | None]:
    """Whether the missiles were read, and the character's sigil among them as (x, y, radius) (skills.py
    SIGIL_MISSILES), None with none."""
    if run.flights is None or world is None or world.player is None:
        return False, None
    try:
        found = run.flights(frozenset(SIGIL_MISSILES))
    except OSError, ValueError, struct.error:
        return False, None
    mine = [(x, y, SIGIL_MISSILES[kind]) for owner, kind, x, y in found if owner == world.player.unit_id]
    return True, (mine[-1] if mine else None)


def sigil(cast: Casting) -> Tried:
    """Sigil: Lethargy on the ground under an elite (slows it, lowers its defence): the executor's
    cast on the ground under a monster, with the sigil's own wait when that is not in view. A monster kept in its
    sigil (buffs.py `kept`) is looked at every SIGIL_LOOK s and gets one when `keep_reason` names why; none sooner than
    SIGIL_GAP after the last."""
    run, target, world = cast.run, cast.target, cast.world
    watch = watch_of(cast.buffs)
    now = run.clock()
    area = world.player.area if world is not None and world.player is not None else None
    keeping = target is not None and kept(target)
    every = SIGIL_LOOK if keeping else SIGIL_SECONDS
    why, again = None, False
    if keeping and target is not None:
        again = watch.lies(now, area)  # one lies: this one is said with why
        judged = watch.age(now) >= SIGIL_SHOWS
        words = run.reads.unit_states(target) if judged else None
        by_place = words is None or watch.unshown.get(target.unit_id, 0) >= SIGIL_UNSHOWN
        seen, lying = in_flight(run, world) if judged and by_place else (False, None)
        why = keep_reason(watch, target, now, area, words, lying, seen)
        if why is None:
            # It stands in its sigil: looked at again in SIGIL_LOOK, or when the sigil runs out or a Herald's is old
            return Tried(min(now, watch.next_due(target) - SIGIL_LOOK), touched=False)
        if again and watch.age(now) < SIGIL_GAP:
            assert watch.at is not None
            return Tried(watch.at + SIGIL_GAP - every, touched=False)
    aimed = afresh(cast)
    tried = cast.buffs.shared(aimed)
    if not tried.cast:
        # Off the screen (the blades reach further than it shows): no sigil now, asked again in a second.
        return Tried.again(now, every, 1.0)
    if aimed.target is not None and tried.at is not None:
        if keeping and why is not None and why.startswith(UNSHOWN) and watch.unit == aimed.target.unit_id:
            watch.unshown[aimed.target.unit_id] = watch.unshown.get(aimed.target.unit_id, 0) + 1
        watch.lay(aimed.target.unit_id, (aimed.target.x, aimed.target.y), area, tried.at)
        if again:
            here = aimed.target
            LOG.info('Macro: sigil under %s at (%.1f, %.1f): %s', label(here), here.x, here.y, why)
    return tried


CASTERS: dict[str, Caster] = {
    'defiler dance': defiler_dance,
    'consume': consume_again,
    'engorge': engorge,
    'sigil': sigil,
    'defiler': defiler_out,
    **CTA_CASTERS,  # Call to Arms (macros/cta.py)
}
