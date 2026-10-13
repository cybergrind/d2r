"""The macros' pad back end: the acts of a run made with the virtual pad while the game is in controller mode.

rca/2026-10-13/controller-mode.md (plan step 9). A run plays in one input mode, the game's at its start
(`input_policy`, asked by runner.py); a flip during the run stops it at the next act, as a key of the player's
does. Keyboard mode is the keyboard back end: the code of every routine as it was. In controller mode the
routines ask `Run.pad` (a `PadActs`) at the few places where they would move the pointer, click or tap a skill
key, and nowhere else:

- a cast: `aim_unit` (the client picks its own target, +0xD10: the character is turned toward the unit and the
  target must name it, else nothing is cast) or `aim_place` (a heading: a ground cast lands at its skill's own
  distance in the stick's direction), then `cast` (the record's button, LT with it for records 6-11);
- the held strike: `hold`, steered by `steer`;
- a walk: `walk` (the left stick held toward the place, aimed again at every look, centred in every `finally`);
- an object or a door: `interact` (stand by it, the target names it, A); an item: `pick_up` (stand on it, so it
  is the nearest, the Loot record: Loot, else Loot to Cube);
- what the run may cast: `slots` (the skills on the pad's records stand for the skills on keys), `keys` (the
  record's label per skill, as skills.py `skill_keys` gives the key).

No act makes a mouse button or a movement key (either flips the client back to mouse mode), and the pad is
only pressed while the mode byte reads controller with no flip pending (`PadActuator.guard`). Belt keys and the
weapon swap key are keyboard keys, which flip nothing (gamepad-proton.md §5); whether they act in controller mode
is measured (`Pad drink:`, `Pad swap:`).

What a log of the next game in controller mode answers (one line each, stable prefixes):

- `Pad target:` how long the controller's target took to name the unit a cast was meant for, or what it held
  instead after TARGET_WAIT (the auto-target's rule and its settling time);
- `Pad walk:` the world heading the stick was given against the way the character went over its first
  MEASURE_UNITS (the stick's sign and its turn into the world: STICK_TURN, STICK_SQUASH, STICK_Y);
- `Pad jump:` where a jump (Teleport, a build's own) landed against the heading and its fixed reach (`reach`);
- `Pad drink:` whether the belt cell emptied after a belt key pressed in controller mode;
- `Pad swap:` whether the weapons changed after the swap key pressed in controller mode;
- `Pad act:` each press: the skill, its record and what it was aimed at.
"""

import math
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from inventory_tracking.combat.stance import RUN_SPEED, WALK_LATENCY
from inventory_tracking.common import LOG
from inventory_tracking.input.gamepad import Pad, record_buttons, record_label
from inventory_tracking.input.keybindings import MODIFIERS, action_keys, x11_name
from inventory_tracking.macros.actuator import Abort, Actuator, Cancelled
from inventory_tracking.macros.skills import ACTIONS, ATTACK, SWAP_WEAPONS, TELEPORT, register_names, skill_name
from inventory_tracking.models import InputMode


if TYPE_CHECKING:
    from inventory_tracking.macros.engine import Run
    from inventory_tracking.macros.world import World
    from inventory_tracking.tracking.input_mode import ControllerState


Point = tuple[float, float]

# The controller's own pickup skills (skills.txt; controllerskillsettings.json: the nearest item within 4 units).
LOOT, LOOT_TO_CUBE = 358, 370
register_names({LOOT: 'Loot', LOOT_TO_CUBE: 'Loot to Cube'})
RECORDS = 12  # records 0-5 are A X B Y RB RT, 6-11 the same with LT held (input/gamepad.py)
# Unit types as the client's records name them (native units): the controller's target is (type, id).
MONSTER_UNIT, OBJECT_UNIT, ITEM_UNIT, TILE_UNIT = 1, 2, 4, 5

# World heading -> stick. The client turns the stick's vector by -45 degrees into a world direction (read:
# 0x1400d7630, the constant 0xbec90fdb), so a world heading is the stick turned by +45 degrees: world +x is down
# and right on the screen, world +y down and left (view.py). Pad.stick takes screen directions (x right, y down).
# STICK_SQUASH 1.0 is that pure turn; 0.5 would be the direction the heading is drawn in on the screen (the
# isometric view halves the height). STICK_Y -1.0 flips the stick's y, should the uinput axis come out the other
# way round in Wine. All three inferred: `Pad walk:` lines measure them (plan step 8e).
STICK_SQUASH = 1.0
STICK_Y = 1.0
WALK_STICK = 1.0  # a walk: the stick all the way (past stickRunToggleThreshold 0.8: a run, inferred)
FACE_STICK = 0.5  # a nudge that turns the character toward a unit: past the 0.4 dead zone (read)
FACE_SECONDS = 0.05  # held that long: about three of the game's frames, a turn and not a step (inferred)
AIM_STICK = 0.6  # held while the button of a cast with a heading goes down (the free target's direction)
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


