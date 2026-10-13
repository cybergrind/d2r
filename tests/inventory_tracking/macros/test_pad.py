"""The macros' pad back end (macros/pad.py): each act in each input mode makes the right input and none that
would flip the game's mode; the guards stop on a flip; the pad is let go on every way out; the mode policy."""

import logging
import math
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock.movement import BLADE_WARP_PAD_REACH, MOVEMENT
from inventory_tracking.builds.warlock.skills import BLADE_WARP, ECHOING_STRIKE, HEX_PURGE, SUMMON_DEFILER
from inventory_tracking.input.gamepad import record_buttons
from inventory_tracking.levels.model import Level, Room, Target
from inventory_tracking.macros import pad as pad_module
from inventory_tracking.macros.actuator import Abort, Cancelled
from inventory_tracking.macros.build import PAD_SLACK, Intent, Step
from inventory_tracking.macros.drinking import EVERY, Drinker
from inventory_tracking.macros.hunt import Hunter, strike_input
from inventory_tracking.macros.movement import TELEPORT_RING, StaffTeleport
from inventory_tracking.macros.pad import (
    ITEM_UNIT,
    LOOT_TO_CUBE,
    MONSTER_UNIT,
    OBJECT_UNIT,
    PadActs,
    PadActuator,
    PadPlay,
    input_policy,
    pad_slots,
    records,
    stick_for,
)
from inventory_tracking.macros.routines import leave_game, press_skill
from inventory_tracking.macros.runner import PICKUP, PREBUFF, MacroRunner
from inventory_tracking.macros.skills import ATTACK, SWAP_WEAPONS, TELEPORT
from inventory_tracking.macros.teleport import landing, scaled, way_for
from inventory_tracking.macros.travel import JUMP_LEAST, JUMP_REACH, Travel, step_walk, stride_of
from inventory_tracking.macros.view import Viewport
from inventory_tracking.macros.world import Drop, Loot, Monster, Thing
from inventory_tracking.models import InputMode, PotionType
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.tracking.input_mode import ControllerState
from tests.inventory_tracking.macros.fakes import SLOTS, WINDOW, Game, warlock, world
from tests.inventory_tracking.macros.moves import ASPECT, facts


# The table `make serve` writes (config gamepad_bindings) over the class's defaults: records 0-11, the rest empty.
BINDINGS = (0, LOOT_TO_CUBE, 395, ECHOING_STRIKE, BLADE_WARP, TELEPORT, 387, 359, HEX_PURGE, 375, 393, 381, *(-1,) * 20)
CONTROLLER, KEYBOARD = InputMode(True), InputMode(False)
SWITCHING = InputMode(True, True, False)
RECORD = {record_buttons(record): record for record in range(12)}


class FakePad:
    """The device as `Pad` drives it: every input recorded; a press tells the game."""

    def __init__(self, pressed=lambda names: None) -> None:
        self.events: list[tuple] = []
        self.down: set[str] = set()
        self.left = (0.0, 0.0)
        self.pressed = pressed

    def press(self, *names: str) -> None:
        self.events.append(('press', names))
        self.down |= set(names)
        self.pressed(names)

    def release(self, *names: str) -> None:
        self.events.append(('release', names))
        self.down -= set(names)

    def stick(self, side: str, x: float, y: float) -> None:
        self.events.append(('stick', side, round(x, 2), round(y, 2)))
        if side == 'left':
            self.left = (x, y)

    def neutral(self) -> None:
        self.events.append(('neutral',))
        self.down.clear()
        self.left = (0.0, 0.0)

    def presses(self) -> list[tuple[str, ...]]:
        return [event[1] for event in self.events if event[0] == 'press']


