"""The teleport key on a level that has a route stage (levels/routes.md, the execution layer).

One press performs one step of the stage the level is at (routes/progress.py), `press`:
- `enter`, `use`, `stand`: the level card leads with the stage's mark (levels/guide.py `lead_first`)
  and the teleport step goes there and walks in or clicks it, as it does for any first mark. An
  object that shows operated after the step is noted (`note_used`); a stand is done within
  STAND_NEAR of its mark.
- `fight`: the step toward the fight's mark, and attack mode on within FIGHT_NEAR of it; a fight
  that names no mark is attack mode from where the character stands. Attack mode casts Death Mark
  and the sigil itself (macros/rotation.py), so a stage's `opener` needs no cast of its own.
- `loot`: the pickup step. A press that finds nothing left ends the stage and goes on to the next
  one, unless that is `leave`: then it says so and stops, and only the next press leaves.
- `leave`: what is on the ground first; with nothing there the game is left, the next one made
  and the buffs cast (the macro request's own steps, macros/routines.py).
An `enter` across a border (no door: the Outer Cloister, the Monastery Gate, the Tamoe Highland) is
walked: from a room that touches the next level the press clicks the ground further out until the
level changes (`cross`).
At a level without a stage, or a stage that is `clear` or pending, the press is the plain teleport
step toward the card's own first mark, as before the routes.
"""

import math
from collections.abc import Callable
from functools import partial

from inventory_tracking.common import LOG
from inventory_tracking.levels.exits import outward
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
)
from inventory_tracking.macros.world import Player, World
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import ENTER, FIGHT, LEAVE, LOOT, STAND, USE, Stage
from inventory_tracking.routes.progress import Place, Progress


PERFORMED = frozenset((ENTER, USE, STAND, FIGHT, LOOT, LEAVE))  # the stage kinds a press performs: all but `clear`
STAND_NEAR = 12.0  # world units from a mark: the character has stood at it
# World units from a fight's mark at which attack mode is turned on: its sight (macros/hunt.py SIGHT).
FIGHT_NEAR = 40.0
STAGES = 3  # stages one press may pass: a loot with nothing to take goes on to the next
CROSS_CLICKS = 3  # ground clicks one press makes toward a level across a border
CROSS_UNITS = 16.0  # world units each of them is aimed ahead: in view whichever way it lies
CROSS_SECONDS = 2.0  # one click's walk


def card(
    run: Run,
    read: Callable[[], Target | None] | None,
    progress: Progress | None,
    seconds: float = CARD_SECONDS,
) -> Target | None:
    """The mark this press goes for: the level card's first (`teleport.card_for`), which is the
    stage's own when the card holds it. A stage whose mark the card does not hold yet (a border not
    read, a gap not named) is said, and the press follows the card as it would without a route: the
    key is not taken from a level the route cannot be followed on yet."""
    target = card_for(run, read, seconds)
    if target is None or progress is None:
        return target
    with run.lightly():
        player = run.world().player
    if player is None or target.area != player.area:
        return target  # the step says what is wrong with the card
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
    """After a step toward `target`: when it is the object of the level's `use` stage and the game
    shows that object operated (by this step's click, or before it: a chest the pickup key opened),
    progress is told. `marks(label)`: the places of the card's marks with the label, so a label on
    several objects (a hell pit's chests) is done only with each of them used. A portal needs no
    note: the level behind it is entered."""
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


def leave(run: Run, key_names) -> None:
    """Leave the game, make the next one and cast the buffs: the macro request's steps for a run
    that has ended (routines.run_macro), without its own look at whether it has. The route knows."""
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
    """Whether the press walks over the level's edge: the stage enters a level, the card leads with
    its mark, that mark is no door (the Outer Cloister and the Monastery Gate, the Tamoe Highland:
    levels/exits.py "Borders"), and the character stands in a room that touches the level. A room
    whose preset holds a warp tile in any layout is a door's room, never walked past."""
    if stage.kind != ENTER or area is None or target.area != area or target.label != stage.mark or target.warp:
        return False
    edge = [room for room in target.rooms if stage.to in room.leads_to]
    if any(has_warps(room.preset) for room in edge):
        return False
    x, y = player.x / TILE_UNITS, player.y / TILE_UNITS
    return any(room.x <= x < room.x + room.width and room.y <= y < room.y + room.height for room in edge)


def left_level(area: int, world: World) -> bool:
    return world.player is None or world.player.area != area


def cross(run: Run, name: str, target: Target, to: int) -> None:
    """Walk from a room on the level's edge on into level `to`: CROSS_CLICKS clicks on the ground,
    each CROSS_UNITS further out, until the level changes. A border has no door to click and a
    Teleport lands only on the level's own rooms, so the last stretch is walked. Not seen in the game
    yet (levels/routes.md, Phase 6)."""
    way = outward(target.rooms, to)
    rect = run.actuator.keys.focused_window_rect()
    if way is None or rect is None:
        raise Abort(f'no way across to {target.label} is known')
    aspect = rect[2] / rect[3]
    run.say(f'{name}: walking across to {target.label}')
    for _ in range(CROSS_CLICKS):
        player = run.world().player
        if player is None or player.area != target.area:
            break
        goal = (player.x + way[0] * CROSS_UNITS, player.y + way[1] * CROSS_UNITS)
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
    """One press of the teleport key. `plain(target)` is the teleport step toward the card's mark as
    the runner makes it (a valuable beside the character first, the boss in sight, the staff empty);
    `level()` the level map for a pickup; `attack()` turns attack mode on for after this press."""
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
