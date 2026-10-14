"""The Warlock's casts that are more than one aim and one key (macros/build.py `Build.casters`): the
Defiler's summon, Consume on a Defiler, the two together at a game's start and in the middle of a run,
Engorge on a corpse, and the sigil's own answer when its place is off the screen. Each is called by the
buff executor (macros/buffs.py) with a `Casting` and answers with a `Tried`.
"""

import math

from inventory_tracking.builds.warlock.buffs import (
    CONSUME_RETRY,
    CONSUME_SOON,
    ENGORGE_HURT_SECONDS,
    ENGORGE_LOOKS,
    ENGORGE_REACH,
    ENGORGE_RETRY,
    SIGIL_SECONDS,
)
from inventory_tracking.builds.warlock.skills import CONSUME, ENGORGE, SUMMON_DEFILER
from inventory_tracking.common import LOG
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.buffs import keys_of
from inventory_tracking.macros.build import Caster, Casting, Tried
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
from inventory_tracking.macros.travel import MONSTER_UNIT_TYPE
from inventory_tracking.macros.view import BODY_LIFT, FEET
from inventory_tracking.macros.world import DEFILER_CLASS as DEFILER, NO_OWNER, Monster, Player, World
from inventory_tracking.native.layout import HIRELING_CLASS_ID


# Right of the character, where the user summons; then other sides, a Defiler's width apart.
SUMMON_SPOTS = ((0.66, 0.42), (0.36, 0.44), (0.5, 0.26), (0.64, 0.62), (0.4, 0.64))
# The same sides at half the distance, for where the ground is known and narrow: in Cave Level 1 a prebuff
# summoned nothing at three of the spots above in 5 s (host, 02:43 on 2026-10-12).
NEAR_SPOTS = tuple((round((x + FEET[0]) / 2, 3), round((y + FEET[1]) / 2, 3)) for x, y in SUMMON_SPOTS)
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


def defilers(world: World) -> list[Monster]:
    return [monster for monster in world.monsters if monster.txt_id == DEFILER]