def world_of(stick: tuple[float, float], mirror: bool = False) -> tuple[float, float]:
    """The world direction the client makes of a stick (the inverse of `stick_for`); `mirror` flips the stick's y,
    as a uinput axis the other way round would."""
    across, down = stick[0], -stick[1] if mirror else stick[1]
    dx, dy = (across + down) / 2, (down - across) / 2
    length = math.hypot(dx, dy)
    return (dx / length, dy / length) if length else (0.0, 0.0)


class Controller:
    """The fakes' game (fakes.Game) in controller mode, played by a fake pad: the left stick walks the
    character, a jump's record puts it its reach along the stick, other records do what `effects` says."""

    SPEED = 9.0  # units a second

    def __init__(self, start=None, bindings=BINDINGS, mirror: bool = False) -> None:
        self.game = Game(start or world(slots=SLOTS))
        self.mode = CONTROLLER
        self.target: tuple[int, int] | None = None
        self.timed: list[tuple[float, tuple[int, int]]] = []  # (clock time, target): the client's pick changing
        self.bindings = bindings
        self.mirror = mirror
        self.pad = FakePad(self.pressed)
        self.effects: dict[int, object] = {}
        self.read_at: float | None = None
        self.casts: list[tuple[int, tuple[float, float]]] = []  # (skill, the stick) per press of a record
        self.strikes: list[tuple[int, int] | None] = []  # the client's target at each strike
        self.auto = False  # the client targets the nearest monster by itself (its auto-target, roughly)

    def player_to(self, x: float, y: float) -> None:
        w = self.game.world
        self.game.world = replace(w, player=replace(w.player, x=x, y=y))

    def read(self):
        now, p = self.game.clock.now, self.game.world.player
        if self.read_at is not None and self.pad.left != (0.0, 0.0) and p is not None:
            way, push = world_of(self.pad.left, self.mirror), min(1.0, math.hypot(*self.pad.left))
            step = self.SPEED * push * (now - self.read_at)
            self.player_to(p.x + way[0] * step, p.y + way[1] * step)
        self.read_at = now
        self.game.read()
        if 'y' in self.pad.down and 'lt' not in self.pad.down and self.game.acting_until is None:
            self.strike()  # the strike's record held: the client casts it again and again at its target
        return self.game.world

    def strike(self) -> None:
        """Echoing Strike at the client's own target: a kill, and the cast's animation."""
        w, held = self.game.world, self.state().target
        self.strikes.append(held)
        hit = next((m for m in w.monsters if (MONSTER_UNIT, m.unit_id) == held), None)
        monsters, dead = w.monsters, w.dead
        if hit is not None:
            monsters, dead = tuple(m for m in monsters if m is not hit), dead | {hit.unit_id}
        self.game.world = replace(w, monsters=monsters, dead=dead, player=replace(w.player, mode=7))
        self.game.acting_until = self.game.clock.now + 0.3

    def pressed(self, names: tuple[str, ...]) -> None:
        record = RECORD.get(names)
        if record is None:
            return
        skill = self.bindings[record]
        self.casts.append((skill, self.pad.left))
        reach = {TELEPORT: pad_module.TELEPORT_REACH, BLADE_WARP: BLADE_WARP_PAD_REACH}.get(skill)
        p = self.game.world.player
        if reach is not None and self.pad.left != (0.0, 0.0):
            way = world_of(self.pad.left, self.mirror)
            self.player_to(p.x + way[0] * reach, p.y + way[1] * reach)
        effect = self.effects.get(skill)
        if effect is not None:
            effect()

    def state(self) -> ControllerState:
        """The client's controller state, read on its own (InputModeWatch's thread), whatever the run reads."""
        while self.timed and self.game.clock.now >= self.timed[0][0]:
            self.target = self.timed.pop(0)[1]
        w = self.game.world
        if self.auto and w.player is not None:
            here = (w.player.x, w.player.y)
            near = [m for m in w.monsters if not m.ally and math.dist(here, (m.x, m.y)) <= 20]
            self.target = (MONSTER_UNIT, min(near, key=lambda m: math.dist(here, (m.x, m.y))).unit_id) if near else None
        return ControllerState(self.target, -1, -1)

    def run(self):
        run = self.game.run()
        run.read = self.read
        acts = PadActs(
            run,
            PadActuator(lambda: self.pad, lambda: self.mode, run.actuator),
            self.state,
            lambda: self.bindings,
        )
        run.pad = acts
        run.hovered = acts.target
        run.keys = acts.keys((ECHOING_STRIKE, BLADE_WARP, TELEPORT, HEX_PURGE, 375), lambda: b'')
        run.keys[SWAP_WEAPONS] = 'c'
        return run


