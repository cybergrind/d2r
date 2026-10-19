import logging
import math
from dataclasses import replace
from types import SimpleNamespace

import pytest

from inventory_tracking.combat.harm import GROUND_UNIT, Harm
from inventory_tracking.common import LOG
from inventory_tracking.macros import pursuit as p
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.travel import PRESSED
from tests.inventory_tracking.macros.fakes import patch_hunt


def step_of(act: object) -> Step:
    """The step of an act the test expects to be a move."""
    assert isinstance(act, p.Move)
    return act.step


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
    assert step_of(p.decide(facts, p.Pursuit('teleport', 1.0))).spot == (-15.0, 0.0)
    result = p.decide(replace(facts, budget=0.0), p.Pursuit('teleport', 1.0))
    assert isinstance(result, p.Move)
    assert result.step.spot == (-15.0, 0.0)
    assert result.reason


def test_a_firing_stand_needs_a_material_gain_but_an_unsafe_hold_has_no_commitment():
    goal = Goal('goal', (20.0, 0.0), 'fight', 5.0, PRESSED)
    hold = p.Candidate(p.Hold(goal), 2.0, Harm(10, 20))
    move = p.Candidate(p.Move(Step((10.0, 0.0)), goal, 'firing spot'), 1.9, Harm(10, 20))
    facts = p.Facts(1.0, goal, False, True, True, lambda: step_of(move.act), candidates=(hold, move), budget=100)
    assert p.decide(facts, None) == hold.act
    assert p.decide(replace(facts, candidates=(replace(hold, harm=Harm(200, 300)), move)), None) == move.act


def test_escape_options_include_a_charged_set_on_the_back_and_a_walk():
    from inventory_tracking.game.records import Teleport
    from inventory_tracking.macros.movement import SHARED
    from inventory_tracking.macros.skills import TELEPORT
    from inventory_tracking.macros.travel import SAFE_MOVE, Travel
    from tests.inventory_tracking.macros.test_travel import ASPECT, game

    play = game()
    play.staff = Teleport(10, 20, False)
    here = play.world.player
    assert here is not None
    options = Travel(SHARED).options(play.run(), play.world, None, ASPECT, (here.x + 22, here.y), SAFE_MOVE)
    assert {step.skill for step in options} == {None, TELEPORT}


def test_failed_weapon_swap_cannot_authorize_a_battle_priced_act(monkeypatch):
    from tests.inventory_tracking.macros.test_hunt import game, hunter, keys

    play = game()
    play.sets.reverse()
    hunt = hunter(play)
    hunt.build = replace(hunt.build, settings=hunt.build.settings.model_copy(update={'pursuit': True}))
    patch_hunt(monkeypatch, 'take_battle_weapons', lambda run: None)
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
            player = play.world.player
            assert player is not None
            play.world = replace(play.world, player=replace(player, mode=min(RUN_MODES)))
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
    from inventory_tracking.combat.policy import Observation
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.game.records import Loot
    from inventory_tracking.macros import safety as module

    damage = Harm(100, 1000, losses=(100.0,) * 64)
    monkeypatch.setattr(module, 'harm', lambda *a: damage)
    monkeypatch.setattr(module, 'harm_path', lambda *a: damage)
    monkeypatch.setattr(module, 'taken', lambda *a: (100.0, 0))
    monkeypatch.setattr(module, 'camp', lambda *a, **kw: None)
    goal = Goal('goal', (20.0, 0.0), 'use', 5.0, PRESSED)
    seen = Observation((0.0, 0.0), {})
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
    chosen = p.decide(first, p.Pursuit('teleport', 0))
    assert isinstance(chosen, p.Move)
    assert chosen.reason.startswith('retreating:')
    assert look(0.3, 0).budget == first.budget
    assert look(0.6, 0.6).budget > first.budget


def test_a_hostile_near_keeps_the_strike_gap_unless_only_a_retreat_is_safe():
    goal = Goal('seal', (20.0, 0.0), 'use', 5.0, PRESSED)
    hold = p.Candidate(p.Hold(goal), 3.0, Harm(20, 40), unstruck=0.0, strikes=True)
    warp = p.Candidate(p.Move(Step((15.0, 0.0)), goal), 1.0, Harm(20, 40), unstruck=1.2, strikes=True)
    use = p.Candidate(p.Operate(goal), 0.9, Harm(20, 40), unstruck=1.0, strikes=True)
    facts = p.Facts(1.0, goal, False, True, True, lambda: step_of(warp.act), budget=100, life=1000, near=True)
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
    facts = p.Facts(1.0, goal, False, True, True, lambda: step_of(worse.act), candidates=(worse, fight), life=500.0)
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
    from inventory_tracking.combat.policy import Observation
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.game.records import Loot
    from inventory_tracking.macros import safety as module

    monkeypatch.setattr(module, 'taken', lambda *a: (100.0, 0))
    monkeypatch.setattr(module, 'falls', lambda *a, **kw: {})
    monkeypatch.setattr(module, 'camp', lambda *a, **kw: None)
    goal = Goal('Diablo', (0.0, 0.0), 'fight', 22.0, PRESSED)
    seen = Observation((15.0, 0.0), {})
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
    from inventory_tracking.combat.policy import Foe, Observation
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.game.records import Loot
    from inventory_tracking.macros import safety as module

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
    seen = Observation((0.0, 0.0), {unit: Foe(310, at, 6000.0, unit == 1) for unit, at in pack.items()})
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
    from inventory_tracking.combat.policy import Foe, Observation
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.game.records import Loot
    from inventory_tracking.macros import safety as module
    from inventory_tracking.macros.build import Draw

    monkeypatch.setattr(module, 'taken', lambda *a: (3000.0, 0))
    monkeypatch.setattr(module, 'falls', lambda *a, **kw: dict(deaths))
    monkeypatch.setattr(module, 'camp', lambda *a, **kw: None)
    look = Look(
        tuple(Hostile(unit, txt, at, flags, active=True) for unit, (txt, at, flags) in DE_SEIS.items()),
        companions=demons,
        life=1818,
    )
    foes = {unit: Foe(txt, at, 4000.0, flags == SUPER_UNIQUE) for unit, (txt, at, flags) in DE_SEIS.items()}
    seen = Observation((0.0, 0.0), foes)
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


