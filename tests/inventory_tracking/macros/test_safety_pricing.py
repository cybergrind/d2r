from dataclasses import replace

from inventory_tracking.combat.harm import Harm
from inventory_tracking.macros import pursuit as p
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.travel import PRESSED


def test_unsafe_pressed_leg_keeps_the_goal_and_fights_without_releasing():
    assert hasattr(p, 'Candidate'), 'the arbiter must price all acts, including a pressed leg'
    goal = Goal('next object', (20.0, 0.0), 'use', 5.0, PRESSED)
    move = p.Move(Step((15.0, 0.0)), goal)
    hold = p.Hold(goal)
    facts = p.Facts(
        1.0,
        goal,
        False,
        True,
        True,
        lambda: move.step,
        candidates=(p.Candidate(move, 1.0, Harm(400, 800)), p.Candidate(hold, 3.0, Harm(20, 40))),
        budget=100.0,
        life=1000.0,
    )
    assert p.decide(facts, p.Pursuit('teleport', 1.0)) == hold
    assert p.decide(replace(facts, budget=900.0), p.Pursuit('teleport', 1.0)) == move
    assert p.decide(facts, p.Pursuit('teleport', 1.0), enabled=False) == p.Hold()


def test_a_veto_is_not_lifted_by_an_unlimited_budget_and_retreat_is_said():
    assert hasattr(p, 'Candidate')
    goal = Goal('goal', (20.0, 0.0), 'use', 5.0, PRESSED)
    dangerous = p.Move(Step((15.0, 0.0)), goal)
    retreat = p.Move(Step((-15.0, 0.0)), goal)
    facts = p.Facts(
        1.0,
        goal,
        False,
        True,
        True,
        lambda: dangerous.step,
        candidates=(
            p.Candidate(dangerous, 1.0, Harm(500, 1000, losses=(1000.0,) * 64)),
            p.Candidate(retreat, 20.0, Harm(10, 20), retreat=True),
        ),
        budget=99999.0,
        life=500.0,
    )
    assert p.decide(facts, p.Pursuit('teleport', 1.0)).step.spot == (-15.0, 0.0)
    result = p.decide(replace(facts, budget=0.0), p.Pursuit('teleport', 1.0))
    assert result.step.spot == (-15.0, 0.0)
    assert result.reason


def test_a_firing_stand_needs_a_material_gain_but_an_unsafe_hold_has_no_commitment():
    goal = Goal('goal', (20.0, 0.0), 'fight', 5.0, PRESSED)
    hold = p.Candidate(p.Hold(goal), 2.0, Harm(10, 20))
    move = p.Candidate(p.Move(Step((10.0, 0.0)), goal, 'firing spot'), 1.9, Harm(10, 20))
    facts = p.Facts(1.0, goal, False, True, True, lambda: move.act.step, candidates=(hold, move), budget=100)
    assert p.decide(facts, None) == hold.act
    assert p.decide(replace(facts, candidates=(replace(hold, harm=Harm(200, 300)), move)), None) == move.act


def test_escape_options_include_a_charged_set_on_the_back_and_a_walk():
    from inventory_tracking.macros.movement import SHARED
    from inventory_tracking.macros.skills import TELEPORT
    from inventory_tracking.macros.travel import SAFE_MOVE, Travel
    from inventory_tracking.macros.world import Teleport
    from tests.inventory_tracking.macros.test_travel import ASPECT, game

    play = game()
    play.staff = Teleport(10, 20, False)
    here = play.world.player
    options = Travel(SHARED).options(play.run(), play.world, None, ASPECT, (here.x + 22, here.y), SAFE_MOVE)
    assert {step.skill for step in options} == {None, TELEPORT}


def test_failed_weapon_swap_cannot_authorize_a_battle_priced_act(monkeypatch):
    from inventory_tracking.macros import hunt as module
    from tests.inventory_tracking.macros.test_hunt import game, hunter, keys

    play = game()
    play.sets.reverse()
    hunt = hunter(play)
    hunt.build = replace(hunt.build, settings=hunt.build.settings.model_copy(update={'pursuit': True}))
    monkeypatch.setattr(module, 'take_battle_weapons', lambda run: None)
    run = play.run()
    assert not hunt.main_weapons(run, play.world, keys)
    assert not hunt.main_weapons(run, play.world, keys)  # failed-swap cooldown grants no licence
    run.hands = lambda: ()
    assert not hunt.main_weapons(run, play.world, keys)
    hunt.swap_failed_at = -float('inf')
    assert not hunt.main_weapons(run, play.world, keys)
    run.hands = None
    assert not hunt.main_weapons(run, play.world, keys)