def no_mouse(game: Game) -> bool:
    """Nothing the macro sent would flip the game out of controller mode: no mouse button."""
    return not any(event[0] in ('click', 'button') for event in game.keys.events)


# The geometry and the tables.


def test_a_world_heading_is_the_stick_turned_45_degrees():
    assert stick_for((1.0, -1.0)) == pytest.approx((1.0, 0.0))  # world +x -y: right on the screen
    assert stick_for((-1.0, -1.0)) == pytest.approx((0.0, -1.0))  # up
    assert stick_for((1.0, 1.0)) == pytest.approx((0.0, 1.0))  # down
    assert stick_for((1.0, 0.0), 0.5) == pytest.approx((0.5 / math.sqrt(2), 0.5 / math.sqrt(2)))
    assert stick_for((0.0, 0.0)) == (0.0, 0.0)
    assert world_of(stick_for((3.0, 4.0))) == pytest.approx((0.6, 0.8))


def test_records_give_each_skill_its_first_record_and_teleport_only_with_it_on_a_key():
    found = records(BINDINGS)
    assert found[ECHOING_STRIKE] == 3
    assert found[HEX_PURGE] == 8
    assert found[0] == 0
    assert SUMMON_DEFILER not in found
    assert records(None) == {}
    assert TELEPORT in pad_slots(BINDINGS, (TELEPORT, None))
    assert TELEPORT not in pad_slots(BINDINGS, (None, 390))  # no staff, no Enigma: the record casts nothing
    assert BLADE_WARP in pad_slots(BINDINGS, ())


def test_the_records_labels_stand_for_keys_and_a_skill_on_none_is_refused():
    run = Controller().run()
    assert run.pad.keys((ECHOING_STRIKE, HEX_PURGE), lambda: b'') == {ECHOING_STRIKE: 'Y', HEX_PURGE: 'LT+B'}
    with pytest.raises(Abort, match='Summon Defiler is on no pad record'):
        run.pad.keys((SUMMON_DEFILER,), lambda: b'')


def test_in_controller_mode_the_world_has_the_records_skills_for_slots():
    run = Controller().run()
    slots = run.world().slots
    assert ECHOING_STRIKE in slots
    assert BLADE_WARP in slots
    assert TELEPORT in slots
    assert SUMMON_DEFILER not in slots  # on a key, on no record: not castable here (Consume's dance is off)


# The mode policy.


def test_the_policy_follows_the_games_mode_and_never_flips_it():
    assert input_policy(None, enabled=True) is False  # unread: the keys, as before
    assert input_policy(KEYBOARD, enabled=True, needs_mouse='the macro request') is False
    assert input_policy(CONTROLLER, enabled=True) is True
    with pytest.raises(Abort, match='switching to keyboard'):
        input_policy(SWITCHING, enabled=True)
    with pytest.raises(Abort, match='controller_play'):
        input_policy(CONTROLLER, enabled=False)
    with pytest.raises(Abort, match='the macro request needs mouse mode: click once'):
        input_policy(CONTROLLER, enabled=True, needs_mouse='the macro request')