# The game of 06:05 on 2026-10-14 (rca/2026-10-14/run-0305-findings.md §5.6): Diablo (unit 9 here) at (7793.5, 5293.5)
# cast his wall at 06:08:56.69 and died at 57.67; the character stood at (7807.5, 5290.5), his Amulet lay at
# (7793, 5296). The ten makers left him at these angles off the line to the character (the take's flames 180, read off
# their path records); the walk from 58.03 to 58.75 lost 107 + 63 life to the flames (and 41 + 55 at the stand
# before it), the mercenary went from 96% to 43%.
DIABLO_AT, STAND, AMULET = (7793.5, 5293.5), (7807.5, 5290.5), (7793.0, 5296.0)
WALL_ANGLES = (-33, -20, -6, 1, 12, 27, 31, 43, 46, 57)


def _wall(age: int) -> tuple[tuple[int, int, float, float], ...]:
    """His wall `age` frames after the cast, as the look reads it (owner, class, x, y): each maker WALL_STEP a frame
    out along its line, the flames it left the last FLAME_LIFE frames behind it."""
    from inventory_tracking.combat.sim import diablo as rules

    toward = math.atan2(STAND[1] - DIABLO_AT[1], STAND[0] - DIABLO_AT[0])
    found = []
    for degrees in WALL_ANGLES:
        heading = toward + math.radians(degrees)
        dx, dy = math.cos(heading) * rules.WALL_STEP, math.sin(heading) * rules.WALL_STEP
        if age < rules.WALL_LIFE:
            found.append((9, rules.WALL_MAKER, DIABLO_AT[0] + dx * age, DIABLO_AT[1] + dy * age))
        for k in range(max(0, age - rules.FLAME_LIFE), min(age, rules.WALL_LIFE)):
            found.append((9, rules.WALL_FLAME, DIABLO_AT[0] + dx * k, DIABLO_AT[1] + dy * k))
    return tuple(found)


def _after_diablo(monkeypatch, age: int, start=STAND, drop=AMULET):
    """The look `age` frames after his wall's cast, he dead 24 frames after it (as at 06:08:57.67), and the act
    the safety chooses for the pickup of his Amulet (at `drop`) from `start` at the life then (1482 of 1818)."""
    from types import SimpleNamespace

    from inventory_tracking.combat.harm import SafetySettings
    from inventory_tracking.combat.policy import Observation
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.game.records import Loot, Monster
    from inventory_tracking.macros import safety as module
    from inventory_tracking.macros.goals import PICK_UP
    from tests.inventory_tracking.macros.fakes import player, world

    monkeypatch.setattr(module, 'taken', lambda *a: (0.0, 0))
    monkeypatch.setattr(module, 'falls', lambda *a, **kw: {})
    monkeypatch.setattr(module, 'camp', lambda *a, **kw: None)
    # the character's resistances as its hurt events had them (stats 39 fire 190, 41 lightning 179: Hell's penalty in)
    loot = Loot(life=1482, max_life=1818, stats=((39, 190), (41, 179), (43, 175), (45, 175)))
    stand = player(108, x=start[0], y=start[1])
    safety = module.Safety()
    diablo = Monster(9, 243, 7, *DIABLO_AT, 0xFFFFFFFF, life=100, max_life=1000)
    for frame in range(0, min(age, 24) + 1, 3):  # looks while he casts and lives
        alive = world(108, player=stand, monsters=(diablo,))
        safety.look(alive, loot, 'battle', now=frame / 25, flights=lambda kinds, frame=frame: _wall(frame))
    dead = world(108, player=stand, monsters=())
    look = safety.look(dead, loot, 'battle', now=age / 25, flights=lambda kinds: _wall(age))
    goal = Goal('Amulet', drop, PICK_UP, 1.5, PRESSED)
    facts = p.Facts(age / 25, goal, False, False, True, lambda: Step(goal.place))
    posted = p.Pursuit('pickup', age / 25)
    seen = Observation(start, {})
    priced = safety.price(
        facts, posted, look, loot, CALM, SafetySettings(), seen, SimpleNamespace(reach=22.1), lambda point: Step(point)
    )
    return p.decide(priced, posted), safety.decision


