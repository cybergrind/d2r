"""The pad back end: a run's acts made with the virtual pad while the game is in controller mode.

A run plays in the game's mode at its start (`input_policy`); a flip mid-run raises `Flipped` and the runner
retries in the new mode. In controller mode the routines ask `Run.pad` (`PadActs`) wherever they would move the
pointer, click or tap a skill key: aim and cast, hold and steer, walk, interact, pick up. Records 12-15 are cast
by keyboard keys only after a probe showed it works (`KeyRoute`). No act presses a mouse button or a movement key
(either flips the client to mouse mode); `PadActuator.guard` stops the run unless the mode reads controller.
Design notes and the `Pad ...:` log lines: history/pad.md (rca/2026-10-13/controller-mode.md).
"""

import math
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from inventory_tracking.combat.stance import AWARE, RUN_SPEED, WALK_LATENCY
from inventory_tracking.common import LOG
from inventory_tracking.game.layout import ITEM_UNIT, NO_OWNER
from inventory_tracking.input.gamepad import KEY_RECORDS, MODIFIER, Pad, record_buttons, record_label
from inventory_tracking.input.keybindings import MODIFIERS, action_keys, button_number, x11_name
from inventory_tracking.levels.geometry import Point
from inventory_tracking.macros.actuator import Abort, Actuator, Cancelled, Flipped
from inventory_tracking.macros.skills import (
    ACTIONS,
    ATTACK,
    SWAP_WEAPONS,
    TELEPORT,
    register_names,
    skill_name,
    slot_action,
)
from inventory_tracking.models import InputMode


if TYPE_CHECKING:
    from inventory_tracking.game.records import World
    from inventory_tracking.macros.engine import Run
    from inventory_tracking.tracking.input_mode import ControllerState


# The controller's own pickup skills (skills.txt; controllerskillsettings.json: the nearest item within 4 units).
LOOT, LOOT_TO_CUBE = 358, 370
register_names({LOOT: 'Loot', LOOT_TO_CUBE: 'Loot to Cube'})
RECORDS = 12  # records 0-5 are A X B Y RB RT, 6-11 the same with LT held (input/gamepad.py)

# World heading -> stick: the client turns the stick by -45 degrees into the world (0x1400d7630, constant
# 0xbec90fdb). Pad.stick takes screen directions (x right, y down). Squash and y sign inferred (history/pad.md).
STICK_SQUASH = 1.0
STICK_Y = 1.0
WALK_STICK = 1.0  # a walk: the stick all the way (past stickRunToggleThreshold 0.8: a run, inferred)
FACE_STICK = 0.5  # a nudge that turns the character toward a unit: past the 0.4 dead zone (read)
FACE_SECONDS = 0.05  # held that long: about three of the game's frames, a turn and not a step (inferred)
AIM_STICK = 0.6  # held while the button of a cast with a heading goes down (the free target's direction)
# Stick held this long before a heading cast's button, and through it: the client takes a free target's direction
# from the facing at the button's down, and the stick turns the facing a frame or two later
# (rca/2026-10-14/run-1904-findings.md §3.1).
AIM_LEAD = 0.08
# Degrees: a pad jump landing further off its heading has the next leg walked, since the next jump tends to go the
# same wrong way (2026-10-14 22:06:56, 14 in a row at 90 degrees); walks are accurate.
ASTRAY = 60.0
ASTRAY_SECONDS = 3.0  # an astray jump's walk is owed this long at most (no walk asked meanwhile: a fight, a stop)
TARGET_WAIT = 0.3  # seconds the controller's target is given to name the unit after the nudge
TARGET_POLL = 0.02
STEER_EVERY = 0.25  # seconds between two nudges under the held strike
WALK_POLL = 0.05  # seconds between two looks of a walk
WALK_TURN = math.radians(6)  # the stick is moved again when the way to the place turns more than this
WALK_NEAR = 1.5  # units from the place a walk ends at
STALL_SECONDS = 0.7  # a walk that gained nothing for this long has ended
MEASURE_UNITS = 3.0  # units walked before the way the stick sent the character is measured
MOVED = 2.0  # units a jump must have carried the character for a landing (teleport.py MOVED)
JUMP_WATCH = 1.5  # seconds a jump's landing is watched for after its press
TELEPORT_REACH = 23.0  # Teleport's controller `defaultTargetDistance` (controllerskillsettings.json, read)
PICK_REACH = 4.0  # units the controller's Loot takes the nearest item within (read)
PICK_STAND = 0.8  # units from an item the character stands at for it to be the nearest
PICK_SECONDS = 1.0  # for the item to leave the ground after the press
INTERACT_REACH = 5.2  # units the controller's Interact group reaches objects within (read)
INTERACT_STAND = 2.5
INTERACT_SECONDS = 1.5
DRINK_WATCH = 1.0  # seconds a belt cell is watched for emptying after its key
KEY_WATCH = 1.5  # seconds the probe's state is watched for after its key
PROBE_CLEAR = AWARE  # no hostile within this many units: the probe's quiet moment
# Keys a keyboard slot may hold that the route never presses: keypad 5 is the service's own pad hotkey (it taps X).
UNPRESSABLE = frozenset(('KP_5', 'KP_Begin'))


