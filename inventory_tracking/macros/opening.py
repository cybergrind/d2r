"""Chests opened by the pickup step (user, 2026-10-12: "in KP_1 mode - I'd like to click for ground
objects that are: close to current location; superchests").

With nothing to pick up (macros/pickup.py), a press opens what holds something and was not opened yet:
the containers within NEAR_UNITS of the character (chests, caskets, urns, corpses, racks: game/
`containers`), the nearest first and OPENS of them at most, and with none that near a super chest
wherever the game shows one ("we need to always click superchests/glowing chests"), which is hopped
toward like a drop. What falls out is the next press's. Only then is the press a seek step.

Whether a container can still be used is the game's own flag on the unit (game/decode.py `usable`,
UNIT_FLAGS), with objects.txt's word on its mode when that is unread. An aim is clicked only with that
object under the pointer by the game's own record (`run.hovered`); the object no longer usable is the
proof. One no click opened (a locked chest and no key, a picture the aims miss) is left alone for
SHUN_SECONDS.

On the host, 09:30 to 09:32 on 2026-10-12 (Glacial Trail, Drifter Cavern): a glowing chest of class 455
beside the character, a jar 9 away, a dead body 7 away and a glowing chest of class 397 from 67 away
(two hops) were each opened by the first aim, 0.1 to 0.5 s after the click. Not seen yet: a locked
chest, a barrel, an armour stand.
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
# The glowing chests: objects.txt's two rows with the sparkly chest's InitFn 57, ConsolationChest (397, the
# one the loot marks show) and SpecialChest100 (455); one of each was opened on the host (module text).
SUPER_CHESTS = frozenset((SPARKLY_CHEST, 455))
OPENS = 4  # containers one press opens at most
# Classic pixels from the object's ground point, tried in turn: the picture stands on that point and
# rises above it.
AIMS = ((0, -10), (0, 0), (0, -22), (12, -10), (-12, -10), (0, -36))
SHUN_SECONDS = 60.0
SHUNNED: dict[int, float] = {}  # unit id -> the clock until which a container no click opened is left alone
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
    """What a press opens next: the nearest unopened container within NEAR_UNITS, else the nearest
    unopened super chest the game shows."""
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
    """Whether the object is operated by now; one the game no longer shows counts as gone."""
    assert run.containers is not None
    return not any(usable(found) for found in run.containers() if found.unit_id == thing.unit_id)


def open_one(run: Run, what: Container, level: Level | None, key_names) -> bool:
    """Go to `what` if it is far, click it and see it opened; whether it was."""
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
    """The pickup step with nothing to pick up: open the containers by the character, or go for a
    super chest; whether there was one to open (then the press is not a seek step). With `threat`
    (pickup.py) a container is left closed while monsters are near it or the character, and the press
    is not spent on it."""
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