def runner_run(mode: InputMode | None, enabled: bool = True):
    runner = MacroRunner(None, capture_lock=None, saved_games=None)  # type: ignore[arg-type]
    device = FakePad()
    runner.pad_play = PadPlay(lambda: device, lambda: mode, lambda: None, lambda: BINDINGS, enabled)
    game = Game(world(slots=SLOTS))
    return runner, game.run()


def test_the_runner_plays_a_step_by_the_pad_in_controller_mode_and_refuses_the_macro_request():
    runner, run = runner_run(CONTROLLER)
    runner.play_by(run, run.actuator, PICKUP)
    assert run.pad is not None
    assert run.hovered == run.pad.target
    assert run.actuator.mode is not None
    assert not run.actuator.keyboard_run
    runner, run = runner_run(CONTROLLER)
    with pytest.raises(Abort, match='needs mouse mode'):
        runner.play_by(run, run.actuator, PREBUFF)
    assert run.pad is None


def test_the_runner_plays_by_the_keys_in_keyboard_mode_and_without_a_pad_play():
    runner, run = runner_run(KEYBOARD)
    runner.play_by(run, run.actuator, PICKUP)
    assert run.pad is None
    assert run.actuator.keyboard_run
    runner = MacroRunner(None, capture_lock=None, saved_games=None)  # type: ignore[arg-type]
    run = Game(world(slots=SLOTS)).run()
    runner.play_by(run, run.actuator, PICKUP)
    assert run.pad is None
    assert run.actuator.mode is None
    assert not run.actuator.keyboard_run


# The guards.


def test_the_pad_presses_nothing_while_a_flip_is_pending_or_in_keyboard_mode():
    play = Controller()
    run = play.run()
    for mode, said in ((SWITCHING, 'switching'), (KEYBOARD, 'keyboard mode now'), (None, 'cannot be read')):
        play.mode = mode
        with pytest.raises(Abort, match=said):
            press_skill(run, HEX_PURGE)
    assert play.pad.presses() == []


def test_the_pad_stops_for_a_key_or_a_mouse_button_of_the_players_and_a_cancel():
    play = Controller()
    run = play.run()
    play.game.keys.held = True
    with pytest.raises(Abort, match='a key was pressed'):
        run.pad.actuator.tap(3)
    play.game.keys.held = False
    play.game.keys.pointer_state = lambda: (0, 0, 1 << 8)  # the left button down
    with pytest.raises(Abort, match='a mouse button'):
        run.pad.actuator.tap(3)
    play.game.keys.pointer_state = lambda: (0, 0, 0)
    run.actuator.cancelled = run.cancelled
    run.cancelled.set()
    with pytest.raises(Cancelled):
        run.pad.actuator.tap(3)
    assert play.pad.presses() == []


def test_the_keys_press_no_mouse_button_in_controller_mode_but_keys_go():
    game = Game(world(slots=SLOTS))
    run = game.run()
    mode = [CONTROLLER]
    run.actuator.mode = lambda: mode[0]
    with pytest.raises(Abort, match='a click would switch it back'):
        run.actuator.click()
    with pytest.raises(Abort, match='a click would switch it back'), run.actuator.hold('Button3'):
        pass
    run.actuator.tap('Escape')  # a keyboard key flips nothing
    assert no_mouse(game)
    assert game.pressed() == ['Escape']
    mode[0] = KEYBOARD
    run.actuator.click()
    assert not no_mouse(game)


def test_a_run_by_the_keys_stops_when_the_game_leaves_keyboard_mode():
    game = Game(world(slots=SLOTS))
    run = game.run()
    mode = [KEYBOARD]
    run.actuator.mode, run.actuator.keyboard_run = (lambda: mode[0]), True
    run.actuator.tap('Escape')
    mode[0] = SWITCHING  # the player's pad touched
    with pytest.raises(Abort, match='left keyboard mode'):
        run.actuator.tap('Escape')