def test_the_loot_walk_after_diablo_prices_his_fire_wall_his_death_or_not(monkeypatch):
    # 06:08:57.83, 28 frames after the cast and 4 after his death, from where the character stood: the walk to the
    # Amulet crosses the wall. It was priced at nothing (no hostile left); the walk lost 170 life to it.
    chosen, decision = _after_diablo(monkeypatch, 28)
    operate = next(c for c in decision['candidates'] if c['act'] == 'Operate')
    assert dict(operate['contributors'])[GROUND_UNIT] > 50
    assert 100 < operate['H'] < 300  # the game's 107 + 63 by the walk, at its resistances
    # standing it out there is no better: the makers come at where the character stands (41 + 55 there that game)
    waits = [c for c in decision['candidates'] if c['act'] == 'NoWay' and not c['retreat']]
    assert waits
    assert all(c['H'] > operate['H'] for c in waits)
    assert isinstance(chosen, p.Operate)
    # Two seconds on the flames by the way are out, and nothing is offered but the pickup
    gone, decision = _after_diablo(monkeypatch, 28 + 50)
    assert isinstance(gone, p.Operate)
    assert [c['act'] for c in decision['candidates']] == ['Operate']


def test_the_loot_walk_waits_for_his_flames_across_the_way_where_the_character_stands_clear(monkeypatch):
    # Out of his wall's fan (where the step of the fight below puts it), as soon as he is dead, at about the
    # least life of that game (1216 of 1818 at 06:08:58.8; here 1195: a budget of 13 points over the floor): the walk
    # to the Amulet where he stood crosses the flames his makers left there, which is over the budget while they
    # stand; standing here is not. The act is to wait them out (no hardcoded wait: the same walk priced after the
    # wait); once they are out, the pickup.
    from types import SimpleNamespace

    from inventory_tracking.combat.harm import SafetySettings
    from inventory_tracking.combat.policy import Observation
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.game.records import Loot, Monster
    from inventory_tracking.macros import safety as module
    from inventory_tracking.macros.goals import PICK_UP
    from tests.inventory_tracking.macros.fakes import player, world

    monkeypatch.setattr(module, 'taken', lambda *a: (0.0, 0))
    monkeypatch.setattr(module, 'falls', lambda *a, **kw: {})
    monkeypatch.setattr(module, 'camp', lambda *a, **kw: None)
    loot = Loot(life=1195, max_life=1818, stats=((39, 190), (41, 179), (43, 175), (45, 175)))
    edge, drop = (7800.4, 5281.0), AMULET  # an edge of his fan, 14 units from where he stood
    stand = player(108, x=edge[0], y=edge[1])
    diablo = Monster(9, 243, 1, *DIABLO_AT, 0xFFFFFFFF, life=100, max_life=1000)

    def act(age: int):
        safety = module.Safety()
        for frame in range(0, 22, 3):  # looks while he lives
            alive = world(108, player=stand, monsters=(diablo,))
            safety.look(alive, loot, 'battle', now=frame / 25, flights=lambda kinds, frame=frame: _wall(frame))
        look = safety.look(world(108, player=stand), loot, 'battle', now=age / 25, flights=lambda kinds: _wall(age))
        goal = Goal('Amulet', drop, PICK_UP, 1.5, PRESSED)
        facts = p.Facts(age / 25, goal, False, False, True, lambda: Step(goal.place))
        posted = p.Pursuit('pickup', age / 25)
        priced = safety.price(
            facts, posted, look, loot, CALM, SafetySettings(), Observation(edge, {}),
            SimpleNamespace(reach=22.1), lambda point: Step(point),
        )  # fmt: skip
        return p.decide(priced, posted), safety.decision

    waited, decision = act(22)
    operate = next(c for c in decision['candidates'] if c['act'] == 'Operate')
    assert operate['worst'] > decision['budget']
    assert isinstance(waited, p.NoWay), decision['candidates']
    assert waited.reason == module.BURNING
    gone, _ = act(22 + 40)
    assert isinstance(gone, p.Operate)


def test_while_diablo_lives_his_fire_wall_coming_at_the_character_is_stepped_out_of(monkeypatch):
    # 06:08:56.69 to 57.67: he cast the wall at 14 units and the character held its stand under it (41 + 55 life
    # before his death, his wall unpriced). Four frames after the cast the hold is priced with the makers that come
    # at it, and a place off the fan, his strike's reach kept, is the act.
    from types import SimpleNamespace

    from inventory_tracking.combat.harm import SafetySettings
    from inventory_tracking.combat.policy import Observation
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.game.records import Loot, Monster
    from inventory_tracking.macros import safety as module
    from tests.inventory_tracking.macros.fakes import player, world

    monkeypatch.setattr(module, 'taken', lambda *a: (100.0, 0))
    monkeypatch.setattr(module, 'falls', lambda *a, **kw: {})
    monkeypatch.setattr(module, 'camp', lambda *a, **kw: None)
    loot = Loot(life=1482, max_life=1818, stats=((39, 190), (41, 179), (43, 175), (45, 175)))
    stand = player(108, x=STAND[0], y=STAND[1])
    safety = module.Safety()
    diablo = Monster(9, 243, 1, *DIABLO_AT, 0xFFFFFFFF, life=100, max_life=1000)
    alive = world(108, player=stand, monsters=(diablo,))
    look = safety.look(alive, loot, 'battle', now=0.16, flights=lambda k: _wall(4))
    goal = Goal('Diablo', DIABLO_AT, 'fight', 22.0, PRESSED)
    facts = p.Facts(0.16, goal, True, True, True, lambda: Step(goal.place))
    seen = Observation(STAND, {})
    priced = safety.price(
        facts, None, look, loot, CALM, SafetySettings(), seen, SimpleNamespace(reach=22.1), lambda point: Step(point)
    )
    chosen = p.decide(priced, None)
    hold = next(c for c in safety.decision['candidates'] if c['act'] == 'Hold')
    assert dict(hold['contributors']).get(GROUND_UNIT, 0) > 0
    assert isinstance(chosen, p.Move), safety.decision['candidates']
    assert 'fire wall' in chosen.reason
    assert math.dist(chosen.step.spot, DIABLO_AT) < 22.0  # he is struck from there


