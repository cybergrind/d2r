"""The pure part of survival: the pressure read from the life's history, and the potion asked for."""

import pytest

from inventory_tracking.combat.survival import CALM, DrinkSettings, Pressure, Reading, Supply, drink, pressure
from inventory_tracking.config import with_overrides
from inventory_tracking.models import PotionType


HEALING, REJUVENATION = PotionType.HEALING, PotionType.REJUVENATION
MARKS = DrinkSettings()
BELT = Supply(healing=8, rejuvenation=4)


def lives(*shares: float, step: float = 0.5, most: float = 1000.0) -> list[Reading]:
    return [Reading(index * step, share * most, most) for index, share in enumerate(shares)]


def felt(share: float, lost: float = 0.0, rate: float = 0.0) -> Pressure:
    return Pressure(share, lost, rate, lost)


def test_no_reading_or_only_unread_ones_is_calm():
    assert pressure([]) == CALM
    assert pressure([Reading(0.0, 0.0, 0.0), Reading(0.5, 500.0, 0.0)]) == CALM


def test_the_drops_of_the_window_are_summed_and_what_a_potion_gave_back_is_not_taken_off():
    found = pressure(lives(1.0, 0.8, 1.0, 0.7))
    assert found.share == pytest.approx(0.7)
    assert found.lost == pytest.approx(0.5)
    assert found.rate == pytest.approx(0.5 / 1.5)
    assert found.sustained


def test_what_is_older_than_the_window_does_not_count():
    found = pressure(lives(1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5))  # the drop is 4.5 s old
    assert (found.share, found.lost, found.sustained) == (0.5, 0.0, False)


def test_the_burst_is_the_most_lost_within_a_second():
    found = pressure(lives(1.0, 0.9, 0.6, 0.6, 0.6, 0.5))
    assert found.burst == pytest.approx(0.4)
    assert found.lost == pytest.approx(0.5)


def test_a_weapon_swap_moves_the_share_and_is_no_loss():
    readings = [Reading(0.0, 1783.0, 1783.0), Reading(0.5, 1783.0, 1818.0), Reading(1.0, 1783.0, 1818.0)]
    found = pressure(readings)
    assert found.lost == 0.0
    assert found.share == pytest.approx(1783 / 1818)


@pytest.mark.parametrize(
    ('now', 'expected'),
    [
        (felt(0.95, 0.05, 0.05), None),  # above the mark
        (felt(0.89, 0.05, 0.05), HEALING),  # under it, and life is being lost
        (felt(0.89), None),  # under it and nothing adds to it: left to mend
        (felt(0.74), HEALING),  # low enough to drink whatever happens
    ],
)
def test_a_healing_potion_under_the_mark_while_life_is_lost_or_well_under_it_anyway(now, expected):
    assert drink(now, BELT, {}, MARKS) == expected


def test_a_healing_potion_is_given_its_time_and_less_of_it_when_the_life_is_low():
    assert drink(felt(0.8, 0.1, 0.05), BELT, {HEALING: 5.9}, MARKS) is None
    assert drink(felt(0.8, 0.1, 0.05), BELT, {HEALING: 6.0}, MARKS) == HEALING
    assert drink(felt(0.6, 0.1, 0.05), BELT, {HEALING: 2.4}, MARKS) is None
    assert drink(felt(0.6, 0.1, 0.05), BELT, {HEALING: 2.5}, MARKS) == HEALING


def test_the_last_healing_potions_are_kept_for_low_life_unless_more_lie_near():
    few = Supply(healing=2, rejuvenation=0)
    assert drink(felt(0.8, 0.1, 0.05), few, {}, MARKS) is None
    assert drink(felt(0.8, 0.1, 0.05), Supply(healing=2, healing_near=1), {}, MARKS) == HEALING
    assert drink(felt(0.6, 0.1, 0.05), few, {}, MARKS) == HEALING
    assert drink(felt(0.6, 0.1, 0.05), Supply(), {}, MARKS) is None  # nothing to drink


def test_a_rejuvenation_when_the_loss_played_ahead_takes_the_life_under_the_danger_mark():
    # 50% now, 20% a second lost: 20% in a second and a half
    assert drink(felt(0.5, 0.4, 0.2), BELT, {}, MARKS) == REJUVENATION
    assert drink(felt(0.5, 0.1, 0.05), BELT, {}, MARKS) == HEALING  # 42.5% ahead: no rejuvenation yet
    assert drink(felt(0.6, 0.4, 0.3), BELT, {}, MARKS) == HEALING  # above the rejuvenation mark still
    assert drink(felt(0.5), BELT, {}, MARKS) == HEALING  # low, and nothing is being lost


def test_a_rejuvenation_is_not_drunk_twice_within_its_gap_and_a_healing_potion_stands_in_for_none():
    assert drink(felt(0.5, 0.4, 0.2), BELT, {REJUVENATION: 0.5}, MARKS) == HEALING
    assert drink(felt(0.5, 0.4, 0.2), BELT, {REJUVENATION: 0.5, HEALING: 1.0}, MARKS) is None
    assert drink(felt(0.5, 0.4, 0.2), Supply(healing=3), {HEALING: 2.5}, MARKS) == HEALING


def test_a_build_may_turn_the_drinking_off_or_move_a_mark():
    assert drink(felt(0.3, 0.4, 0.2), BELT, {}, with_overrides(MARKS, enabled=False)) is None
    assert drink(felt(0.92, 0.05, 0.05), BELT, {}, with_overrides(MARKS, healing_below=95.0)) == HEALING
