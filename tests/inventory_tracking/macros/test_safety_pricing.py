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


def _pressed_pack(monkeypatch, *, draw):
    """Three Doom Knights (310) on the character at 3-4 units, its two demons 20 units behind it; the life 700 of
    1000 (a budget of 50 points at the floor of 65%). `draw`: the build's (macros/build.py `Draw`) or None."""
    from types import SimpleNamespace

    from inventory_tracking.combat.harm import Hostile, Look, SafetySettings
    from inventory_tracking.combat.policy import Foe
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.macros import safety as module
    from inventory_tracking.macros.world import Loot

    monkeypatch.setattr(module, 'taken', lambda *a: (100.0, 0))
    monkeypatch.setattr(module, 'falls', lambda *a, **kw: {})
    monkeypatch.setattr(module, 'camp', lambda *a, **kw: None)
    pack = {1: (4.0, 0.0), 2: (4.5, 1.5), 3: (4.5, -1.5)}
    look = Look(
        tuple(Hostile(unit, 310, at, active=True) for unit, at in pack.items()),
        companions=((-20.0, 0.0), (-21.0, 1.0)),
        life=700,
    )
    goal = Goal('the fight', (4.0, 0.0), 'fight', 22.0, PRESSED)
    seen = SimpleNamespace(
        origin=(0.0, 0.0), blocked=None, foes={unit: Foe(310, at, 6000.0, unit == 1) for unit, at in pack.items()}
    )
    facts = p.Facts(1.0, goal, True, True, True, lambda: Step(goal.place))
    safety = module.Safety(draw=draw, sendable=((0, 361), (1, 744)) if draw is not None else ())
    priced = safety.price(
        facts, None, look, Loot(life=700, max_life=1000), CALM, SafetySettings(), seen, SimpleNamespace(reach=22.1),
        lambda point: Step(point),
    )  # fmt: skip
    return p.decide(priced, None), safety


def test_a_draw_that_pulls_the_attackers_onto_the_demons_is_chosen_over_the_retreat(monkeypatch):
    # The player, 2026-10-14: Death Mark "allow to distract/re-aggro enemies". Without the draw the pack's blows put
    # holding over the budget and the act is the retreat; with the demons sent onto the leader the knights round it
    # go for them (the nearest body), holding fits, and the safety asks for the draw on the leader.
    from inventory_tracking.macros.build import Draw

    alone, _ = _pressed_pack(monkeypatch, draw=None)
    assert isinstance(alone, p.Move)
    assert alone.reason.startswith('retreating:')
    draw = Draw(999, lambda world, unit: True, math.inf, 2.8, 1.0, 11.76, pack=8.0, turns=0.58)
    chosen, safety = _pressed_pack(monkeypatch, draw=draw)
    assert isinstance(chosen, p.Hold)
    assert safety.draws is not None
    best = max(safety.draws.values(), key=lambda price: price.worth)
    assert best.worth > 0
    assert best.life > 0
    assert best.pressed  # holding without it was over the budget
    assert safety.priced(1.0) == safety.draws
    assert safety.priced(1.0 + 1.0) is None  # stale after DRAW_FRESH: the row goes by its own rule


SUPER_UNIQUE, MINION = 0x0A, 0x10
# Lord De Seis's seal on 2026-10-14, 02:23:00 (the take 20261013T232029Z-108 at 150.2 s), relative to the character:
# the seal boss (an Oblivion Knight, 312, a ranged caster) 17.7 units off, his Doom Knights (310) between, the Pit
# Lord and the Defiler on the character, as after a Blade Warp.
DE_SEIS = {
    1: (312, (17.0, 5.0), SUPER_UNIQUE),
    2: (310, (6.5, 2.0), MINION),
    3: (310, (10.0, 3.0), MINION),
    4: (310, (13.0, 2.5), MINION),
    5: (310, (14.0, 4.0), MINION),
    6: (310, (15.5, 4.5), MINION),
    7: (310, (16.5, 3.0), MINION),
}


def _seal(monkeypatch, *, deaths, demons=((0.0, 0.0), (0.4, 0.4))):
    """The safety's look at De Seis's seal (DE_SEIS) with the strikes' forecast deaths `deaths` (unit -> seconds) and
    a draw of 0.37 s whose companions land 2.8 units from the hostile 0.28 s after its key."""
    from types import SimpleNamespace

    from inventory_tracking.combat.harm import Hostile, Look, SafetySettings
    from inventory_tracking.combat.policy import Foe
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.macros import safety as module
    from inventory_tracking.macros.build import Draw
    from inventory_tracking.macros.world import Loot

    monkeypatch.setattr(module, 'taken', lambda *a: (3000.0, 0))
    monkeypatch.setattr(module, 'falls', lambda *a, **kw: dict(deaths))
    monkeypatch.setattr(module, 'camp', lambda *a, **kw: None)
    look = Look(
        tuple(Hostile(unit, txt, at, flags, active=True) for unit, (txt, at, flags) in DE_SEIS.items()),
        companions=demons,
        life=1818,
    )
    foes = {unit: Foe(txt, at, 4000.0, flags == SUPER_UNIQUE) for unit, (txt, at, flags) in DE_SEIS.items()}
    seen = SimpleNamespace(origin=(0.0, 0.0), blocked=None, foes=foes)
    goal = Goal('the fight', (6.5, 2.0), 'fight', 22.1, PRESSED)
    facts = p.Facts(1.0, goal, True, True, True, lambda: Step(goal.place))
    draw = Draw(999, lambda world, unit: True, math.inf, 2.8, 0.37, 11.76, arrives=0.28, pack=8.0, turns=0.58)
    safety = module.Safety(draw=draw, sendable=((0, 361), (1, 744)))
    safety.price(
        facts, None, look, Loot(life=1818, max_life=1818), CALM, SafetySettings(), seen, SimpleNamespace(reach=22.1),
        lambda point: Step(point),
    )  # fmt: skip
    return safety


def test_the_draw_onto_a_seal_boss_is_priced_by_the_pack_that_turns_not_by_what_the_demons_leave(monkeypatch):
    # 02:23:00: "no Death Mark on the elite 312 (138710487), 128/128: the safety prices it: saves -40 life": the
    # demons stood on the character, so by the nearest body the model had some knights on them, and sent onto the
    # boss they "left" those knights to the character. The takes show the pack round a marked monster turning to the
    # demons (44% -> 8% at the character three seconds on) and no more life lost by the character after a mark than
    # at an unmarked elite's engagement (67 against 69 points in six seconds, n = 63 / 181).
    safety = _seal(monkeypatch, deaths={2: 0.6, 3: 1.0, 4: 1.4, 5: 1.6, 6: 1.8, 7: 2.0, 1: 3.0})
    assert safety.draws is not None
    assert 1 in safety.draws  # the seal boss is weighed, whatever its share of the harm here
    boss = safety.draws[1]
    assert boss.life > 0
    assert boss.worth > 0
    assert not boss.pressed  # full life: holding fits the budget; the boss is marked by its price alone
