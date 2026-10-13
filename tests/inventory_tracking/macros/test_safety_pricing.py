import math
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


def test_a_hostile_near_keeps_the_strike_gap_unless_only_a_retreat_is_safe():
    goal = Goal('seal', (20.0, 0.0), 'use', 5.0, PRESSED)
    hold = p.Candidate(p.Hold(goal), 3.0, Harm(20, 40), unstruck=0.0, strikes=True)
    warp = p.Candidate(p.Move(Step((15.0, 0.0)), goal), 1.0, Harm(20, 40), unstruck=1.2, strikes=True)
    use = p.Candidate(p.Operate(goal), 0.9, Harm(20, 40), unstruck=1.0, strikes=True)
    facts = p.Facts(1.0, goal, False, True, True, lambda: warp.act.step, budget=100, life=1000, near=True)
    fresh = p.Pursuit('teleport', 1.0)
    # A strike was just seen: the move fits the gap and wins on time
    assert p.decide(replace(facts, candidates=(hold, warp), quiet=0.1), fresh) == warp.act
    # The landing came 1.1 s after the last strike: the use would make it 2.1 s, so one strike first
    assert p.decide(replace(facts, candidates=(hold, use), quiet=1.1), fresh) == hold.act
    # Nothing near: no gap to keep
    assert p.decide(replace(facts, candidates=(hold, use), quiet=1.1, near=False), fresh) == use.act
    # The strike here is over the budget: the gap does not keep the character in it
    risky = replace(hold, harm=Harm(200, 400))
    assert p.decide(replace(facts, candidates=(risky, use), quiet=1.1), fresh) == use.act


def test_with_every_act_vetoed_the_least_lethal_is_made_and_said_never_a_silent_stop():
    goal = Goal('goal', (20.0, 0.0), 'use', 5.0, PRESSED)
    worse = p.Candidate(p.Move(Step((15.0, 0.0)), goal), 1.0, Harm(900, 1200, losses=(1000.0,) * 64))
    fight = p.Candidate(p.Hold(goal), 2.0, Harm(600, 1100, losses=(1000.0,) * 10 + (100.0,) * 54), True)
    facts = p.Facts(1.0, goal, False, True, True, lambda: worse.act.step, candidates=(worse, fight), life=500.0)
    chosen = p.decide(facts, p.Pursuit('teleport', 1.0))
    assert isinstance(chosen, p.Hold)
    assert 'every act is vetoed' in chosen.reason


def test_escapes_go_away_from_the_threat_back_the_way_come_and_behind_a_companion():
    import math

    from inventory_tracking.combat.harm import Hostile, Look
    from inventory_tracking.macros.safety import ESCAPE_SAME, Safety

    safety = Safety()
    safety.trail.extend([(-30.0, 0.0), (-15.0, 0.0), (0.0, 0.0)])
    look = Look((Hostile(1, 310, (10.0, 0.0)), Hostile(2, 310, (10.0, 4.0))), companions=((-5.0, 6.0),))
    places = safety.escapes((0.0, 0.0), look, Harm())
    assert places[0][0] < -15  # straight away from the pack, the far one first
    assert (-15.0, 0.0) in places  # the way the character came, no nearer the pack
    assert any(p_[0] < -5 and p_[1] > 6 for p_ in places)  # behind the companion, from the pack
    assert all(math.dist(a, b) >= ESCAPE_SAME for i, a in enumerate(places) for b in places[i + 1 :])
    assert safety.escapes((0.0, 0.0), Look(()), Harm()) == []


def _diablo_look(mode: int, frames: int, flying: int):
    """Diablo (243) at the origin, the character 15 units east; his red lightning's missiles 172 in flight at it."""
    from inventory_tracking.combat.harm import Hostile, Look

    missiles = tuple((9, (0.88 * k, 0.0), 0.0) for k in range(1, flying + 1))
    diablo = Hostile(9, 243, (0.0, 0.0), active=True, mode=mode, mode_frames=frames)
    return Look((diablo,), life=1818, missiles=missiles)


def _price_against(monkeypatch, look):
    from types import SimpleNamespace

    from inventory_tracking.combat.harm import SafetySettings
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.macros import safety as module
    from inventory_tracking.macros.world import Loot

    monkeypatch.setattr(module, 'taken', lambda *a: (100.0, 0))
    monkeypatch.setattr(module, 'falls', lambda *a, **kw: {})
    monkeypatch.setattr(module, 'camp', lambda *a, **kw: None)
    goal = Goal('Diablo', (0.0, 0.0), 'fight', 22.0, PRESSED)
    seen = SimpleNamespace(origin=(15.0, 0.0), blocked=None, foes={})
    facts = p.Facts(1.0, goal, True, True, True, lambda: Step(goal.place))
    safety = module.Safety()
    priced = safety.price(
        facts, None, look, Loot(life=1818, max_life=1818), CALM, SafetySettings(), seen,
        SimpleNamespace(reach=22.1), Step,
    )  # fmt: skip
    return priced, safety.decision


def test_his_stream_under_way_makes_a_step_across_his_line_the_act_not_the_hold(monkeypatch):
    # rca/2026-10-13/diablo.md section 5.3, item 5: Diablo at 15 units in SC, age 20, his missiles in flight at the
    # character: the chosen act is a move across his line (an escape priced against holding, not only when unsafe).
    priced, decision = _price_against(monkeypatch, _diablo_look(7, 20, 10))
    assert decision['dear'] == 10.0  # a dear class in the fight
    chosen = p.decide(priced, None)
    assert isinstance(chosen, p.Move)
    assert chosen.reason.startswith('stepping across')
    gap = abs(math.dist(chosen.step.spot, (0.0, 0.0)) - 15.0)
    assert gap < 1.0  # round him, the strike's reach kept


def test_with_no_stream_under_way_no_step_is_priced(monkeypatch):
    priced, decision = _price_against(monkeypatch, _diablo_look(1, 0, 0))
    assert isinstance(p.decide(priced, None), p.Hold)
    assert not any(c['act'] == 'Move' for c in decision['candidates'])