# The game of 06:05 on 2026-10-14 (rca/2026-10-14/run-0305-findings.md §5.2): Diablo entered his lightning's mode
# (SC) at 06:08:52.18; the first step across was decided at 52.30, three frames in, before his first missile flew
# (52.78): the stream, aimed at where the character stands as each missile is made, came at the step's place (151
# at 53.51). The second step (53.14) went back to the place the first had left (138 at 53.99).
SC_START = 3  # frames into SC at the first step's decision


def _diablo_looks(monkeypatch, looks):
    """A Safety's looks in one cast of his lightning: each (frames into SC, where the character stands, missiles in
    flight as (place, heading)); the act chosen at each, the character standing where the look says."""
    from types import SimpleNamespace

    from inventory_tracking.combat.harm import SafetySettings
    from inventory_tracking.combat.policy import Observation
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.game.records import Loot, Monster
    from inventory_tracking.macros import safety as module
    from tests.inventory_tracking.macros.fakes import player, world

    monkeypatch.setattr(module, 'taken', lambda *a: (100.0, 0))
    monkeypatch.setattr(module, 'falls', lambda *a, **kw: {})
    monkeypatch.setattr(module, 'camp', lambda *a, **kw: None)
    loot = Loot(life=1760, max_life=1818, stats=((39, 190), (41, 179), (43, 175), (45, 175)))
    diablo = Monster(9, 243, 7, 0.0, 0.0, 0xFFFFFFFF, life=900, max_life=1000)
    safety = module.Safety()
    goal = Goal('Diablo', (0.0, 0.0), 'fight', 22.0, PRESSED)
    chosen = []
    for frames, here, flying in looks:
        now = frames / 25
        stand = player(108, x=here[0], y=here[1])
        reads = tuple((9, 172, at[0], at[1]) for at, _ in flying)
        alive = world(108, player=stand, monsters=(diablo,))
        look = safety.look(alive, loot, 'battle', now=now, flights=lambda k, r=reads: r)
        facts = p.Facts(now, goal, True, True, True, lambda: Step(goal.place))
        seen = Observation(here, {})
        priced = safety.price(
            facts, None, look, loot, CALM, SafetySettings(), seen, SimpleNamespace(reach=22.1), lambda pt: Step(pt)
        )
        chosen.append((p.decide(priced, None), safety.decision))
    return chosen


def _stream_at(here, frames_flown: int):
    """His missiles in flight at `here` from the origin: one a frame for `frames_flown` frames, STREAM_STEP apart."""
    heading = math.atan2(here[1], here[0])
    step = (0.88 * math.cos(heading), 0.88 * math.sin(heading))
    return tuple(((step[0] * k, step[1] * k), heading) for k in range(1, frames_flown + 1))


def test_no_step_across_his_lightning_is_offered_before_a_missile_flies(monkeypatch):
    here = (14.0, 0.0)
    ((act, decision),) = _diablo_looks(monkeypatch, [(SC_START, here, ())])
    assert not any(c['why'].startswith('stepping across') for c in decision['candidates'])
    assert not (isinstance(act, p.Move) and act.reason.startswith('stepping across'))


def test_a_step_across_his_lightning_never_goes_back_to_the_place_it_left_in_the_same_cast(monkeypatch):
    start = (14.0, 0.0)
    (first,) = _diablo_looks(monkeypatch, [(20, start, _stream_at(start, 10))])
    act = first[0]
    assert isinstance(act, p.Move), first[1]['candidates']
    assert act.reason.startswith('stepping across')
    landed = act.step.spot
    both = _diablo_looks(monkeypatch, [(20, start, _stream_at(start, 10)), (30, landed, _stream_at(landed, 8))])
    _, decision = both[1]
    places = [c['place'] for c in decision['candidates'] if c['why'].startswith('stepping across')]
    assert all(math.dist(place, start) >= 4.0 for place in places), places


