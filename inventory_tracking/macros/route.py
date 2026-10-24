"""The teleport key on a level with a route stage (levels/routes.md): one press, one step (`press`).

- `enter`/`use`/`stand`: the card leads with the stage's mark and the teleport step goes to it.
- `fight`: toward the mark, attack mode within FIGHT_NEAR (no mark: attack mode where it stands).
- `loot`: the pickup step; nothing left ends the stage. `leave`: pick up, then the next game.
An `enter` across a border with no door is walked (`cross`). Without a performed stage the press is
the plain teleport step.
"""

import math
from collections.abc import Callable
from functools import partial

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Player, World
from inventory_tracking.levels.exits import door_passage, in_rooms, outward
from inventory_tracking.levels.model import Level, Target
from inventory_tracking.levels.presets import has_warps
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.pickup import pick_up
from inventory_tracking.macros.routines import character_keys, create_next_game, leave_game, prebuff
from inventory_tracking.macros.teleport import (
    CARD_SECONDS,
    MOVED,
    STILL_SECONDS,
    USES,
    WALK_POLL,
    card_for,
    ground_fraction,
    marked_thing,
    scaled,
    use_thing,
)
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import ENTER, FIGHT, LEAVE, LOOT, STAND, USE, Stage
from inventory_tracking.routes.progress import Place, Progress


PERFORMED = frozenset((ENTER, USE, STAND, FIGHT, LOOT, LEAVE))  # all kinds but `clear`
STAND_NEAR = 12.0  # world units: stood at the mark
# World units from a fight's mark to turn attack mode on: hunt.py SIGHT.
FIGHT_NEAR = 40.0
STAGES = 3  # stages one press may pass (empty loots)
CROSS_CLICKS = 3  # ground clicks one press makes toward a level across a border
CROSS_UNITS = 16.0  # world units each click aims ahead
CROSS_SECONDS = 2.0  # one click's walk
# 17:57:19-34 on 2026-10-23 (Outer Cloister into the Monastery Gate): six presses of "3 clicks toward Monastery Gate
# (+0, +1) and still on level 27" from the roof edge, and the zone was given up from that side. True: a door on the
# edge the walk crosses (levels/exits.py `door_passage`) is walked to, opened within CROSS_DOOR_NEAR, and gone through.
# False: straight out from where the character stands, as before.
CROSS_DOOR = True
CROSS_DOOR_NEAR = 15.0  # world units: as hunting/moves.py DOOR_NEAR


def card(
    run: Run,
    read: Callable[[], Target | None] | None,
    progress: Progress | None,
    seconds: float = CARD_SECONDS,
) -> Target | None:
    """The card's first mark (`teleport.card_for`). A stage mark not on the card yet is said and the
    card followed, so the key still works where the route cannot be followed yet."""
    target = card_for(run, read, seconds)
    if target is None or progress is None:
        return target
    with run.lightly():
        player = run.world().player
    if player is None or target.area != player.area:
        return target
    found = staged(progress, player.area)
    if found is None or not found[1].mark:
        return target
    name, stage = found
    if target.label != stage.mark:
        LOG.info('Macro: route %s: %s: the mark is not on the level card', name, stage.text())
        run.say(f'{name}: {stage.mark} is not marked yet; toward {target.label}')
        return target
    LOG.info('Macro: route %s: %s', name, stage.text())
    return target


def note_used(
    run: Run,
    target: Target | None,
    progress: Progress | None,
    marks: Callable[[str], tuple[Place, ...]] | None,
) -> None:
    """Tell progress when `target` is the `use` stage's object and shows operated (by any click).
    `marks(label)`: every place with the label, so a multi-object mark is done only when all are used."""
    if target is None or progress is None or not target.use or USES[target.use].leaves:
        return
    step = progress.step(target.area)
    if step is None or step.stage.kind != USE or step.stage.mark != target.label:
        return
    thing = marked_thing(run, target)
    if thing is None or not thing.mode:
        return
    places = marks(target.label) if marks is not None else ()
    progress.used(target.area, target.label, target.point, places or (target.point,))
    LOG.info('Macro: route %s: %s is done at (%.1f, %.1f)', step.route, step.stage.text(), *target.point)