def test_keyboard_mode_is_as_before_no_pad_and_the_same_keys():
    game = Game(world(slots=SLOTS))
    run = game.run()
    run.actuator.mode = lambda: KEYBOARD
    press_skill(run, HEX_PURGE)
    assert game.pressed() == ['g']
    assert run.pad is None


# The acts.


def test_a_cast_on_the_character_is_its_record_with_lt_and_no_mouse_and_no_key():
    play = Controller()
    run = play.run()
    press_skill(run, HEX_PURGE)
    assert play.pad.presses() == [('lt', 'b')]
    assert play.pad.down == set()
    assert no_mouse(play.game)
    assert play.game.pressed() == []


def test_a_cast_toward_a_place_pushes_the_stick_that_way_presses_and_centres(caplog):
    play = Controller()
    run = play.run()
    here = (5000.0, 5000.0)
    run.pad.aim_place(here, (5017.0, 5000.0))  # world +x: down and right on the screen
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        press_skill(run, BLADE_WARP)
        run.world()
        play.game.clock.now += 0.1
        run.world()
    first, last = play.pad.events[0], play.pad.events[-1]
    assert first[0] == 'stick'
    assert first[2] > 0
    assert first[3] > 0
    assert first[2] == pytest.approx(first[3])
    assert ('press', ('rb',)) in play.pad.events
    assert last == ('stick', 'left', 0.0, 0.0)
    assert play.casts[0][0] == BLADE_WARP
    assert 'Pad jump: Blade Warp toward 0 degrees, reach 17' in caplog.text
    assert 'off +0 degrees and +0.0 units' in caplog.text
    assert no_mouse(play.game)


def test_a_mirrored_stick_shows_in_the_jumps_log_line(caplog):
    play = Controller(mirror=True)
    run = play.run()
    run.pad.aim_place((5000.0, 5000.0), (5023.0, 5000.0))
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        press_skill(run, TELEPORT)
        run.world()
        play.game.clock.now += 0.1
        run.world()
    assert 'Pad jump: Teleport toward 0 degrees, reach 23' in caplog.text
    assert 'off -90 degrees' in caplog.text or 'off +90 degrees' in caplog.text


def test_a_cast_on_a_unit_waits_for_the_controllers_target_to_name_it(caplog):
    play = Controller()
    run = play.run()
    play.timed.append((0.08, (MONSTER_UNIT, 42)))
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        assert run.pad.aim_unit(MONSTER_UNIT, 42, (5000.0, 5000.0), (5010.0, 5000.0), 'the monster 42')
    assert 'Pad target: the monster 42 named' in caplog.text
    sticks = [event for event in play.pad.events if event[0] == 'stick']
    assert sticks[0][2:] == pytest.approx(stick_for((1.0, 0.0), pad_module.FACE_STICK), abs=0.01)
    assert sticks[-1] == ('stick', 'left', 0.0, 0.0)  # the nudge is let go
    press_skill(run, 375)  # Death Mark: LT+Y
    assert play.pad.presses() == [('lt', 'y')]


def test_a_cast_on_a_unit_the_target_does_not_name_is_not_made(caplog):
    play = Controller()
    run = play.run()
    play.target = (MONSTER_UNIT, 7)
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        assert not run.pad.aim_unit(MONSTER_UNIT, 42, (5000.0, 5000.0), (5010.0, 5000.0), 'the monster 42')
    assert 'the client holds (1, 7)' in caplog.text
    assert 'not cast' in caplog.text
    assert play.pad.presses() == []


def test_the_target_already_named_needs_no_nudge():
    play = Controller()
    run = play.run()
    play.target = (MONSTER_UNIT, 42)
    assert run.pad.aim_unit(MONSTER_UNIT, 42, (5000.0, 5000.0), (5010.0, 5000.0))
    assert play.pad.events == []