def test_a_step_out_of_his_stream_in_flight_is_not_held_to_the_strike_gap_as_a_move_in_flight():
    # rca/2026-10-14/diablo-handling.md R2, fix 1: the 06:08 look at +0.60 (take 20261014T030618Z-108): holding 22.77 s
    # against the step across's 16.0, 0.58 s after the last strike; the step's 1.06 s without a strike missed the
    # 1.6 s gap by 0.04 s and the hold was made, the stream tanked. I2: "... unless a move is in flight".
    goal = Goal('Diablo', (0.0, 0.0), 'fight', 22.0, PRESSED)
    hold = p.Candidate(p.Hold(goal), 22.77, Harm(30, 60), unstruck=0.0, strikes=True)
    dodge = p.Move(Step((13.5, 3.5)), goal, "stepping across Diablo's lightning", dodge=True)
    across = p.Candidate(dodge, 16.0, Harm(20, 40), unstruck=1.06, strikes=True)
    facts = p.Facts(1.0, goal, True, True, True, lambda: Step(goal.place), budget=500, life=1818, near=True)
    assert p.decide(replace(facts, candidates=(hold, across), quiet=0.58), None) == dodge
    # A step that is not out of an act under way is held to the gap as before: one strike first
    plain = replace(across, act=replace(dodge, reason='firing spot', dodge=False))
    assert p.decide(replace(facts, candidates=(hold, plain), quiet=0.58), None) == hold.act
    # The dodge still competes on its price, and never past the budget
    assert p.decide(replace(facts, candidates=(hold, replace(across, seconds=30.0)), quiet=0.58), None) == hold.act
    dear = replace(across, harm=Harm(20, 600))
    assert p.decide(replace(facts, candidates=(hold, dear), quiet=0.58), None) == hold.act


def test_a_step_across_his_stream_in_flight_is_a_dodge_and_the_threats_geometry_is_not(monkeypatch):
    start = (14.0, 0.0)
    ((act, decision),) = _diablo_looks(monkeypatch, [(20, start, _stream_at(start, 10))])
    assert isinstance(act, p.Move), decision['candidates']
    assert act.dodge
    stepping = [c for c in decision['candidates'] if c['why'].startswith('stepping across')]
    assert stepping
    assert all(c['dodge'] for c in stepping)
    assert not any(c['dodge'] for c in decision['candidates'] if c not in stepping)


def test_a_retreat_that_keeps_the_strike_and_fits_the_budget_comes_before_the_least_harm():
    """rca/2026-10-14/baal-sim.md fix 1: with nothing here fitting the budget, a retreat within the strike's reach of
    what ends the harm is taken before the least-harm one out of reach (which only defers the harm), the cheapest of
    them; one over the budget is not, and then the least harm goes as before."""
    goal = Goal('the fight', (0.0, 0.0), 'fight', 22.0, PRESSED)
    hold = p.Candidate(p.Hold(goal), 8.5, Harm(186, 502), unstruck=0.0, strikes=True)
    far = p.Candidate(p.Move(Step((35.0, 0.0)), goal), 3.4, Harm(154, 233), retreat=True, unstruck=3.4)
    near = p.Candidate(p.Move(Step((20.6, 5.0)), goal), 2.1, Harm(160, 266), True, 2.1, True, keeps=True)
    nearer = replace(near, seconds=2.0, harm=Harm(165, 270))
    dear = replace(near, harm=Harm(170, 450))
    facts = p.Facts(
        1.0, None, False, True, True, lambda: step_of(far.act), candidates=(hold, far, near), budget=389.0,
        life=1560.0, kappa=0.01, near=True,
    )  # fmt: skip
    chosen = p.arbitrate(facts)
    assert isinstance(chosen, p.Move)
    assert chosen.step == step_of(near.act)
    assert chosen.reason == p.KEEPING
    assert step_of(p.arbitrate(replace(facts, candidates=(hold, far, near, nearer)))) == step_of(nearer.act)
    alone = p.arbitrate(replace(facts, candidates=(hold, far, dear)))
    assert isinstance(alone, p.Move)
    assert alone.step == step_of(far.act)
    assert alone.reason.startswith('retreating:')


def test_the_hostile_whose_kill_ends_the_harm_counts_what_is_bound_to_it():
    """`keeper`: Baal's clone goes with him (combat/threats `bound`), so the harm of both is his kill's; a pack whose
    harm is spread names none, and neither does harm from no hostile that can be struck."""
    from inventory_tracking.combat.harm import Hostile, Look
    from inventory_tracking.combat.policy import Foe, Observation
    from inventory_tracking.macros import safety as module

    baal, clone, tentacle = Hostile(1, 544, (20.0, 0.0)), Hostile(2, 570, (8.0, 0.0)), Hostile(3, 564, (5.0, 0.0))
    look = Look((baal, clone, tentacle))
    seen = Observation((0.0, 0.0), {h.unit: Foe(h.txt, h.at, 1000.0) for h in (baal, clone, tentacle)})
    assert module.keeper(look, seen, Harm(186, 502, by=((2, 163.0), (1, 23.0)))) == 1
    assert module.keeper(look, seen, Harm(186, 502, by=((3, 120.0), (1, 30.0), (2, 36.0)))) == 3
    spread = Look(tuple(Hostile(unit, 345, (10.0, unit)) for unit in range(10, 15)))
    pack = Observation((0.0, 0.0), {h.unit: Foe(h.txt, h.at, 1000.0) for h in spread.hostiles})
    assert module.keeper(spread, pack, Harm(100, 200, by=tuple((unit, 20.0) for unit in range(10, 15)))) is None
    assert module.keeper(look, seen, Harm(100, 200, by=((GROUND_UNIT, 100.0),))) is None