def note_toured(run: Run, target: Target | None, progress: Progress | None, area: int | None) -> None:
    """A tour mark (routes/model.py `tour`) whose step changed the level is gone through: the tour skips it."""
    if target is None or progress is None or area is None or target.area != area:
        return
    step = progress.step(area)
    if step is None or not step.stage.tours or step.stage.mark != target.label:
        return
    with run.lightly():
        player = run.world().player
    if player is None or player.area == area:
        return
    progress.used(area, target.label, target.point, ())
    LOG.info('Macro: route %s: %s at (%.1f, %.1f) gone through into level %d', step.route, target.label,
             *target.point, player.area)  # fmt: skip


def note_empty(
    run: Run,
    target: Target,
    progress: Progress | None,
    marks: Callable[[str], tuple[Place, ...]] | None,
    why: str = 'none here',
) -> bool:
    """At a `use` mark showing no object: done with it if the object may be gone (`Use.gone`), True.
    The player, 2026-10-16: "count an empty mark as done". False for never-gone objects (a seal: a missed read)."""
    if progress is None or not target.use or not USES[target.use].gone:
        return False
    step = progress.step(target.area)
    if step is None or step.stage.kind != USE or step.stage.mark != target.label:
        return False
    places = marks(target.label) if marks is not None else ()
    progress.used(target.area, target.label, target.point, places or (target.point,))
    LOG.info('Macro: route %s: %s: %s at (%.1f, %.1f): done with it', step.route, target.label, why, *target.point)
    run.say(f'{target.label}: {why}')
    return True


def leave(run: Run, key_names) -> None:
    """Leave the game, make the next one and prebuff (routines.run_macro's steps, without its end check)."""
    world = run.world()
    run.keys = character_keys(run, key_names)
    run.actuator.wait_released()
    leave_game(run)
    trace = create_next_game(run, world.game_name)
    if key_names(run.world()) != run.keys:
        raise Abort('the skill keys changed')
    prebuff(run, fresh=trace)
    run.say('Prebuff done')


def borders(area: int | None, stage: Stage, target: Target, player: Player) -> bool:
    """Whether the press walks over the edge: an `enter` mark with no door (levels/exits.py "Borders") and
    the character in a room touching the level. A room whose preset has a warp tile is a door's, never walked."""
    if stage.kind != ENTER or area is None or target.area != area or target.label != stage.mark or target.warp:
        return False
    edge = [room for room in target.rooms if stage.to in room.leads_to]
    if any(has_warps(room.preset) for room in edge):
        return False
    x, y = player.x / TILE_UNITS, player.y / TILE_UNITS
    return any(room.x <= x < room.x + room.width and room.y <= y < room.y + room.height for room in edge)


def left_level(area: int, world: World) -> bool:
    return world.player is None or world.player.area != area


def past_edge(target: Target, player: Player, way: tuple[int, int]) -> tuple[float, float]:
    """The first point (world units) straight out from the character, `way`, that lies in none of the level's rooms."""
    x, y = player.x / TILE_UNITS, player.y / TILE_UNITS
    for _ in range(400):  # 0.25 tiles a step: 100 tiles at most
        if not in_rooms(target.rooms, (x, y)):
            break
        x, y = x + way[0] * 0.25, y + way[1] * 0.25
    return (x * TILE_UNITS, y * TILE_UNITS)


