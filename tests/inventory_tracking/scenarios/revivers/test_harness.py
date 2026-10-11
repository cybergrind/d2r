"""The harness (harness.py): it deals what the production simulator deals, and a corpse comes back
only as the scenario says."""

from itertools import pairwise

from inventory_tracking.combat.controller import LiveAim
from inventory_tracking.combat.mechanics.damage import damage_table
from inventory_tracking.combat.policy import Choice, LinePolicy
from inventory_tracking.combat.sim.engine import simulate
from inventory_tracking.combat.sim.situation import MonsterTrack, Situation
from inventory_tracking.macros.view import Viewport

from .harness import ASPECT, MOVE_FRAMES, ORIGIN, Brief, Move, Raiser, Scenario, body, run, today, wall
from .scenarios import CATACOMBS, FALLEN, KNOT, SHAMAN, fallen, shaman


def at_the_first(brief: Brief) -> Choice:
    """A cast straight at the live monster with the lowest unit id."""
    unit = min(brief.seen.foes)
    return Choice(brief.seen.foes[unit].at, unit, 0.0)


def test_without_a_reviver_the_harness_kills_as_the_production_simulator_does():
    scenario = Scenario('plain', CATACOMBS, fallen(*KNOT), seconds=4.0)
    frames = scenario.frames
    tracks = {
        b.unit: MonsterTrack(b.unit, b.txt, b.points, dict.fromkeys(range(frames + 1), b.at)) for b in scenario.bodies
    }
    situation = Situation(0, frames, CATACOMBS, ASPECT, dict.fromkeys(range(frames + 1), ORIGIN), tracks, [], 0.0)
    policy = LiveAim(LinePolicy(yields=True), Viewport(ASPECT).reachable_focal)
    off = {'companions': {}, 'link': (0.0, 0, 0.0), 'explosion': (0.0, 0.0), 'mark': (0.0, 0), 'mana': (0.0, 0.0, 0.0)}
    production = simulate(situation, [], damage_table(), policy=policy, **off)
    result = run(scenario, today())
    assert {unit: died[0] for unit, died in result.deaths.items()} == production.deaths
    assert result.casts == production.casts
    assert result.cleared_at == max(production.deaths.values())
    assert (result.revivals, result.wasted) == (0, 0.0)


def test_a_killed_minion_comes_back_at_full_life_one_period_later_while_the_reviver_lives():
    minion, reviver = body(1, FALLEN, (8.0, 0.0), CATACOMBS), shaman(9, (0.0, 15.0))
    scenario = Scenario('one', CATACOMBS, (minion, reviver), (Raiser(9, 30.0, 20, frozenset({1})),), seconds=4.0)
    result = run(scenario, lambda brief: at_the_first(brief) if 1 in brief.seen.foes else None)
    deaths = result.deaths[1]
    assert len(deaths) >= 3  # killed, raised, killed again: the fight never ends
    assert not result.cleared
    assert result.revivals == len(deaths) - 1  # the last corpse is still waiting for its raise at the end
    assert result.wasted == minion.points * result.revivals
    assert all(later - earlier >= 20 for earlier, later in pairwise(deaths))


def test_a_dead_reviver_raises_nothing_and_a_corpse_out_of_its_range_stays_dead():
    minion, reviver = body(1, FALLEN, (8.0, 0.0), CATACOMBS), shaman(9, (0.0, 15.0))
    both = Scenario('both', CATACOMBS, (reviver, minion), (Raiser(9, 30.0, 20, frozenset({1})),), seconds=6.0)

    def reviver_first(brief: Brief) -> Choice:
        unit = max(brief.seen.foes)
        return Choice(brief.seen.foes[unit].at, unit, 0.0)

    result = run(both, reviver_first)
    assert result.cleared
    assert result.revivals == 0
    short = Scenario('short', CATACOMBS, (minion, reviver), (Raiser(9, 10.0, 20, frozenset({1})),), seconds=2.0)
    result = run(short, lambda brief: at_the_first(brief) if 1 in brief.seen.foes else None)
    assert (len(result.deaths[1]), result.revivals) == (1, 0)
    assert result.alive == (9,)


def test_a_wall_stops_the_blades_and_a_move_takes_the_character_past_it():
    target = shaman(9, (12.0, 0.0))
    scenario = Scenario('walled', CATACOMBS, (target,), blocked=wall(5.0, -6.0, 6.5, 6.0), seconds=4.0)
    result = run(scenario, at_the_first)
    assert not result.cleared
    assert result.taken == 0.0
    moved = iter([Move((ORIGIN[0] + 12.0, ORIGIN[1] + 10.0))])
    result = run(scenario, lambda brief: next(moved, None) or at_the_first(brief))
    assert result.cleared
    assert result.moves == 1
    assert result.deaths[9][0] > MOVE_FRAMES  # nothing is cast during the move


def test_the_reviver_rate_and_range_of_a_scenario_are_the_table_rows():
    from .scenarios import BY_NAME

    raiser = BY_NAME['shaman_out_of_reach'].raisers[0]
    assert (raiser.range, raiser.period) == (SHAMAN['raise_range'], SHAMAN['raise_frames'])