def test_the_places_that_keep_the_fight_lie_inside_the_reach_the_nearest_first():
    from inventory_tracking.macros import safety as module

    at, here = (0.0, 0.0), (19.4, 0.0)
    places = module.keeping(here, at, 22.1)
    assert len(places) == module.KEEP_MOST
    assert all(math.dist(place, at) == pytest.approx(22.1 - module.KEEP_MARGIN) for place in places)
    gaps = [math.dist(here, place) for place in places]
    assert gaps == sorted(gaps)
    assert gaps[0] < 2.0


def _clump_fight(monkeypatch, *, offer=None, posted='run', now=5.0, harm_at_stand=0.0):
    """The Ancient's Way pack of run-1932-findings.md §4 (22:50:26.9): two hostiles 20 to 21.5 units off, at the edge
    of the reach, and the rest of their pack 24 to 28 off, just out of it (the fights ended there, "nothing left in
    reach"); a level run's fight priced near nothing against the budget. `offer`: the place the fight's own look found
    and when (`Safety.offer`); `harm_at_stand`: the harm of any way that ends there (a dangerous pack round it)."""
    from inventory_tracking.builds.warlock.echoing_strike.attack import ECHOING_STRIKE_ATTACK
    from inventory_tracking.combat.harm import Hostile, Look, SafetySettings
    from inventory_tracking.combat.policy import Foe, Observation
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.game.records import Loot
    from inventory_tracking.macros import safety as module
    from inventory_tracking.macros.goals import FIGHT

    stand = offer[0] if offer is not None else None

    def priced(look, path, *rest):
        end = path[-1][0] if isinstance(path, tuple) and path and isinstance(path[0], tuple) else path
        hurt = harm_at_stand if stand is not None and math.dist(end, stand.spot) < 0.5 else 0.0
        return Harm(hurt, 2 * hurt)

    monkeypatch.setattr(module, 'harm_path', priced)
    monkeypatch.setattr(module, 'harm', lambda look, at, *rest: priced(look, at))
    spots = ((20.0, 0.0), (21.5, 1.0), (24.0, -1.5), (25.0, 2.0), (26.5, -1.0), (28.0, 0.5))
    pack = dict(enumerate(spots))
    seen = Observation((0.0, 0.0), {unit: Foe(624, at, 3000.0) for unit, at in pack.items()})
    look = Look(tuple(Hostile(unit, 624, at, active=True) for unit, at in pack.items()), life=1800)
    goal = Goal('clearing the way', pack[0], FIGHT, 22.1, PRESSED, clearing=True)
    facts = p.Facts(now, goal, True, True, True, lambda: Step(goal.place), area=118, near=True)
    pursuit = p.Pursuit('pickup', 0.0, advance=False, leash=p.FULL, area=118) if posted == 'run' else None
    safety = module.Safety()
    if offer is not None:
        safety.offer(*offer)
    found = safety.price(
        facts, pursuit, look, Loot(life=1800, max_life=1800), CALM, SafetySettings(), seen, ECHOING_STRIKE_ATTACK,
        lambda point: Step(point),
    )  # fmt: skip
    return p.decide(found, pursuit), found


def test_a_level_runs_safe_fight_moves_to_the_nearer_stand_its_look_found_when_it_takes_materially_more(monkeypatch):
    # Before: Hold was the only act of the safe fights, and the run struck from the edge of the reach (17 to 22 units,
    # a third of the casts hitting nothing). The stand 12 from the clump (the attack's engage ring) is gone to.
    held, _ = _clump_fight(monkeypatch)
    assert isinstance(held, p.Hold)
    stand = Step((8.0, 0.0))
    chosen, priced = _clump_fight(monkeypatch, offer=(stand, 4.8))
    assert isinstance(chosen, p.Move)
    assert chosen.step.spot == stand.spot
    assert chosen.reason == 'firing spot'
    hold = next(c for c in priced.candidates if isinstance(c.act, p.Hold))
    move = next(c for c in priced.candidates if isinstance(c.act, p.Move))
    assert hold.seconds - move.seconds > max(0.3, 0.2 * hold.seconds)  # the commitment's material gain


def test_the_stand_its_look_found_is_not_gone_to_into_harm_over_the_budget_stale_or_outside_a_run(monkeypatch):
    stand = Step((8.0, 0.0))
    # a dangerous pack round the stand: its harm decides (no reckless closing)
    chosen, _ = _clump_fight(monkeypatch, offer=(stand, 4.8), harm_at_stand=5000.0)
    assert isinstance(chosen, p.Hold)
    # looked at more than STAND_FRESH ago: the next look prices its own
    chosen, priced = _clump_fight(monkeypatch, offer=(stand, 3.0))
    assert isinstance(chosen, p.Hold)
    assert len(priced.candidates) == 1
    # attack mode alone, no run and no press: the mode does not go anywhere of its own
    chosen, priced = _clump_fight(monkeypatch, offer=(stand, 4.8), posted=None)
    assert isinstance(chosen, p.Hold)
    assert len(priced.candidates) == 1
    # one onto a hostile (within KEEP_AWAY) is no stand
    chosen, priced = _clump_fight(monkeypatch, offer=(Step((16.0, 0.0)), 4.8))
    assert len(priced.candidates) == 1


# -- the look's time: the goal's way within its share, once a look; a look over its time said --------------------