def test_an_empty_priced_choice_set_cannot_fall_back_to_an_unpriced_press():
    goal = Goal('goal', (20.0, 0.0), 'use', 5.0, PRESSED)
    facts = p.Facts(1.0, goal, False, False, True, lambda: Step(goal.place), priced=True)
    assert isinstance(p.decide(facts, p.Pursuit('teleport', 1.0)), p.NoWay)


def test_priced_act_expires_and_restores_the_world_observer():
    import pytest

    from inventory_tracking.macros.actuator import Abort
    from tests.inventory_tracking.macros.test_hunt import game, hunter

    play = game()
    hunt = hunter(play)
    hunt.build = replace(hunt.build, settings=hunt.build.settings.model_copy(update={'pursuit': True}))
    run = play.run()
    now = [0.0]
    run.clock = lambda: now[0]
    observed = []
    original = observed.append
    run.observe = original

    def act():
        with hunt.priced_for(run, 1.5):
            run.world()
            now[0] = 1.6
            run.world()

    with pytest.raises(Abort, match='priced act expired'):
        act()
    assert len(observed) == 2
    assert run.observe is original


def test_expired_macro_walk_returns_to_safety_but_a_player_key_still_wins():
    import pytest

    from inventory_tracking.macros.actuator import Abort
    from inventory_tracking.macros.hunt import RUN_MODES
    from tests.inventory_tracking.macros.test_hunt import game, hunter

    play = game()
    hunt = hunter(play)
    hunt.build = replace(hunt.build, settings=hunt.build.settings.model_copy(update={'pursuit': True}))
    run = play.run()
    now = [0.0]
    run.clock = lambda: now[0]

    def act():
        with hunt.priced_for(run, 1.5):
            play.world = replace(play.world, player=replace(play.world.player, mode=min(RUN_MODES)))
            now[0] = 1.6
            run.world()

    with pytest.raises(Abort, match='priced act expired'):
        act()
    assert hunt.moving(run, play.world) is None  # do not wait for the unsafe destination to be reached
    play.keys.held = True
    assert hunt.moving(run, play.world) == 'a key is held'
    play.keys.held = False
    assert hunt.moving(run, play.world) == 'the character is on the move'


def test_insistence_survives_retreats_but_a_single_press_does_not_buy_more_budget(monkeypatch):
    from types import SimpleNamespace

    from inventory_tracking.combat.harm import Look, SafetySettings
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.macros import safety as module
    from inventory_tracking.macros.world import Loot

    damage = Harm(100, 1000, losses=(100.0,) * 64)
    monkeypatch.setattr(module, 'harm', lambda *a: damage)
    monkeypatch.setattr(module, 'harm_path', lambda *a: damage)
    monkeypatch.setattr(module, 'taken', lambda *a: (100.0, 0))
    monkeypatch.setattr(module, 'camp', lambda *a, **kw: None)
    goal = Goal('goal', (20.0, 0.0), 'use', 5.0, PRESSED)
    seen = SimpleNamespace(origin=(0.0, 0.0), blocked=None, foes={})
    attack = SimpleNamespace(reach=22)
    safety = module.Safety()

    def look(now, pressed_at):
        facts = p.Facts(now, goal, False, False, False, lambda: Step(goal.place))
        return safety.price(
            facts,
            p.Pursuit('teleport', pressed_at),
            Look((), life=1000),
            Loot(life=1000, max_life=1000),
            CALM,
            SafetySettings(),
            seen,
            attack,
            Step,
        )

    first = look(0, 0)
    assert p.decide(first, p.Pursuit('teleport', 0)).reason.startswith('retreating:')
    assert look(0.3, 0).budget == first.budget
    assert look(0.6, 0.6).budget > first.budget