def test_the_held_strike_is_its_record_held_and_let_go_and_centred_on_any_way_out():
    play = Controller()
    run = play.run()
    seen = []

    def fight() -> None:
        with run.pad.hold(ECHOING_STRIKE) as again:
            seen.append(set(play.pad.down))
            again()
            seen.append(play.pad.presses())
            again.release()  # type: ignore[attr-defined]
            seen.append(set(play.pad.down))
            again()
            raise RuntimeError('the fight broke off')

    with pytest.raises(RuntimeError):
        fight()
    assert seen == [{'y'}, [('y',), ('y',)], set()]
    assert play.pad.down == set()
    assert play.pad.events[-1] == ('neutral',)


def test_the_strike_input_in_controller_mode_is_the_record():
    play = Controller()
    run = play.run()
    held, how = strike_input(run, run.world(), lambda world, skills: run.pad.keys(skills, lambda: b''), ECHOING_STRIKE)
    assert held == ()
    assert how == 'pad Y'


def test_steering_nudges_toward_the_prey_until_the_target_names_it(caplog):
    play = Controller()
    run = play.run()
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        assert not run.pad.steer(MONSTER_UNIT, 42, (5000.0, 5000.0), (5000.0, 5010.0), 'the monster 42')
        nudges = len([e for e in play.pad.events if e[0] == 'stick'])
        assert not run.pad.steer(MONSTER_UNIT, 42, (5000.0, 5000.0), (5000.0, 5010.0))  # too soon for another
        assert len([e for e in play.pad.events if e[0] == 'stick']) == nudges
        play.target = (MONSTER_UNIT, 42)
        assert run.pad.steer(MONSTER_UNIT, 42, (5000.0, 5000.0), (5000.0, 5010.0), 'the monster 42')
    assert 'the strike wants the monster 42' in caplog.text
    assert 'the strike holds the monster 42' in caplog.text


def test_a_walk_holds_the_stick_toward_the_place_and_centres_it_and_measures_the_heading(caplog):
    play = Controller()
    run = play.run()
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        assert run.pad.walk((5012.0, 5000.0), why='a better place')
    p = play.game.world.player
    assert math.dist((p.x, p.y), (5012.0, 5000.0)) <= pad_module.WALK_NEAR
    assert play.pad.events[-1] == ('stick', 'left', 0.0, 0.0)
    assert play.pad.left == (0.0, 0.0)
    assert 'Pad walk: stick +0.71, +0.71 for a heading of 0 degrees (a better place); the character went 0 degrees' in (
        caplog.text
    )
    assert no_mouse(play.game)


def test_a_mirrored_stick_shows_in_the_walks_log_line(caplog):
    play = Controller(mirror=True)
    run = play.run()
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        run.pad.walk((5012.0, 5000.0), limit=1.0)
    assert 'Pad walk: stick +0.71, +0.71 for a heading of 0 degrees; the character went -90 degrees, off -90' in (
        caplog.text
    )
    assert play.pad.events[-1] == ('stick', 'left', 0.0, 0.0)


def test_a_walk_that_breaks_off_still_centres_the_stick():
    play = Controller()
    run = play.run()
    play.game.arrivals.append((0.2, lambda: setattr(play, 'mode', SWITCHING)))
    with pytest.raises(Abort, match='switching'):
        run.pad.walk((5030.0, 5000.0))
    assert play.pad.events[-1] == ('stick', 'left', 0.0, 0.0)


def test_a_walk_step_of_the_mode_is_the_stick_and_no_click():
    play = Controller()
    run = play.run()
    p = play.game.world.player
    step_walk(run, (5010.0, 5004.0), p, WINDOW[2] / WINDOW[3], [])
    assert no_mouse(play.game)
    assert play.pad.left == (0.0, 0.0)
    assert math.dist((play.game.world.player.x, play.game.world.player.y), (5010.0, 5004.0)) <= 1.5