def _run_fight(monkeypatch, *, way, timer=None, safety=None):
    """A level run's fight not yet at its goal (Hold, and the advance priced beside it: `price`'s Hold branch), the
    goal's way `way` (counted by the caller); the safety's clock `timer` (None: the arena's, no clock)."""
    from inventory_tracking.combat.harm import Hostile, Look, SafetySettings
    from inventory_tracking.combat.policy import Foe, Observation
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.game.records import Loot
    from inventory_tracking.macros import safety as module
    from inventory_tracking.macros.goals import FIGHT

    monkeypatch.setattr(module, 'taken', lambda *a, **kw: (100.0, 0))
    monkeypatch.setattr(module, 'falls', lambda *a, **kw: {})
    monkeypatch.setattr(module, 'camp', lambda *a, **kw: None)
    seen = Observation((0.0, 0.0), {1: Foe(624, (15.0, 0.0), 3000.0)})
    look = Look((Hostile(1, 624, (15.0, 0.0), active=True),), life=1800)
    goal = Goal('the rest of the level', (300.0, 0.0), FIGHT, 22.1, PRESSED, clearing=True)
    facts = p.Facts(5.0, goal, False, True, True, way, area=105, near=True)
    pursuit = p.Pursuit('pickup', 0.0, advance=False, leash=p.FULL, area=105)
    safety = safety if safety is not None else module.Safety()
    safety.timer = timer
    found = safety.price(
        facts, pursuit, look, Loot(life=1800, max_life=1800), CALM, SafetySettings(), seen,
        SimpleNamespace(reach=22.1), lambda point: Step(point),
    )  # fmt: skip
    return p.decide(found, pursuit), found, safety


def test_the_goals_way_is_asked_once_a_look_within_its_share_of_the_looks_time(monkeypatch):
    # The Plains of Despair, 23:48 on 2026-10-14 (rca/2026-10-14/run-2040-findings.md §1.2): the way to Izual 342 off
    # was asked with no bound at every look, the strike and the drinker waiting on it
    from inventory_tracking.combat.harm import SafetySettings
    from inventory_tracking.macros import travel
    from inventory_tracking.macros.safety import WAY_SHARE

    asked = []
    reads = iter(range(10**6))

    def way():
        plan = travel.PLANNING.get()
        asked.append(None if plan is None else plan.until)
        return Step((20.0, 0.0))

    clock = lambda: next(reads) * 1e-4  # ruff: ignore[lambda-assignment] - a tenth of a millisecond at each read
    chosen, priced, _ = _run_fight(monkeypatch, timer=clock, way=way)
    assert isinstance(chosen, p.Hold)
    assert any(isinstance(c.act, p.Move) for c in priced.candidates)  # the advance priced beside the hold
    assert priced.way() == Step((20.0, 0.0))  # the arbiter and the act go by the same leg
    assert len(asked) == 1
    assert asked[0] == pytest.approx(SafetySettings().look_seconds * WAY_SHARE, abs=1e-3)  # from the look's start
    # with no clock (the arena) the way is asked as before, with no bound
    asked.clear()
    _run_fight(monkeypatch, way=way)
    assert asked == [None]


def test_past_the_looks_time_no_way_is_asked_and_a_look_over_its_time_is_said_once_a_second(monkeypatch, caplog):
    asked = []
    reads = iter(range(10**6))
    slow = lambda: next(reads) * 0.05  # ruff: ignore[lambda-assignment] - every stage of the look 50 ms

    def way():
        asked.append(1)
        return Step((20.0, 0.0))

    with caplog.at_level(logging.INFO, logger=LOG.name):
        chosen, priced, safety = _run_fight(monkeypatch, timer=slow, way=way)
        assert isinstance(chosen, p.Hold)
        assert not asked  # the advance is the next look's to price
        assert len(priced.candidates) == 1
        _run_fight(monkeypatch, timer=slow, way=way, safety=safety)  # the same look's clock: within the second
        said = [r.getMessage() for r in caplog.records if r.getMessage().startswith('Macro: look:')]
        assert len(said) == 1
        assert 'over budget (80 ms)' in said[0]
        assert said[0].endswith('-> Hold')
        safety.over_said -= 1.0
        _run_fight(monkeypatch, timer=slow, way=way, safety=safety)
        said = [r.getMessage() for r in caplog.records if r.getMessage().startswith('Macro: look:')]
    assert len(said) == 2
    assert said[1].endswith('(1 more since)')


def test_with_no_hostile_near_a_look_may_grow_the_goals_way_longer():
    # 2026-10-17: a cold field to the next chest grew 40 ms a look, the straight line or no way for three or four looks
    from inventory_tracking.macros.safety import QUIET_WAY_SECONDS, WAY_SHARE, way_seconds

    assert way_seconds((0.0, 0.0), [], 0.08) == QUIET_WAY_SECONDS
    assert way_seconds((0.0, 0.0), [(50.0, 0.0)], 0.08) == QUIET_WAY_SECONDS  # far off
    assert way_seconds((0.0, 0.0), [(10.0, 0.0)], 0.08) == 0.08 * WAY_SHARE  # one near: the look's share


