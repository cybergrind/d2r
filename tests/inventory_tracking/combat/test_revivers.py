"""The reviver table and rules (combat/revivers.py): what the game's tables give, who raises whom, and what the strike's
lines make of it with REVIVERS_FIRST on."""

from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock.echoing_strike.attack import EchoingStrike
from inventory_tracking.combat import revivers
from inventory_tracking.combat.policy import Foe, Observation
from inventory_tracking.game.layout import CHAMPION_FLAG, MINION_FLAG, UNIQUE_FLAG
from tests.inventory_tracking.scenarios.revivers.table import raised, reviver


SHAMAN = reviver('fallenshaman1')['txt']
FALLEN = raised('FallenShaman')['fallen1']
UNRAVELER = reviver('unraveler3')['txt']
BURNING_DEAD = raised('GreaterMummy')['skeleton4']


@pytest.fixture
def first(monkeypatch):
    monkeypatch.setattr(revivers, 'REVIVERS_FIRST', True)


def test_the_table_is_what_the_dumped_game_tables_give():
    if not (revivers.EXCEL / 'monstats.txt').exists():
        pytest.skip('the excel dump (pricing/raw/game-excel) is not on this machine')
    import json

    assert revivers.build() == json.loads(revivers.FILE.read_text(encoding='utf-8'))


def test_the_three_families_and_what_they_raise():
    table = revivers.revivers()
    assert {r.ai for r in table.values()} == {'FallenShaman', 'GreaterMummy', 'FetishShaman'}
    assert {FALLEN, SHAMAN} <= table[SHAMAN].raises  # the shamans raise each other too
    assert BURNING_DEAD in table[UNRAVELER].raises
    assert UNRAVELER not in table[UNRAVELER].raises  # high undead: not raised
    assert all(r.range > 22 and r.seconds > 0 for r in table.values())


def test_switched_off_nobody_is_raising(monkeypatch):
    monkeypatch.setattr(revivers, 'REVIVERS_FIRST', False)
    assert revivers.raising([(1, SHAMAN, (0.0, 0.0), 0), (2, FALLEN, (3.0, 0.0), 0)]) == {}


def test_a_shaman_raises_the_fallen_in_its_range_and_never_a_unique(first):
    reach = revivers.revivers()[SHAMAN].range + revivers.COVER_MARGIN
    bodies = [
        (1, SHAMAN, (0.0, 0.0), MINION_FLAG),
        (2, FALLEN, (5.0, 0.0), MINION_FLAG),  # a Herald's minion is raised
        (3, FALLEN, (reach + 1.0, 0.0), 0),  # out of its range
        (4, FALLEN, (2.0, 0.0), UNIQUE_FLAG),  # the Herald: never
        (5, FALLEN, (2.0, 1.0), CHAMPION_FLAG),  # a shaman spares a champion
    ]
    assert revivers.raising(bodies) == {1: frozenset({2})}
    assert revivers.weights(bodies) == {1: revivers.REVIVER_WEIGHT, 2: revivers.RAISED_WEIGHT}


def test_a_greater_mummy_raises_champions(first):
    bodies = [(1, UNRAVELER, (0.0, 0.0), 0), (2, BURNING_DEAD, (5.0, 0.0), CHAMPION_FLAG)]
    assert revivers.raising(bodies) == {1: frozenset({2})}


def test_a_lone_reviver_raises_nothing(first):
    assert revivers.raising([(1, SHAMAN, (0.0, 0.0), 0)]) == {}


def test_the_sweep_lays_its_line_through_the_raising_reviver(first):
    # Two lines apart: three Fallen on one, the shaman raising them alone on the other; plain points, the Fallen's
    # line takes more; weighted (combat/policy.py `observe` sets the weights), the shaman's is the one cast
    fallen = [Foe(FALLEN, (12.0, dy), 10_000.0, weight=revivers.RAISED_WEIGHT) for dy in (-0.5, 0.0, 0.5)]
    shaman = Foe(SHAMAN, (0.0, 14.0), 20_000.0, weight=revivers.REVIVER_WEIGHT, raising=True)
    seen = Observation((0.0, 0.0), {1: fallen[0], 2: fallen[1], 3: fallen[2], 4: shaman})
    plain = Observation((0.0, 0.0), {unit: replace(foe, weight=1.0) for unit, foe in seen.foes.items()})
    swept = EchoingStrike().choose(plain)
    assert swept is not None
    assert swept.unit in {1, 2, 3}
    chosen = EchoingStrike().choose(seen)
    assert chosen is not None
    assert chosen.unit == 4
