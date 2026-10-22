"""A hostile's life for the decisions (combat/mechanics/life.py): rank and Herald tier on the type's points."""

import pytest

from inventory_tracking.combat.mechanics import life
from inventory_tracking.combat.mechanics.tables import points_of, tables
from inventory_tracking.game.layout import CHAMPION_FLAG, MINION_FLAG, SUPER_FLAG, UNIQUE_FLAG
from inventory_tracking.macros.rotation import ELITE_LIFE


BRAMBLE_HULK, GREAT_MARSH = 128, 77  # the tier 5 pack of 2026-10-21 09:30:41 (rca/2026-10-21/herald-fight-findings.md)


def test_the_rank_factor_is_the_one_the_readers_used() -> None:
    assert life.RANK_LIFE == ELITE_LIFE


def test_a_plain_monster_has_its_types_points() -> None:
    assert life.full_points(BRAMBLE_HULK, GREAT_MARSH) == points_of(BRAMBLE_HULK, GREAT_MARSH)


@pytest.mark.parametrize('flags', [UNIQUE_FLAG, CHAMPION_FLAG, SUPER_FLAG, UNIQUE_FLAG | SUPER_FLAG])
def test_a_leader_has_twice_its_types_points(flags: int) -> None:
    assert life.full_points(BRAMBLE_HULK, GREAT_MARSH, flags) == 2 * points_of(BRAMBLE_HULK, GREAT_MARSH)


def test_a_minion_is_no_leader() -> None:
    assert life.full_points(BRAMBLE_HULK, GREAT_MARSH, MINION_FLAG) == points_of(BRAMBLE_HULK, GREAT_MARSH)


def test_a_tier_5_herald_and_its_minions_carry_the_terror_zones_life_boost() -> None:
    plain = points_of(BRAMBLE_HULK, GREAT_MARSH)
    boost = tables()['heralds']['5']
    assert (boost['life'], boost['minion_life']) == (2000, 750)
    assert life.full_points(BRAMBLE_HULK, GREAT_MARSH, UNIQUE_FLAG, 5) == pytest.approx(plain * 2 * 21)
    assert life.full_points(BRAMBLE_HULK, GREAT_MARSH, MINION_FLAG, 5) == pytest.approx(plain * 8.5)


def test_every_tier_raises_life_and_a_tier_the_config_lacks_raises_nothing() -> None:
    lives = [life.full_points(BRAMBLE_HULK, GREAT_MARSH, MINION_FLAG, tier) for tier in range(6)]
    assert lives == sorted(lives)
    assert len(set(lives)) == 6
    assert life.tier_boost(MINION_FLAG, 9) == 1.0


def test_the_decisions_get_the_tier_and_the_readers_add_the_rank() -> None:
    plain = points_of(BRAMBLE_HULK, GREAT_MARSH)
    boost = life.tier_boost(UNIQUE_FLAG, 5)
    assert not life.RANK_POINTS  # off: the rank moved 115 golden aims and stands (combat/mechanics/life.py)
    assert life.foe_points(BRAMBLE_HULK, GREAT_MARSH, UNIQUE_FLAG, 5) == pytest.approx(plain * boost)
    assert life.foe_points(BRAMBLE_HULK, GREAT_MARSH, UNIQUE_FLAG) == plain
    assert life.rank_share(True) == ELITE_LIFE
    assert life.rank_share(False) == 1.0


def test_with_the_rank_in_the_points_the_readers_add_nothing(monkeypatch) -> None:
    monkeypatch.setattr(life, 'RANK_POINTS', True)
    plain = points_of(BRAMBLE_HULK, GREAT_MARSH)
    assert life.foe_points(BRAMBLE_HULK, GREAT_MARSH, UNIQUE_FLAG, 5) == pytest.approx(
        life.full_points(BRAMBLE_HULK, GREAT_MARSH, UNIQUE_FLAG, 5)
    )
    assert life.foe_points(BRAMBLE_HULK, GREAT_MARSH, UNIQUE_FLAG) == 2 * plain
    assert life.rank_share(True) == 1.0


def test_with_the_tier_off_the_decisions_get_the_plain_points(monkeypatch) -> None:
    monkeypatch.setattr(life, 'TIER_LIFE', False)
    plain = points_of(BRAMBLE_HULK, GREAT_MARSH)
    assert life.foe_points(BRAMBLE_HULK, GREAT_MARSH, UNIQUE_FLAG, 5) == plain
    assert life.foe_points(BRAMBLE_HULK, GREAT_MARSH, MINION_FLAG, 5) == plain