def test_a_jump_of_the_movement_is_a_heading_and_lands_at_its_reach():
    play = Controller()
    run = play.run()
    travel = Travel(MOVEMENT)
    p = play.game.world.player
    travel.jump(run, Step((5016.0, 5000.0), BLADE_WARP), p, WINDOW[2] / WINDOW[3], lambda w, s: run.pad.keys(s, bytes))
    after = play.game.world.player
    assert math.dist((after.x, after.y), (5017.0, 5000.0)) < 0.1
    assert ('press', ('rb',)) in play.pad.events
    assert no_mouse(play.game)


def test_pickup_stands_on_the_item_and_presses_the_loot_record(caplog):
    play = Controller()
    run = play.run()
    ring = Drop(9, 5006.0, 5003.0, 'Ring', 'valuable')
    play.game.loot = Loot((ring,))

    def take() -> None:
        here = play.game.world.player
        if math.dist((here.x, here.y), (ring.x, ring.y)) <= 4:
            play.game.loot = Loot(())

    play.effects[LOOT_TO_CUBE] = take
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        assert run.pad.pick_up(9, (ring.x, ring.y), lambda: not play.game.loot.drops, 'Ring')
    assert ('press', ('x',)) in play.pad.events  # Loot to Cube on X: Loot is on no record
    assert 'Pad pick: Ring by Loot to Cube' in caplog.text
    assert no_mouse(play.game)


def test_pickup_presses_nothing_while_the_target_names_another_item(caplog):
    play = Controller()
    run = play.run()
    play.target = (ITEM_UNIT, 77)
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        assert not run.pad.pick_up(9, (5003.0, 5000.0), lambda: False, 'Ring')
    assert 'the client holds item 77: not pressed' in caplog.text
    assert play.pad.presses() == []


def test_a_chest_is_opened_by_a_once_the_target_names_it():
    play = Controller()
    run = play.run()
    chest = Thing(31, 5, 0, 5008.0, 5000.0)
    opened = []
    play.target = (OBJECT_UNIT, 31)
    play.effects[ATTACK] = lambda: opened.append(True)
    assert run.pad.interact(OBJECT_UNIT, 31, (chest.x, chest.y), lambda: bool(opened), 'a chest')
    assert play.pad.presses() == [('a',)]
    assert no_mouse(play.game)


def test_save_and_exit_is_refused_in_controller_mode():
    play = Controller()
    run = play.run()
    with pytest.raises(Abort, match='needs mouse mode'):
        leave_game(run)
    assert play.pad.presses() == []
    assert play.game.pressed() == []


def test_the_swap_is_the_keyboard_key_and_its_outcome_is_said(caplog):
    play = Controller()
    run = play.run()
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        press_skill(run, SWAP_WEAPONS)
    assert play.game.pressed() == ['c']
    assert play.pad.presses() == []
    assert 'Pad swap: key c pressed in controller mode' in caplog.text


def test_a_belt_key_in_controller_mode_says_whether_the_cell_emptied(caplog):
    play = Controller(world(area=101, slots=SLOTS))
    play.game.loot = Loot((), (606, 606, 531, 531) * 4, 1000, 1000)
    run, drinker = play.run(), Drinker()
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        for life in (1000, 850, 850, 850):
            play.game.loot = replace(play.game.loot, life=life)
            drinker.look(run, (5000.0, 5000.0))
            play.game.clock.now += EVERY
    assert play.game.pressed() == ['1']
    assert play.pad.presses() == []
    assert 'Pad drink: Healing potion on 1 in controller mode: the belt cell emptied' in caplog.text
    assert drinker.drunk_at[PotionType.HEALING] is not None


# Navigation gets the landing it plans.