def test_a_teleports_window_holds_the_keys_second_press_and_its_price_is_unchanged():
    # rca/2026-10-17/teleport-not-cast-findings.md: ~5% of Teleport keys cast nothing; the press again lands 0.26-0.39 s
    # later, but the act's window (its price, 0.81 s) ran out first in 115 of 126 and the hop counted as failed
    from inventory_tracking.macros.build import PricedStep
    from inventory_tracking.macros.hunting.base import act_window
    from inventory_tracking.macros.teleport import REPRESS_SECONDS, TELEPORT

    hop = PricedStep((10.0, 10.0), TELEPORT, needs='travel', seconds=0.81)
    assert act_window(hop) == pytest.approx(0.81 + REPRESS_SECONDS)
    assert hop.seconds == 0.81  # the price is the arbiter's as before
    assert act_window(PricedStep((10.0, 10.0), None, needs='battle', seconds=1.2)) == 1.2  # a walk: its price


def test_a_teleport_of_the_characters_own_is_priced_with_no_weapon_swap(monkeypatch):
    # 10:55-11:08 on 2026-10-18: with Enigma's Teleport priced with a swap there and back (2.31 s unstruck), none of
    # 172 Teleports to a firing spot fitted the strike gap on Catacombs 4
    # (rca/2026-10-18/sluggish-engagement-findings.md)
    from types import SimpleNamespace

    from inventory_tracking.combat.harm import Look, SafetySettings
    from inventory_tracking.combat.policy import Observation
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.game.records import Loot
    from inventory_tracking.macros import safety as module
    from inventory_tracking.macros.skills import TELEPORT

    monkeypatch.setattr(module, 'harm', lambda *a: Harm(10, 20))
    monkeypatch.setattr(module, 'harm_path', lambda *a: Harm(10, 20))
    monkeypatch.setattr(module, 'taken', lambda *a, **kw: (100.0, 0))
    monkeypatch.setattr(module, 'camp', lambda *a, **kw: None)
    goal = Goal('goal', (40.0, 0.0), 'use', 5.0, PRESSED)

    def teleport(hands) -> tuple[p.Candidate, ...]:
        facts = p.Facts(1.0, goal, False, False, False, lambda: Step(goal.place, TELEPORT))
        priced = module.Safety().price(
            facts, p.Pursuit('teleport', 1.0), Look((), life=1000), Loot(life=1000, max_life=1000), CALM,
            SafetySettings(), Observation((0.0, 0.0), {}), SimpleNamespace(reach=22),
            lambda point: Step(point, TELEPORT), teleport_hands=hands,
        )  # fmt: skip
        return tuple(c for c in priced.candidates if isinstance(c.act, p.Move) and c.act.step.skill == TELEPORT)

    staff, own = teleport('travel'), teleport('battle')
    assert staff
    assert own
    assert min(c.unstruck for c in staff) - min(c.unstruck for c in own) == pytest.approx(2 * module.SWAP_SECONDS)


@pytest.mark.parametrize(
    ('at_goal', 'at_step', 'shorter'),
    [
        # The move over the budget, the step out of the fire within it: shorter stands are priced (were not)
        (Harm(400, 900, by=((GROUND_UNIT, 400.0),)), Harm(1, 2), True),
        # The move within it, the step over it: no shorter stand (they were priced)
        (Harm(100, 200, by=((GROUND_UNIT, 100.0),)), Harm(400, 900), False),
    ],
)
def test_shorter_approaches_follow_the_moves_own_price_not_what_its_fire_adds(monkeypatch, at_goal, at_step, shorter):
    # Fire on the way adds burnt-out waits and steps out of it after the move; the over-budget check read the last
    # of them, not the move (found splitting `Safety.price`, fixed 2026-10-19).
    from inventory_tracking.combat.harm import Look, SafetySettings
    from inventory_tracking.combat.policy import Observation
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.game.records import Loot
    from inventory_tracking.macros import safety as module

    goal, out = (20.0, 0.0), (0.0, 6.0)

    def priced(look, path, *rest):
        end = path[-1][0] if isinstance(path, tuple) and path and isinstance(path[0], tuple) else path
        return at_goal if end == goal else at_step if end == out else Harm(1, 2)

    fire = SimpleNamespace(clears=lambda lying: 2.0, escapes=lambda lying, here: [(out, 'out of the fire')])
    monkeypatch.setattr(module, 'harm_path', priced)
    monkeypatch.setattr(module, 'harm', lambda look, at, *rest: priced(look, at))
    monkeypatch.setattr(module, 'taken', lambda *a, **kw: (100.0, 0))
    monkeypatch.setattr(module, 'camp', lambda *a, **kw: None)
    monkeypatch.setattr(module, 'footing', lambda field, here, point: point)
    facts = p.Facts(1.0, Goal('goal', goal, 'use', 5.0, PRESSED), False, False, False, lambda: Step(goal))
    found = module.Safety().price(
        facts, p.Pursuit('teleport', 1.0), Look((), life=1000, ground=((fire, ()),)),  # pyrefly: ignore[bad-argument-type]  # a fake read model
        Loot(life=1000, max_life=1000), CALM, SafetySettings(), Observation((0.0, 0.0), {}), SimpleNamespace(reach=22),
        Step,
    )  # fmt: skip
    reasons = [c.act.reason for c in found.candidates if isinstance(c.act, (p.Move, p.NoWay))]
    assert reasons[:4] == ['', module.BURNING, module.BURNING, f'{module.STEPPING} out of the fire']
    assert ('safe approach' in reasons) is shorter