def heading_degrees(vector: Point) -> float:
    return math.degrees(math.atan2(vector[1], vector[0]))


def turned(a: float, b: float) -> float:
    """The angle from heading `b` to heading `a`, degrees in (-180, 180]."""
    return (a - b + 180.0) % 360.0 - 180.0 or 0.0


def stick_for(heading: Point, magnitude: float = 1.0) -> Point:
    """The stick (screen x right, y down) that sends the character along world `heading`."""
    dx, dy = heading
    across, down = dx - dy, STICK_SQUASH * (dx + dy) * STICK_Y
    length = math.hypot(across, down)
    if length == 0:
        return (0.0, 0.0)
    return (magnitude * across / length, magnitude * down / length)


def records(bindings: Sequence[int] | None, *, by_key: bool = False) -> dict[int, int]:
    """skill -> the first of records 0-11 holding it (12-15 too `by_key`); empty while bindings are unread."""
    found: dict[int, int] = {}
    for record, skill in enumerate(list(bindings or ())[: KEY_RECORDS.stop if by_key else RECORDS]):
        if skill != -1:
            found.setdefault(skill, record)
    return found


def pad_slots(
    bindings: Sequence[int] | None, keyed: Sequence[int | None], *, by_key: bool = False
) -> tuple[int | None, ...]:
    """The skills on pad records, standing for `World.slots`. Teleport counts only when also on a key: it comes
    from an item, and a record naming it casts nothing without one."""
    return tuple(skill for skill in records(bindings, by_key=by_key) if skill != TELEPORT or TELEPORT in keyed)


@dataclass
class KeyRoute:
    """Whether keyboard skill keys reach controller records 12-15 (no pad button) this session: unknown until a
    probe (`PadActs.probe_key`), then open or closed by its outcome. `enabled` is config `controller_key_route`."""

    enabled: bool = True
    ok: bool | None = None  # the last probe's outcome; None: none this session
    probed: set[str] = field(default_factory=set)  # games probed (once a game)
    unkeyed: set[int] = field(default_factory=set)  # records whose slot has no pressable key, logged once

    @property
    def open(self) -> bool:
        return self.enabled and self.ok is True

    def due(self, game: str) -> bool:
        """Whether a probe may still be made in this game."""
        return self.enabled and game not in self.probed


def hostile_near(world: World, reach: float) -> bool:
    """Whether an unowned, non-town monster stands within `reach`: the probe waits for a quiet moment."""
    from inventory_tracking.macros.routines import TOWN_NPCS  # late: routines.py is above this module

    player = world.player
    if player is None:
        return True
    here = (player.x, player.y)
    return any(
        m.owner == NO_OWNER
        and not m.ally
        and m.txt_id not in TOWN_NPCS
        and m.unit_id not in world.dead
        and math.dist(here, (m.x, m.y)) <= reach
        for m in world.monsters
    )


def input_policy(mode: InputMode | None, *, enabled: bool) -> bool:
    """Whether a run plays by the pad (True) or keys and mouse (False), from the game's mode at its start; Abort
    when it cannot play now. The run follows the mode and never flips it. Unreadable mode: keyboard."""
    if mode is None:
        return False
    if mode.pending:
        going = 'controller' if mode.wanted else 'keyboard'
        raise Abort(f'the game is switching to {going} mode: press again after it')
    if not mode.controller:
        return False
    if not enabled:
        raise Abort('the game is in controller mode and controller play is off (config controller_play): click once')
    return True