def records(bindings: Sequence[int] | None) -> dict[int, int]:
    """skill -> the first of records 0-11 that holds it, from the bindings the game loaded (tracking/input_mode.py
    `read_bindings`); empty while they are not read."""
    found: dict[int, int] = {}
    for record, skill in enumerate(list(bindings or ())[:RECORDS]):
        if skill != -1:
            found.setdefault(skill, record)
    return found


def pad_slots(bindings: Sequence[int] | None, keyed: Sequence[int | None]) -> tuple[int | None, ...]:
    """What a run in controller mode can cast, in place of the skills on keys (`World.slots`): the skills of
    records 0-11. Teleport counts only when it is on a key as well: it comes from an item (a staff's charges,
    Enigma), and a record that names it casts nothing without one."""
    return tuple(
        skill
        for skill in records(bindings)
        if skill != TELEPORT or TELEPORT in keyed  # a record's skill the character may not have: Teleport only
    )


def input_policy(mode: InputMode | None, *, enabled: bool, needs_mouse: str | None = None) -> bool:
    """Whether a run plays by the pad (True) or the keys and mouse (False), the game's mode as read at its start;
    Abort with the reason when it cannot be played now. The game's mode is followed and never changed by the run:
    a flip asks for a click or a movement key (which acts in the world as well) or a pad press (which is thrown
    away by the client), takes 1-2 s by players' reports and is not measured yet (plan step 8a); flips by the
    macros are step 10. `needs_mouse`: what the routine does that only mouse mode can (panels, menus, a prebuff
    with a skill on no record), said when the game is in controller mode. Unreadable: keyboard, as before."""
    if mode is None:
        return False
    if mode.pending:
        going = 'controller' if mode.wanted else 'keyboard'
        raise Abort(f'the game is switching to {going} mode: press again after it')
    if not mode.controller:
        return False
    if not enabled:
        raise Abort('the game is in controller mode and controller play is off (config controller_play): click once')
    if needs_mouse is not None:
        raise Abort(f'{needs_mouse} needs mouse mode: click once to switch, then press again')
    return True


@dataclass(frozen=True)
class PadPlay:
    """What the service hands the runner for controller mode (appraisal/service.py): the pad, made at its first
    need and kept (input/gamepad.py `PadKeys.device`), and the input mode, the controller's state and the
    bindings the game loaded, as tracking/input_mode.py `InputModeWatch` reads them."""

    device: Callable[[], Pad | None]
    mode: Callable[[], InputMode | None]
    controller: Callable[[], ControllerState | None]
    bindings: Callable[[], Sequence[int] | None]
    enabled: bool = True  # config `controller_play`: off, a run in controller mode is refused (`input_policy`)