def test_in_controller_mode_a_jump_is_of_one_length_and_one_without_a_fixed_reach_is_not_made():
    walk = MOVEMENT[-1]  # the Warlock's walk: Blade Warp first
    found = walk.jumps(facts(slots=(BLADE_WARP,), pad=True), Intent('test', 0, False, False, 1.0))
    assert [(jump.skill, jump.least, jump.reach) for jump in found] == [
        (BLADE_WARP, BLADE_WARP_PAD_REACH - PAD_SLACK, BLADE_WARP_PAD_REACH + PAD_SLACK)
    ]
    keyed = walk.jumps(facts(slots=(BLADE_WARP,)), Intent('test', 0, False, False, 1.0))
    assert [(jump.least, jump.reach) for jump in keyed] == [(JUMP_LEAST, JUMP_REACH)]  # keyboard: as before
    staff = StaffTeleport()
    no_reach = replace(staff, sources=(replace(staff.sources[0], pad_reach=None),))
    assert no_reach.jumps(facts(slots=(TELEPORT,), pad=True), Intent('test', 0, False, False, 1.0)) == ()


def test_a_stride_in_controller_mode_lands_within_the_slack_of_the_reach():
    jumps = (MOVEMENT[-1].sources[0].pad_jump(),)
    here = (5000.5, 5000.5)
    found = stride_of(facts(slots=(BLADE_WARP,), pad=True), (5040.5, 5000.5), jumps=jumps)
    assert isinstance(found, Step)
    assert found.skill == BLADE_WARP
    assert abs(math.dist(here, found.spot) - BLADE_WARP_PAD_REACH) <= PAD_SLACK
    near = stride_of(facts(slots=(BLADE_WARP,), pad=True), (5010.5, 5000.5), jumps=jumps)
    assert isinstance(near, Step)
    assert near.skill is None  # nearer than the blade's one length: walked


def test_a_hop_in_controller_mode_lands_only_on_its_ring():
    # A corridor east of the character (as test_teleport's), the mark at its far end.
    rooms = (Room(1, 996, 996, 8, 8), *(Room(2 + i, 1004 + 8 * i, 996, 8, 8) for i in range(4)))
    target = Target(109, rooms, (1030.5, 1000.5), 'Next level', 'stairs', False)
    player = replace(world().player, x=1000.0 * TILE_UNITS, y=1000.0 * TILE_UNITS)
    way = way_for(target, Viewport(ASPECT))
    free = landing(target, player, way, ASPECT)
    found = landing(target, player, way, ASPECT, TELEPORT_RING)
    assert free is not None
    assert found is not None
    away = math.dist(scaled(found[0]), (player.x, player.y))
    assert TELEPORT_RING[0] <= away <= TELEPORT_RING[1]
    assert not TELEPORT_RING[0] <= math.dist(scaled(free[0]), (player.x, player.y)) <= TELEPORT_RING[1]


def pad_names(run):
    """The runner's `key_names` in controller mode (runner.py), with Swap Weapons on `c` as the fakes have it."""

    def names(_world, skills):
        found = run.pad.keys([skill for skill in skills if skill != SWAP_WEAPONS], lambda: b'')
        return found | ({SWAP_WEAPONS: 'c'} if SWAP_WEAPONS in skills else {})

    return names


def test_attack_mode_in_controller_mode_holds_the_strike_on_its_record_at_the_clients_target():
    start = world(monsters=(Monster(10, 19, 1, 5008.0, 5000.0, 0xFFFFFFFF, 0, life=90, max_life=90),), area=101)
    play = Controller(replace(start, player=replace(start.player, consume=True)))
    play.auto = True
    run = play.run()
    hunt = Hunter(lambda: Level(101, (), ()), lambda area: [], None, build=warlock(play.game.world))
    play.game.arrivals.append((5.0, run.cancelled.set))
    with pytest.raises(Abort, match='cancelled'):
        hunt.attack_mode(run, pad_names(run))
    assert play.strikes[0] == (MONSTER_UNIT, 10)
    assert 10 in play.game.world.dead
    assert ('y',) in play.pad.presses()
    assert no_mouse(play.game)
    assert play.game.pressed() == []  # no skill key: the records cast
    assert play.pad.down == set()