def cross(run: Run, name: str, target: Target, to: int) -> None:
    """Walk on into level `to` with ground clicks: Teleport lands only on the level's own rooms.
    Not seen in the game yet (levels/routes.md, Phase 6)."""
    way = outward(target.rooms, to)
    rect = run.actuator.keys.focused_window_rect()
    if way is None or rect is None:
        raise Abort(f'no way across to {target.label} is known')
    aspect = rect[2] / rect[3]
    run.say(f'{name}: walking across to {target.label}')
    for _ in range(CROSS_CLICKS):
        world = run.world()
        player = world.player
        if player is None or player.area != target.area:
            break
        goal = (player.x + way[0] * CROSS_UNITS, player.y + way[1] * CROSS_UNITS)
        via = door_passage(world.doors, target.rooms, past_edge(target, player, way)) if CROSS_DOOR else None
        if via is not None:
            door = min(world.doors, key=lambda d: math.dist((d.x, d.y), via))
            here = (player.x, player.y)
            if door.closed and math.dist(here, (door.x, door.y)) <= CROSS_DOOR_NEAR:
                thing = next(
                    (t for t in (run.things() if run.things is not None else ()) if t.unit_id == door.unit_id), None
                )
                if thing is not None:
                    LOG.info('Macro: route %s: the door on the edge at (%.1f, %.1f) opened first', name, door.x, door.y)
                    mark = Target(player.area, (), (door.x / TILE_UNITS, door.y / TILE_UNITS), target.label, 'target',
                                  use=door.txt_id)  # fmt: skip
                    use_thing(run, mark, player, thing, aspect)
                    continue
            away = math.dist(here, via)
            ratio = min(1.0, CROSS_UNITS / away) if away else 1.0
            goal = (here[0] + (via[0] - here[0]) * ratio, here[1] + (via[1] - here[1]) * ratio)
        if run.pad is not None:  # controller mode: the stick held that way (macros/pad.py)
            run.pad.walk(goal, near=MOVED, limit=CROSS_SECONDS, done=partial(left_level, target.area))
            continue
        run.actuator.aim(*ground_fraction(player, *goal, aspect), scatter=(4, 3))
        run.actuator.click()
        deadline, still, stood = run.clock() + CROSS_SECONDS, run.clock() + STILL_SECONDS, (player.x, player.y)
        while run.clock() < deadline:
            now = run.world().player
            if now is None or now.area != target.area or math.dist((now.x, now.y), goal) <= MOVED:
                break
            if run.clock() >= still and (now.x, now.y) == stood:
                break  # the click sent the character nowhere: the next one
            run.pace.sleep(WALK_POLL)
    now = run.world().player
    if now is not None and now.area != target.area:
        LOG.info('Macro: route %s: across the border to %s at (%.1f, %.1f)', name, target.label, now.x, now.y)
        run.say(f'{target.label}: there')
    else:
        LOG.info(
            'Macro: route %s: %d clicks toward %s (%+d, %+d) and still on level %d',
            name, CROSS_CLICKS, target.label, *way, target.area,
        )  # fmt: skip


def staged(progress: Progress | None, area: int) -> tuple[str, Stage] | None:
    """(route, stage) of the stage a press performs on level `area`; None with none to perform."""
    if progress is None:
        return None
    step = progress.step(area)
    if step is None or step.stage.kind not in progress.performed or step.stage.pending:
        return None
    return step.route, step.stage


def press(
    run: Run,
    progress: Progress | None,
    read: Callable[[], Target | None] | None,
    marks: Callable[[str], tuple[Place, ...]] | None,
    key_names,
    *,
    plain: Callable[[Target | None], None],
    level: Callable[[], Level | None],
    attack: Callable[[], None],
    leave: Callable[[Run, object], None] = leave,
) -> None:
    """One press. `plain(target)`: the runner's teleport step; `level()`: the map for a pickup;
    `attack()`: attack mode on after this press."""
    with run.lightly():
        player = run.world().player
    area = player.area if player is not None else None
    found = None
    for _ in range(STAGES):
        found = staged(progress, area) if area is not None else None
        if found is None or progress is None or area is None or found[1].kind not in (LOOT, LEAVE):
            break
        name, stage = found
        if pick_up(run, level(), key_names, lambda: None):
            return  # one press, one pickup: the next press looks again
        if stage.kind == LEAVE:
            LOG.info('Macro: route %s: leave', name)
            leave(run, key_names)
            return
        progress.looted(area)
        after = progress.step(area)
        if after is not None and after.stage.kind == LEAVE:
            run.say(f'{name}: nothing to pick up; the next press leaves the game')
            return
    if found is not None and found[1].kind == FIGHT and not found[1].mark:
        run.say(f'{found[0]}: {found[1].boss}, attack mode')
        attack()
        return
    target = card(run, read, progress)
    if found is not None and target is not None and player is not None and borders(area, found[1], target, player):
        cross(run, found[0], target, found[1].to)
        return
    plain(target)
    note_used(run, target, progress, marks)
    note_toured(run, target, progress, area)
    if found is None or progress is None or target is None or target.label != found[1].mark:
        return
    name, stage = found
    now = run.world().player
    away = math.dist((now.x, now.y), scaled(target.point)) if now is not None and now.area == target.area else math.inf
    if stage.kind == STAND and away <= STAND_NEAR:
        progress.stood(target.area, stage.mark)
        run.say(f'{name}: at {stage.mark}')
    elif stage.kind == FIGHT and away <= FIGHT_NEAR:
        attack()