class PadActuator:
    """The pad behind the guard the keys have (actuator.py: the run cancelled, the focus, a key of the player's)
    and one of its own: a mouse button down, or the game anywhere but in controller mode with no flip pending,
    stops the run. A press while a flip is due is thrown away by the client, and one in keyboard mode flips it."""

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
            raise Abort('the input mode is switching')
        if not mode.controller:
            raise Abort('the game is in keyboard mode now')

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

    def stick(self, x: float, y: float) -> None:
        if (x, y) != (0.0, 0.0):
            self.guard()
        self.pad.stick('left', x, y)

    def neutral(self) -> None:
        """Everything let go and the sticks centred: a held input bars the way back to mouse mode."""
        if self.made is not None:
            try:
                self.made.neutral()
            except OSError as exc:  # the device gone: nothing is held on it any more, and the run's own end stands
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
    """The acts of one run in controller mode (the module's doc)."""

    def __init__(
        self,
        run: Run,
        actuator: PadActuator,
        controller: Callable[[], ControllerState | None],
        bindings: Callable[[], Sequence[int] | None],
    ) -> None:
        self.run = run
        self.actuator = actuator
        self.controller = controller
        self.bindings = bindings
        self.aimed: Aimed | None = None
        self.jumped: Jumped | None = None
        self.nudged_at = -math.inf
        self.steered: dict[int, float | None] = {}  # unit id -> when the strike's target first named it (None: not yet)
        self.settled: set[tuple[int, int]] = set()  # units whose settling time is logged

    # What the run can cast, and with what.

    @property
    def reach(self) -> dict[int, float]:
        """skill -> units a jump by it lands at in the stick's direction (the controller's fixed distance): the
        `pad_reach` of the jump sources of the build the run plays (macros/build.py `JumpSource`), Teleport's
        TELEPORT_REACH among them."""
        found = {TELEPORT: TELEPORT_REACH}
        for movement in self.run.build.movement:
            for source in movement.sources:
                if source.pad_reach is not None:
                    found[source.jump.skill] = source.pad_reach
        return found

    def record(self, skill: int) -> int:
        loaded = self.bindings()
        found = records(loaded).get(skill)
        if found is None:
            if not loaded:
                raise Abort('the controller bindings the game loaded are not read yet: press again in a moment')
            raise Abort(f'{skill_name(skill)} is on no pad record (controller bindings: config gamepad_bindings)')
        return found

    def slots(self, keyed: Sequence[int | None]) -> tuple[int | None, ...]:
        return pad_slots(self.bindings(), keyed)

    def keys(self, skills: Sequence[int], key_file: Callable[[], bytes]) -> dict[int, str]:
        """The label of each skill's record ('Y', 'LT+RB'), as skills.py `skill_keys` gives keys; Swap Weapons is
        its keyboard key (no record holds it). Abort names the first skill on no record."""
        found = {}
        for skill in skills:
            if skill in ACTIONS:
                codes = action_keys(key_file(), ACTIONS[skill])
                key = next((k for k in map(x11_name, codes) if k and k not in MODIFIERS), None)
                if key is None:
                    raise Abort(f'{skill_name(skill)} has no key the macro can press')
                found[skill] = key
            else:
                found[skill] = record_label(self.record(skill))
        return found

    def ring(self, skill: int) -> tuple[float, float] | None:
        """The distances a jump by `skill` may be planned to land at (its fixed reach, give or take the slack
        a JumpSource allows), or None for a skill with no fixed reach."""
        from inventory_tracking.macros.build import PAD_SLACK  # late: build.py is above this module

        reach = self.reach.get(skill)
        return None if reach is None else (reach - PAD_SLACK, reach + PAD_SLACK)

    # Each look at the game.

    def seen(self, world: World) -> World:
        """The world as a run in controller mode sees it: the skills on records stand for the skills on keys.
        A jump's landing is watched for here (`Pad jump:`)."""
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
        LOG.info(
            'Pad jump: %s toward %.0f degrees, reach %.0f (planned %.1f): landed %.1f away at %.0f degrees, off '
            '%+.0f degrees and %+.1f units, %.2fs after the press',
            skill_name(jumped.skill), heading_degrees(jumped.heading), jumped.reach, jumped.planned,
            math.hypot(*went), heading_degrees(went), turned(heading_degrees(went), heading_degrees(jumped.heading)),
            math.hypot(*went) - jumped.reach, now - jumped.at,
        )  # fmt: skip
        self.jumped = None

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
        """The next cast is for unit (`kind`, `unit`) at `there`: whether the controller's target names it now or
        within TARGET_WAIT of a nudge toward it. Not named: nothing is aimed, and the caller casts nothing (the
        client would cast at what it holds, or into the air)."""
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

    def cast(self, skill: int) -> None:
        """The skill's record pressed once, toward what `aim_unit` or `aim_place` set (nothing set: a cast on the
        character itself, the stick centred). Swap Weapons is its keyboard key."""
        aimed, self.aimed = self.aimed, None
        if skill == SWAP_WEAPONS:
            key = self.run.keys[skill]
            self.run.actuator.tap(key)  # a keyboard key: flips nothing (gamepad-proton.md §5)
            LOG.info('Pad swap: key %s pressed in controller mode', key)
            return
        record = self.record(skill)
        if aimed is not None and aimed.unit is None:
            heading = aimed.heading
            names = record_buttons(record)
            try:
                # The direction first, then the button: a free target lands along the stick (inferred).
                self.actuator.stick(*stick_for(heading, AIM_STICK))
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
                skill_name(skill), record_label(record), heading_degrees(heading), math.hypot(*heading),
            )  # fmt: skip
            return
        self.actuator.tap(record)
        LOG.info(
            'Pad act: %s on %s%s',
            skill_name(skill), record_label(record), '' if aimed is None else f' at the target {aimed.unit}',
        )  # fmt: skip

    @contextmanager
    def hold(self, skill: int) -> Iterator[Callable[[], None]]:
        """The skill's record held through the block: the client casts it again and again at its own target.
        Yields `again` (let go and pressed anew) with `again.release`, as `Actuator.hold` does."""
        names = record_buttons(self.record(skill))
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
        """Under the held strike: whether the controller's target names the unit; if not, a nudge toward it, at
        most every STEER_EVERY. The first time a unit is named or missed goes to the log (`Pad target:`)."""
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
        """The left stick held toward `to`, aimed again at each look, until the character is `near` of it, `done`
        says so, it gains nothing for STALL_SECONDS, or `limit` seconds pass; whether it got there (or `done`).
        The stick is centred in every case (centring sends the client's stop). The first MEASURE_UNITS walked go
        to the log against the heading the stick was given (`Pad walk:`)."""
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
                # The first push is kept until the walk under it is measured: then aimed again at each look.
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
        """Use an object or a door: stand by it, the controller's target names it, the Attack record (A: the
        client interacts with what it targets, `allowInteractOnDefaultAttack`), and `done` seen; whether it was."""
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
        """Pick an item up: stand on it, so that it is the nearest within PICK_REACH (the client's Loot takes the
        nearest, whatever the loot filter shows), the Loot record (Loot to Cube when Loot is on none), and the
        item seen leaving the ground. A gold pile is taken by standing on it. With another item the client's
        target names, nothing is pressed."""
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