def bystanders(world: World, but: int | None = None) -> list[Monster]:
    """Every living monster Consume might take in place of the Defiler: the character's own (the
    bound demon: allied or owned) and any whose stats could not be read, but the mercenary and
    townsfolk. A hostile monster is not one: Consume cannot take it, and in the middle of a level
    the monsters around made every Defiler "crowded", so that four more were summoned, each ending
    the Consume in force or the oldest Defiler, and the press stopped (host, 18:48 on 2026-10-10)."""
    return [
        m
        for m in world.monsters
        if m.txt_id not in (DEFILER, HIRELING_CLASS_ID)
        and m.txt_id not in TOWN_NPCS
        and m.unit_id != but
        and (m.ally or m.owner != NO_OWNER or not m.max_life)
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
    a crowded spot back in front for a replacement. Where the level's ground is known (`run.ground`),
    only the spots a summon can stand on, the NEAR_SPOTS after the others; all of them when none can."""
    spots = list(SUMMON_SPOTS[skip % len(SUMMON_SPOTS) :] + SUMMON_SPOTS[: skip % len(SUMMON_SPOTS)])
    rect = run.actuator.keys.focused_window_rect()
    if rect is None or world.player is None:
        return spots
    player, aspect = world.player, rect[2] / rect[3]
    ground = run.ground() if run.ground is not None else None
    if ground:
        here = (player.x, player.y)
        known = [*spots, *NEAR_SPOTS]
        found = [spot for spot in known if standable(ground, here, world_point(player, *spot, aspect))]
        if len(found) < len(spots):
            LOG.info('Macro: %d of %d summon spots are on ground a Defiler can stand on', len(found), len(known))
        spots = found or spots
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
        rect = run.actuator.keys.focused_window_rect()
        if run.pad is not None and start.player is not None and rect is not None:
            # Controller mode: a heading toward the spot (macros/pad.py); the game puts it at its own distance.
            here = (start.player.x, start.player.y)
            run.pad.aim_place(here, world_point(start.player, *spot, rect[2] / rect[3]))
        else:
            run.actuator.move(*spot, scatter=(40, 25))
        press_skill(run, SUMMON_DEFILER)
        world = run.seen(lambda w: any(m.unit_id not in before for m in defilers(w)), 1.5)
        if world is None and not spots and until is not None and run.clock() < until:
            spots = open_spots(run, run.world())[:1]
            run.pause('screen')
    if world is None:
        raise Abort('Defiler: not seen at any spot')
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
        if run.pad is not None:
            # Controller mode: the client's target has to name it (macros/pad.py); nothing else is consumed.
            here = (world.player.x, world.player.y)
            return run.pad.aim_unit(MONSTER_UNIT_TYPE, unit, here, (target.x, target.y), 'the Defiler')
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
    if missed:
        raise Abort(f'Consume: not seen in 2.5s, {CONSUME_ATTEMPTS} times over')
    raise Abort('something stays too close to the Defiler, or it keeps walking; Consume was not pressed')


def log_consume(run: Run, when: str) -> None:
    """Research: the buff's record, to find where it keeps the time it has left."""
    player = run.world().player
    if player is not None and player.consume_node:
        LOG.info('Macro: Consume record %s (clock %.2f): %s', when, run.clock(), player.consume_node.hex())


def defiler_dance(cast: Casting) -> Tried:
    """End with a newly cast Consume and one Defiler out. Consume is always cast, never taken
    as good because it is active: how long it has left is not known, and it ran out in the
    middle of a run (user, 2026-10-06). The bound demon aside, the character has two demon slots
    and an active Consume holds one (user, 2026-10-10): a Defiler summoned with both taken ends
    the oldest, the Consume included. So a standing Defiler is the one consumed, never summoned
    over, and the Defiler that stays out is summoned after the Consume."""
    run, fresh = cast.run, cast.fresh
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
    return Tried(run.clock(), cast=True)


def renew_consume(run: Run) -> None:
    """Consume cast anew in the middle of a run (attack mode, when the buff has run out: 300 s after
    its cast, the 15% of life with it; user, 2026-10-12): a Defiler summoned for it is the one consumed,
    and another is summoned after. Not the standing one: it follows the character and has the bound
    demon beside it (09:57 to 09:58 on 2026-10-12: one try stopped at "crowded by class 361", the next
    aimed four times at a Defiler that had moved, and the buff stayed off; user: "auto-attack doesn't
    refresh consume buff right now"). The one summoned at 09:58:47 had Consume's key 0.6 s later."""
    take_prebuff_weapons(run)
    consume(run, summon_defiler(run))
    if not defilers(run.world()):
        summon_defiler(run)


def consume_again(cast: Casting) -> Tried:
    """Consume cast again (`renew_consume`); a try that fails is logged and the mode goes on. The try
    counts from its start, also when it is stopped half way."""
    run = cast.run
    assert cast.world is not None
    assert cast.key_names is not None
    started = run.clock()
    cast.buffs.remember(cast.row, started)
    on = cast.world.player is not None and cast.world.player.consume is True
    run.say('Consume renewed before the boss' if on else 'Consume ran out: casting it again')
    try:
        run.keys.update(cast.key_names(cast.world, keys_of(cast.row)))
        renew_consume(run)
    except (Abort, ValueError) as stop:
        if run.cancelled.is_set():
            raise
        # A key of the player's stops any routine: that try was no failure of the cast, so the next
        # comes soon (09:58:00 on 2026-10-12: stopped by a key, and 20 s without the buff).
        wait = CONSUME_RETRY
        tried = Tried(started)
        if 'a key was pressed' in str(stop):
            wait = CONSUME_SOON
            tried = Tried.again(run.clock(), CONSUME_RETRY, wait)
        LOG.info('Macro: no Consume (%s); again in %.0fs', stop, wait)
        return tried
    return Tried(started, cast=True)


ITEM_UNIT_TYPE = 4


def engorge(cast: Casting) -> Tried:
    """Engorge on the nearest corpse in view within ENGORGE_REACH. With no corpse there nothing is
    touched; with one that the pointer could not be kept on, the pointer was moved and no cast made."""
    run, world, aspect = cast.run, cast.world, cast.aspect
    assert world is not None
    assert aspect is not None
    assert cast.key_names is not None
    player = world.player
    assert player is not None
    assert run.corpses is not None
    here = (player.x, player.y)
    near = [
        corpse
        for corpse in run.corpses()
        if math.dist(here, corpse[1:]) <= ENGORGE_REACH and on_screen(ground_fraction(player, *corpse[1:], aspect))
    ]
    if not near:
        return Tried.again(run.clock(), ENGORGE_HURT_SECONDS, ENGORGE_RETRY, touched=False)
    run.keys.update(cast.key_names(world, (ENGORGE,)))
    alive = {m.unit_id for m in world.monsters}
    # The nearest corpse the pointer really has under it: of 12 casts on 2026-10-10 the record
    # named a monster under the pointer 11 times and an item's label once, and whether that monster
    # was the corpse was not known (a live one stands on a corpse often: the fight is there).
    for unit, x, y in sorted(near, key=lambda corpse: math.dist(here, corpse[1:]))[:ENGORGE_LOOKS]:
        if run.pad is not None:
            # Controller mode: the client's target has to name the corpse (macros/pad.py).
            if not run.pad.aim_unit(MONSTER_UNIT_TYPE, unit, here, (x, y), f'the corpse {unit}'):
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
            if over is not None and (over[0] == ITEM_UNIT_TYPE or (over[0] == MONSTER_UNIT_TYPE and over[1] in alive)):
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
    return Tried.again(run.clock(), ENGORGE_HURT_SECONDS, ENGORGE_RETRY)


def sigil(cast: Casting) -> Tried:
    """Sigil: Lethargy on the ground under an elite (slows it, lowers its defence): the executor's
    cast on the ground under a monster, with the sigil's own wait when that is not in view."""
    tried = cast.buffs.shared(cast)
    if not tried.cast:
        # Off the screen (the blades reach further than it shows): no sigil now, asked again in a second.
        return Tried.again(cast.run.clock(), SIGIL_SECONDS, 1.0)
    return tried


CASTERS: dict[str, Caster] = {
    'defiler dance': defiler_dance,
    'consume': consume_again,
    'engorge': engorge,
    'sigil': sigil,
}