@dataclass(frozen=True)
class PadPlay:
    """What the service hands the runner for controller mode: the lazily made pad, and the input mode, controller
    state and loaded bindings as `InputModeWatch` reads them."""

    device: Callable[[], Pad | None]
    mode: Callable[[], InputMode | None]
    controller: Callable[[], ControllerState | None]
    bindings: Callable[[], Sequence[int] | None]
    enabled: bool = True  # config `controller_play`
    route: KeyRoute = field(default_factory=KeyRoute)  # kept for the session


class PadActuator:
    """The pad behind the keys' guard (cancel, focus, a player's key) plus its own: a mouse button down, or the
    game not in controller mode with no flip pending, stops the run (such a press is lost or flips the mode)."""

    def __init__(
        self,
        device: Callable[[], Pad | None],
        mode: Callable[[], InputMode | None],
        keys: Actuator,
    ) -> None:
        self.device = device
        self.mode = mode
        self.keys = keys
        self.made: Pad | None = None

    @property
    def pad(self) -> Pad:
        if self.made is None:
            self.made = self.device()
            if self.made is None:
                raise Abort('no virtual pad (see the log: /dev/uinput)')
        return self.made

    def guard(self) -> None:
        keys = self.keys
        if keys.cancelled is not None and keys.cancelled.is_set():
            raise Cancelled
        if not keys.focused():
            raise Abort('the game lost the focus')
        if keys.key_held():
            codes = sorted(keys.keys.held_keys() - keys.allowed - keys.holding)
            raise Abort(f'a key was pressed (key code {", ".join(map(str, codes)) or "?"})')
        if any(keys.button_held(button) for button in (1, 2, 3)):
            raise Abort('a mouse button was pressed (the game leaves controller mode)')
        mode = self.mode()
        if mode is None:
            raise Abort('the input mode cannot be read')
        if mode.pending:
            raise Flipped('the input mode is switching')
        if not mode.controller:
            raise Flipped('the game is in keyboard mode now')

    def press(self, *names: str) -> None:
        self.guard()
        self.pad.press(*names)
        self.keys.mark('first_key')

    def release(self, *names: str) -> None:
        self.pad.release(*names)

    def tap(self, record: int) -> None:
        names = record_buttons(record)
        self.press(*names)
        try:
            self.keys.pace.hold()
        finally:
            self.release(*names)

    def key(self, name: str) -> None:
        """A keyboard skill key, casting its slot's controller record (`KeyRoute`). LT is let go first: held, the
        client would take the record six further on."""
        self.guard()
        if self.made is not None and MODIFIER in self.made.down:
            self.made.release(MODIFIER)
        self.keys.tap(name)
        self.keys.mark('first_key')

    def stick(self, x: float, y: float) -> None:
        if (x, y) != (0.0, 0.0):
            self.guard()
        self.pad.stick('left', x, y)

    def neutral(self) -> None:
        """Everything let go and the sticks centred: a held input bars the way back to mouse mode."""
        if self.made is not None:
            try:
                self.made.neutral()
            except OSError as exc:  # the device gone: nothing is held on it, the run's own end stands
                LOG.warning('Pad act: the pad could not be let go: %s', exc)


@dataclass(frozen=True)
class Aimed:
    """What the next cast is for: a unit the controller's target names, or a heading from `here`."""

    here: Point
    there: Point
    unit: tuple[int, int] | None = None  # (unit type, unit id)

    @property
    def heading(self) -> Point:
        return (self.there[0] - self.here[0], self.there[1] - self.here[1])


@dataclass
class Jumped:
    """A jump made by the pad, watched for its landing (`PadActs.seen`)."""

    skill: int
    start: Point
    heading: Point
    reach: float
    planned: float  # units to the place the planner chose
    at: float
    moved: Point | None = None  # where the character was seen first away from the start


