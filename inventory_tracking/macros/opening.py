"""Containers opened by the pickup step (the player, 2026-10-12: "in KP_1 mode - I'd like to click for ground
objects that are: close to current location; superchests").

With nothing to pick up, a press opens up to OPENS unopened containers within NEAR_UNITS, nearest first, else hops
toward a super chest anywhere in view ("we need to always click superchests/glowing chests"). Only then is the press a
seek step. Usability is the unit's own flag (game/decode.py `usable`); a click is made only with the object under the
pointer (`run.hovered`). One no click opened is shunned for SHUN_SECONDS. First host check: history/opening.md.
"""

import math
from dataclasses import dataclass
from functools import partial

from inventory_tracking.common import LOG
from inventory_tracking.game.decode import container_names, usable
from inventory_tracking.game.records import Thing
from inventory_tracking.levels.model import Level
from inventory_tracking.loot.ground import SPARKLY_CHEST
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.pickup import PICK_SECONDS, WALK_SPEED, Threat, approach, standing
from inventory_tracking.macros.routines import UNIT_PIXELS
from inventory_tracking.macros.teleport import HOVER_SECONDS, OBJECT_UNIT, ground_fraction, in_view, ready


NEAR_UNITS = 12.0  # world units: a container this near is opened on the way
# The glowing chests: objects.txt's InitFn 57 rows, ConsolationChest (397) and SpecialChest100 (455)
SUPER_CHESTS = frozenset((SPARKLY_CHEST, 455))
OPENS = 4  # containers one press opens at most
# Classic pixels from the object's ground point, tried in turn: the picture rises above that point
AIMS = ((0, -10), (0, 0), (0, -22), (12, -10), (-12, -10), (0, -36))
SHUN_SECONDS = 60.0
SHUNNED: dict[int, float] = {}  # unit id -> clock until which it is left alone
POLL = 0.05


@dataclass(frozen=True)
class Container:
    """A container to open, with the name the press says."""

    thing: Thing
    label: str

    @property
    def x(self) -> float:
        return self.thing.x

    @property
    def y(self) -> float:
        return self.thing.y


def choose(things: tuple[Thing, ...], here: tuple[float, float], now: float) -> Container | None:
    """The nearest unopened container within NEAR_UNITS, else the nearest unopened super chest shown."""
    for unit in [unit for unit, until in SHUNNED.items() if until <= now]:
        del SHUNNED[unit]

    def away(thing: Thing) -> float:
        return math.dist(here, (thing.x, thing.y))

    closed = [thing for thing in things if usable(thing) and thing.unit_id not in SHUNNED]
    near = [thing for thing in closed if away(thing) <= NEAR_UNITS]
    if near:
        found = min(near, key=away)
        name = 'the super chest' if found.txt_id in SUPER_CHESTS else container_names().get(found.txt_id, 'a chest')
        return Container(found, name)
    supers = [thing for thing in closed if thing.txt_id in SUPER_CHESTS]
    return Container(min(supers, key=away), 'the super chest') if supers else None


def opened(run: Run, thing: Thing) -> bool:
    """Whether the object is operated; one no longer shown counts."""
    assert run.containers is not None
    return not any(usable(found) for found in run.containers() if found.unit_id == thing.unit_id)


def open_one(run: Run, what: Container, level: Level | None, key_names) -> bool:
    """Approach, click and see `what` opened; whether it was."""
    thing = what.thing
    approach(run, what, level, key_names)
    if run.pad is not None:  # controller mode: stand by it, the target names it, A (macros/pad.py)
        if run.pad.interact(OBJECT_UNIT, thing.unit_id, (thing.x, thing.y), partial(opened, run, thing), what.label):
            run.say(f'{what.label}: opened')
            return True
        SHUNNED[thing.unit_id] = run.clock() + SHUN_SECONDS
        run.say(f'{what.label}: not opened')
        return False
    looked: list[str] = []
    for aim in AIMS:
        player = standing(run)
        rect = run.actuator.keys.focused_window_rect()
        if player is None or rect is None:
            raise Abort('not in a game')
        aspect = rect[2] / rect[3]
        away = math.dist((player.x, player.y), (thing.x, thing.y))
        across, down = ground_fraction(player, thing.x, thing.y, aspect)
        where = (across + aim[0] * UNIT_PIXELS[0] / 16 / aspect, down + aim[1] * UNIT_PIXELS[1] / 8)
        if not in_view(where):
            continue
        run.actuator.aim(*where, scatter=(2, 2))
        over = None
        if run.hovered is not None:
            run.pace.sleep(HOVER_SECONDS)
            over = run.hovered()
            if over != (OBJECT_UNIT, thing.unit_id):
                looked.append(f'{aim} {over}')
                continue
        run.actuator.click()
        began = run.clock()
        while run.clock() - began < PICK_SECONDS + away / WALK_SPEED:
            run.world()  # a cancel stops here
            if opened(run, thing):
                LOG.info(
                    'Macro: %s (object %d, class %d) opened %.2fs after the click %s pixels from its ground, from '
                    '%.1f away; under the pointer %s',
                    what.label, thing.unit_id, thing.txt_id, run.clock() - began, aim, away, over,
                )  # fmt: skip
                run.say(f'{what.label}: opened')
                return True
            run.pace.sleep(POLL)
        looked.append(f'{aim} {over} clicked')
    SHUNNED[thing.unit_id] = run.clock() + SHUN_SECONDS
    LOG.info(
        'Macro: %s (object %d, class %d) at (%.1f, %.1f) was not opened; the aims and what was under them: %s',
        what.label, thing.unit_id, thing.txt_id, thing.x, thing.y, '; '.join(looked) or 'none in view',
    )  # fmt: skip
    run.say(f'{what.label}: not opened')
    return False


def open_near(run: Run, level: Level | None, key_names, threat: Threat | None = None) -> bool:
    """Open the containers by the character or go for a super chest; whether there was one (then the press is not a
    seek step). With `threat` (pickup.py) one with monsters near is left closed."""
    if run.containers is None:
        return False
    tried = False
    for _ in range(OPENS):
        player, _rect = ready(run)
        what = choose(run.containers(), (player.x, player.y), run.clock())
        if what is None:
            break
        close = threat((player.x, player.y), (what.x, what.y)) if threat is not None else 0
        if close:
            LOG.info(
                'Macro: %s at (%.1f, %.1f) left closed: %d hostiles near it or the character',
                what.label,
                what.x,
                what.y,
                close,
            )
            run.say(f'{what.label} left for later: {close} monsters near')
            break
        tried = True
        level = level if level is not None and level.area == player.area else None
        run.say(f'Opening {what.label}, {math.dist((player.x, player.y), (what.x, what.y)):.0f} away')
        open_one(run, what, level, key_names)
    return tried