class PadActs:
    """The acts of one run in controller mode."""

    def __init__(
        self,
        run: Run,
        actuator: PadActuator,
        controller: Callable[[], ControllerState | None],
        bindings: Callable[[], Sequence[int] | None],
        route: KeyRoute | None = None,
    ) -> None:
        self.run = run
        self.actuator = actuator
        self.controller = controller
        self.bindings = bindings
        self.route = route if route is not None else KeyRoute()
        self.key_file: Callable[[], bytes] | None = None  # set by `keys`
        self.aimed: Aimed | None = None
        self.pressed = False  # whether the last `cast` pressed its record
        self.jumped: Jumped | None = None
        self.astray: tuple[int, float] | None = None  # (skill, clock) of the last jump off by > ASTRAY
        self.nudged_at = -math.inf
        self.steered: dict[int, float | None] = {}  # unit id -> when the strike's target named it (None: not yet)
        self.settled: set[tuple[int, int]] = set()  # units whose settling time is logged

    # What the run can cast, and with what.

    @property
    def reach(self) -> dict[int, float]:
        """skill -> the controller's fixed jump distance: the build's `JumpSource.pad_reach`, plus Teleport's."""
        found = {TELEPORT: TELEPORT_REACH}
        for movement in self.run.build.movement:
            for source in movement.sources:
                if source.pad_reach is not None:
                    found[source.jump.skill] = source.pad_reach
        return found

    def record(self, skill: int) -> int:
        loaded = self.bindings()
        found = records(loaded, by_key=self.route.open).get(skill)
        if found is None:
            if not loaded:
                raise Abort('the controller bindings the game loaded are not read yet: press again in a moment')
            if skill in records(loaded, by_key=True):
                raise Abort(
                    f'{skill_name(skill)} is on record {records(loaded, by_key=True)[skill]}, reached by a key only, '
                    'and no `Pad key:` probe has shown that the keys reach the records in this session'
                )
            raise Abort(
                f'{skill_name(skill)} is on no pad record (controller bindings: config gamepad_bindings); '
                'mouse mode casts it: click once to switch'
            )
        return found

    def slots(self, keyed: Sequence[int | None]) -> tuple[int | None, ...]:
        return pad_slots(self.bindings(), keyed, by_key=self.route.open)

    def slot_key(self, record: int) -> str | None:
        """The key of keyboard skill slot `record`, which casts controller record `record` (Quick Cast on); None
        when it has no pressable key (a mouse button flips the mode; keypad 5 is the service's; a modifier)."""
        if self.key_file is None:
            return None
        try:
            codes = action_keys(self.key_file(), slot_action(record))
        except OSError, ValueError:
            return None
        for code in codes:
            name = x11_name(code)
            if name and name not in MODIFIERS and name not in UNPRESSABLE and button_number(name) is None:
                return name
        return None

    def record_key(self, record: int) -> str:
        key = self.slot_key(record)
        if key is None:
            raise Abort(f'keyboard skill slot {record} has no key the macro can press: record {record} is out of reach')
        return key

    def label(self, record: int) -> str:
        """'Y', 'LT+B'; a record reached by a key: 'key 7 (record 13)'."""
        return f'key {self.record_key(record)} (record {record})' if record in KEY_RECORDS else record_label(record)

    def keys(self, skills: Sequence[int], key_file: Callable[[], bytes]) -> dict[int, str]:
        """Each skill's record label, as `skill_keys` gives keys; Swap Weapons is its keyboard key. Abort names
        the first skill on no record."""
        self.key_file = key_file
        found = {}
        for skill in skills:
            if skill in ACTIONS:
                codes = action_keys(key_file(), ACTIONS[skill])
                key = next((k for k in map(x11_name, codes) if k and k not in MODIFIERS), None)
                if key is None:
                    raise Abort(f'{skill_name(skill)} has no key the macro can press')
                found[skill] = key
            else:
                found[skill] = self.label(self.record(skill))
        return found

    def ring(self, skill: int) -> tuple[float, float] | None:
        """The distances a jump by `skill` may be planned at (fixed reach ± PAD_SLACK); None: no fixed reach."""
        from inventory_tracking.macros.build import PAD_SLACK  # late: build.py is above this module

        reach = self.reach.get(skill)
        return None if reach is None else (reach - PAD_SLACK, reach + PAD_SLACK)

    # Each look at the game.

    def seen(self, world: World) -> World:
        """The world with record skills for key skills; also watches a jump's landing (`Pad jump:`)."""
        jumped, player = self.jumped, world.player
        if jumped is not None and player is not None:
            now, here = self.run.clock(), (player.x, player.y)
            away = math.dist(here, jumped.start) >= MOVED
            if away and jumped.moved is not None and math.dist(here, jumped.moved) < 0.3:
                self.landed(jumped, here, now)  # seen away and standing: the landing
            elif away:
                jumped.moved = here
            elif now - jumped.at > JUMP_WATCH:
                LOG.info(
                    'Pad jump: %s toward %.0f degrees: no landing %.1fs after the press (the character at '
                    '(%.1f, %.1f))',
                    skill_name(jumped.skill), heading_degrees(jumped.heading), now - jumped.at, *here,
                )  # fmt: skip
                self.jumped = None
        return replace(world, slots=self.slots(world.slots))

    def landed(self, jumped: Jumped, here: Point, now: float) -> None:
        went = (here[0] - jumped.start[0], here[1] - jumped.start[1])
        off = turned(heading_degrees(went), heading_degrees(jumped.heading))
        LOG.info(
            'Pad jump: %s toward %.0f degrees, reach %.0f (planned %.1f): landed %.1f away at %.0f degrees, off '
            '%+.0f degrees and %+.1f units, %.2fs after the press',
            skill_name(jumped.skill), heading_degrees(jumped.heading), jumped.reach, jumped.planned,
            math.hypot(*went), heading_degrees(went), off, math.hypot(*went) - jumped.reach, now - jumped.at,
        )  # fmt: skip
        self.jumped = None
        if abs(off) > ASTRAY:
            self.astray = (jumped.skill, now)
            LOG.info(
                'Macro: pad jump: %s landed %+.0f degrees off the heading asked (%.0f): the next leg is walked',
                skill_name(jumped.skill), off, heading_degrees(jumped.heading),
            )  # fmt: skip

    def landing(self, here: Point) -> None:
        """The jump's caller saw it land at `here`: judge it now, before the next leg is chosen."""
        if self.jumped is not None and math.dist(here, self.jumped.start) >= MOVED:
            self.landed(self.jumped, here, self.run.clock())

    def walk_owed(self, now: float) -> bool:
        """Whether the next leg is walked: a jump went astray < ASTRAY_SECONDS ago, no walk since."""
        return self.astray is not None and now - self.astray[1] < ASTRAY_SECONDS

    # Aims, and the press that follows them.

    def target(self) -> tuple[int, int] | None:
        state = self.controller()
        return None if state is None else state.target

    def nudge(self, heading: Point) -> None:
        """The character turned toward `heading` by a short push of the stick, centred after it."""
        self.nudged_at = self.run.clock()
        try:
            self.actuator.stick(*stick_for(heading, FACE_STICK))
            self.run.pace.sleep(FACE_SECONDS)
        finally:
            self.actuator.stick(0.0, 0.0)

    def aim_unit(self, kind: int, unit: int, here: Point, there: Point, what: str = '') -> bool:
        """Aim the next cast at unit (`kind`, `unit`): whether the controller's target names it, now or within
        TARGET_WAIT of a nudge. Not named: the caller casts nothing (the client would cast at what it holds)."""
        wanted, began = (kind, unit), self.run.clock()
        aimed = Aimed(here, there, wanted)
        if self.target() == wanted:
            self.aimed = aimed
            return True
        self.nudge(aimed.heading)
        while True:
            held = self.target()
            if held == wanted:
                if wanted not in self.settled:
                    self.settled.add(wanted)
                    LOG.info(
                        'Pad target: %s named %.0f ms after a nudge toward %.0f degrees, %.1f away',
                        what or f'unit {wanted}', 1000 * (self.run.clock() - began),
                        heading_degrees(aimed.heading), math.dist(here, there),
                    )  # fmt: skip
                self.aimed = aimed
                return True
            if self.run.clock() - began >= TARGET_WAIT:
                break
            if self.run.cancelled.is_set():
                raise Cancelled
            self.run.pace.sleep(TARGET_POLL)
        LOG.info(
            'Pad target: %s wanted at %.0f degrees, %.1f away; the client holds %s after %.0f ms: not cast',
            what or f'unit {wanted}', heading_degrees(aimed.heading), math.dist(here, there), held,
            1000 * (self.run.clock() - began),
        )  # fmt: skip
        self.aimed = None
        return False

    def aim_place(self, here: Point, there: Point) -> None:
        """The next cast goes toward `there`: a ground cast lands at its skill's own distance that way."""
        self.aimed = Aimed(here, there)

    def press_record(self, record: int) -> None:
        """Record `record` pressed once: its button (with LT for 6-11), or its keyboard key for 12-15."""
        if record in KEY_RECORDS:
            self.actuator.key(self.record_key(record))
        else:
            self.actuator.tap(record)

    def cast(self, skill: int) -> bool:
        """Press the skill's record once toward the last aim (none: on the character); whether it was pressed. A
        unit cast is pressed only while the target still names it: the client casts at what it holds (Consume's
        group holds the bound demon and the mercenary too)."""
        aimed, self.aimed = self.aimed, None
        self.pressed = False
        if skill == SWAP_WEAPONS:
            key = self.run.keys[skill]
            self.run.actuator.tap(key)  # a keyboard key: flips nothing (gamepad-proton.md §5)
            LOG.info('Pad swap: key %s pressed in controller mode', key)
            self.pressed = True
            return True
        record = self.record(skill)
        if aimed is not None and aimed.unit is not None:
            held = self.target()
            if held != aimed.unit:
                LOG.info(
                    'Pad target: %s for %s, named at the aim; the client holds %s at the press: not cast',
                    skill_name(skill), aimed.unit, held,
                )  # fmt: skip
                return False
        self.pressed = True
        if aimed is not None and aimed.unit is None:
            heading = aimed.heading
            try:
                # Stick first, AIM_LEAD before the button, and held through it (see AIM_LEAD).
                self.actuator.stick(*stick_for(heading, AIM_STICK))
                self.run.pace.sleep(AIM_LEAD)
                if record in KEY_RECORDS:
                    self.actuator.key(self.record_key(record))
                else:
                    names = record_buttons(record)
                    self.actuator.press(*names)
                    try:
                        self.run.pace.hold()
                    finally:
                        self.actuator.release(*names)
            finally:
                self.actuator.stick(0.0, 0.0)
            reach = self.reach.get(skill)
            if reach is not None:
                self.jumped = Jumped(skill, aimed.here, heading, reach, math.hypot(*heading), self.run.clock())
            LOG.info(
                'Pad act: %s on %s toward %.0f degrees (%.1f away)',
                skill_name(skill), self.label(record), heading_degrees(heading), math.hypot(*heading),
            )  # fmt: skip
            return True
        self.press_record(record)
        LOG.info(
            'Pad act: %s on %s%s',
            skill_name(skill), self.label(record), '' if aimed is None else f' at the target {aimed.unit}',
        )  # fmt: skip
        return True

    def probe_key(self, skill: int, shown: Callable[[], bool | None]) -> bool:
        """The key route's probe (rca/2026-10-13/controller-gaps.md step 2): once a game, at a quiet moment, cast
        `skill` (a self buff whose state `shown` reads, now off) by its slot's keyboard key. The state appearing
        within KEY_WATCH opens the route, else it closes and the button casts it. Whether this made the cast."""
        route = self.route
        world = self.run.world()
        if world.player is None or not route.due(world.game_name):
            return False
        record = records(self.bindings()).get(skill)
        if record is None:
            return False
        key = self.slot_key(record)
        if key is None:
            if record not in route.unkeyed:
                route.unkeyed.add(record)
                LOG.info(
                    'Pad key: %s is on %s, and keyboard slot %d has no key the macro can press: not the probe',
                    skill_name(skill), record_label(record), record,
                )  # fmt: skip
            return False
        if shown() is not False or hostile_near(world, PROBE_CLEAR):
            return False  # on already (proves nothing), or not quiet
        route.probed.add(world.game_name)
        began = self.run.clock()
        self.actuator.key(key)
        pressed: list[tuple[int, int]] = []  # (record, skill) the controller state named after the key
        appeared: float | None = None
        while appeared is None and self.run.clock() - began < KEY_WATCH:
            state = self.controller()
            if state is not None and state.record != -1 and (state.record, state.skill) not in pressed:
                pressed.append((state.record, state.skill))
            if shown():
                appeared = self.run.clock() - began
                break
            self.run.pace.sleep(TARGET_POLL)
        client = ', '.join(f'record {r} skill {skill_name(s)}' for r, s in pressed) or 'no record'
        was = route.ok
        route.ok = appeared is not None
        if appeared is not None:
            LOG.info(
                'Pad key: %s (keyboard slot %d) in controller mode -> record %d %s: shown after %.2fs (the client '
                'pressed %s); records 12-15 are cast by their keys in this session',
                key, record, record, skill_name(skill), appeared, client,
            )  # fmt: skip
            return True
        LOG.info(
            'Pad key: %s (keyboard slot %d) in controller mode -> record %d %s: not shown in %.1fs (the client '
            'pressed %s); pressing %s; records 12-15 %s',
            key, record, record, skill_name(skill), KEY_WATCH, client, record_label(record),
            'are no longer used in this session' if was else 'stay unused',
        )  # fmt: skip
        self.cast(skill)
        return True

    @contextmanager
    def hold(self, skill: int) -> Generator[Callable[[], None]]:
        """Hold the skill's record through the block (the client recasts at its own target). Yields `again` with
        `again.release`, as `Actuator.hold` does. Key-only records (12-15) cannot be held."""
        record = self.record(skill)
        if record in KEY_RECORDS:
            raise Abort(f'{skill_name(skill)} is on record {record}, reached by a key only: the pad holds no key')
        names = record_buttons(record)
        down = False

        def release() -> None:
            nonlocal down
            if down:
                down = False
                self.actuator.release(*names)

        def again() -> None:
            nonlocal down
            release()
            if self.run.cancelled.is_set():
                raise Cancelled
            self.run.pace.hold()
            self.actuator.press(*names)
            down = True

        again.release = release  # type: ignore[attr-defined]
        try:
            self.actuator.press(*names)
            down = True
            LOG.info('Pad act: %s held on %s', skill_name(skill), record_label(self.record(skill)))
            yield again
        finally:
            release()
            self.actuator.neutral()

    def steer(self, kind: int, unit: int, here: Point, there: Point, what: str = '') -> bool:
        """Under the held strike: whether the target names the unit; if not, nudge toward it (at most every
        STEER_EVERY)."""
        now, held = self.run.clock(), self.target()
        if held == (kind, unit):
            if self.steered.get(unit, 0.0) is None:
                LOG.info('Pad target: the strike holds %s', what or f'unit {unit}')
            self.steered[unit] = now
            return True
        if unit not in self.steered:
            self.steered[unit] = None
            LOG.info(
                'Pad target: the strike wants %s at %.0f degrees, %.1f away; the client holds %s: nudged',
                what or f'unit {unit}', heading_degrees((there[0] - here[0], there[1] - here[1])),
                math.dist(here, there), held,
            )  # fmt: skip
        if now - self.nudged_at >= STEER_EVERY:
            self.nudge((there[0] - here[0], there[1] - here[1]))
        return False

    # Moves.

    def walk(
        self,
        to: Point,
        *,
        near: float = WALK_NEAR,
        limit: float | None = None,
        done: Callable[[World], bool] | None = None,
        why: str = '',
    ) -> bool:
        """Hold the left stick toward `to` until `near`, `done`, a STALL_SECONDS stall or `limit`; whether it got
        there (or `done`). The stick is always centred after (centring sends the client's stop)."""
        run = self.run
        world = run.world()
        player = world.player
        if player is None:
            raise Abort('not in a game')
        start = (player.x, player.y)
        away = math.dist(start, to)
        if away <= near or (done is not None and done(world)):
            return True
        limit = WALK_LATENCY + 1.5 * away / RUN_SPEED + 0.5 if limit is None else limit
        began = run.clock()
        best, best_at = away, began
        sent: Point | None = None
        first: tuple[Point, Point] | None = None  # (heading, stick) of the first push
        measured, arrived, ended = False, False, 'the time ran out'
        here = start
        try:
            while True:
                if done is not None and done(world):
                    arrived, ended = True, 'done'
                    break
                if world.player is None:
                    ended = 'not in a game'
                    break
                here = (world.player.x, world.player.y)
                left = math.dist(here, to)
                if left <= near:
                    arrived, ended = True, 'there'
                    break
                now = run.clock()
                if left < best - 0.5:
                    best, best_at = left, now
                elif now - best_at >= STALL_SECONDS:
                    ended = 'no nearer'
                    break
                if now - began >= limit:
                    break
                if first is not None and not measured and math.dist(here, start) >= MEASURE_UNITS:
                    measured = True
                    self.measure_walk(start, here, first, now - began, why)
                heading = (to[0] - here[0], to[1] - here[1])
                stick = stick_for(heading, WALK_STICK)
                # The first push is kept until measured, then re-aimed at each look.
                turn = 0.0 if sent is None else abs(turned(heading_degrees(stick), heading_degrees(sent)))
                if sent is None or (measured and turn > math.degrees(WALK_TURN)):
                    self.actuator.stick(*stick)
                    sent = stick
                    if first is None:
                        first = (heading, stick)
                else:
                    self.actuator.guard()
                run.pace.sleep(WALK_POLL)
                world = run.world()
        finally:
            self.actuator.stick(0.0, 0.0)
        if first is not None:
            self.astray = None  # the leg owed after an astray jump is walked
        if first is not None and not measured:
            moved = math.dist(here, start)
            LOG.info(
                'Pad walk: toward %.0f degrees (stick %+.2f, %+.2f)%s: %.1f units in %.2fs, %s',
                heading_degrees(first[0]), *first[1], f' for {why}' if why else '', moved, run.clock() - began,
                f'at {heading_degrees((here[0] - start[0], here[1] - start[1])):.0f} degrees' if moved else 'no move',
            )  # fmt: skip
        LOG.info(
            'Pad act: walk%s from (%.1f, %.1f) toward (%.1f, %.1f): %s at (%.1f, %.1f), %.1f left, %.2fs',
            f' for {why}' if why else '', *start, *to, ended, *here, math.dist(here, to), run.clock() - began,
        )  # fmt: skip
        return arrived

    def measure_walk(self, start: Point, here: Point, first: tuple[Point, Point], seconds: float, why: str) -> None:
        went = (here[0] - start[0], here[1] - start[1])
        heading, stick = first
        LOG.info(
            'Pad walk: stick %+.2f, %+.2f for a heading of %.0f degrees%s; the character went %.0f degrees, off '
            '%+.0f degrees (%.1f units in %.2fs)',
            *stick, heading_degrees(heading), f' ({why})' if why else '', heading_degrees(went),
            turned(heading_degrees(went), heading_degrees(heading)), math.hypot(*went), seconds,
        )  # fmt: skip

    # Objects and items.

    def interact(self, kind: int, unit: int, at: Point, done: Callable[[], bool], what: str) -> bool:
        """Use an object or door: stand by it, target it, press Attack (`allowInteractOnDefaultAttack`), wait for
        `done`; whether it was used."""
        self.walk(at, near=INTERACT_STAND, why=what)
        player = self.run.world().player
        if player is None:
            raise Abort('not in a game')
        here = (player.x, player.y)
        if math.dist(here, at) > INTERACT_REACH:
            LOG.info('Pad act: %s is %.1f away after the walk: not used', what, math.dist(here, at))
            return False
        if not self.aim_unit(kind, unit, here, at, what):
            return False
        began = self.run.clock()
        self.cast(ATTACK)
        while self.run.clock() - began < INTERACT_SECONDS:
            self.run.world()  # a cancel stops here
            if done():
                LOG.info('Pad act: %s used %.2fs after the press', what, self.run.clock() - began)
                return True
            self.run.pace.sleep(WALK_POLL)
        LOG.info('Pad act: %s not used %.1fs after the press', what, INTERACT_SECONDS)
        return False

    def pick_up(self, unit: int, at: Point, gone: Callable[[], bool], what: str, others: Sequence[Point] = ()) -> bool:
        """Pick an item up: stand on it so it is the nearest (Loot takes the nearest, whatever the filter shows),
        press Loot (else Loot to Cube), and see it leave the ground. Another item targeted: nothing is pressed."""
        self.walk(at, near=PICK_STAND, done=lambda world: gone(), why=what)
        if gone():
            LOG.info('Pad pick: %s taken on the walk to it', what)
            return True
        player = self.run.world().player
        if player is None:
            raise Abort('not in a game')
        here = (player.x, player.y)
        away = math.dist(here, at)
        nearer = [spot for spot in others if math.dist(here, spot) < away]
        if away > PICK_REACH or nearer:
            LOG.info(
                'Pad pick: %s %.1f away after the walk, %d other items nearer: not pressed', what, away, len(nearer)
            )
            return False
        held = self.target()
        if held is not None and held[0] == ITEM_UNIT and held[1] != unit:
            LOG.info('Pad pick: %s wanted; the client holds item %d: not pressed', what, held[1])
            return False
        found = records(self.bindings())
        skill = LOOT if LOOT in found else LOOT_TO_CUBE
        began = self.run.clock()
        self.cast(skill)
        while self.run.clock() - began < PICK_SECONDS:
            self.run.world()  # a cancel stops here
            if gone():
                LOG.info(
                    'Pad pick: %s by %s, %.1f away, %.2fs after the press (target %s)',
                    what, skill_name(skill), away, self.run.clock() - began, held,
                )  # fmt: skip
                return True
            self.run.pace.sleep(WALK_POLL)
        LOG.info(
            'Pad pick: %s still on the ground after %s, %.1f away (target %s)', what, skill_name(skill), away, held
        )
        return False
