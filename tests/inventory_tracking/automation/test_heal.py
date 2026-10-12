from dataclasses import replace
from unittest.mock import Mock

import pytest

from inventory_tracking.automation.heal import HealController
from inventory_tracking.config import MERC_HEALING, PLAYER_HEALING, with_overrides
from inventory_tracking.models import Outcome, PotionType, State
from inventory_tracking.native.mercenary import Mercenary


@pytest.mark.parametrize(
    ('config', 'percent', 'choices'),
    [
        (PLAYER_HEALING, 65, []),
        (PLAYER_HEALING, 64, [PotionType.HEALING]),
        (PLAYER_HEALING, 40, [PotionType.HEALING]),
        (PLAYER_HEALING, 39, [PotionType.REJUVENATION, PotionType.HEALING]),
        (MERC_HEALING, 75, []),
        (MERC_HEALING, 74, [PotionType.HEALING]),
        (MERC_HEALING, 65, [PotionType.HEALING]),
        (MERC_HEALING, 64, [PotionType.REJUVENATION, PotionType.HEALING]),
    ],
)
def test_threshold_boundaries_and_priority(config, percent, choices, sample):
    state = sample(
        current_raw=percent * 100,
        maximum_raw=10000,
        merc=Mercenary(99, percent * 100, 10000, (percent * 32768 + 99) // 100, True),
    )
    potions = Mock(config=config)
    HealController(config, potions).step(state)
    potions.step.assert_called_once_with(state, choices)


def stepped(config, sample, readings):
    """The choices at each (time, percent of life) reading, one controller through them all."""
    potions = Mock(config=config)
    controller = HealController(config, potions)
    for at, percent in readings:
        merc = Mercenary(99, percent * 100, 10000, (percent * 32768 + 99) // 100, True)
        controller.step(sample(at, current_raw=percent * 100, maximum_raw=10000, merc=merc))
    return [call.args[1] for call in potions.step.call_args_list]


BURST = [PotionType.REJUVENATION, PotionType.HEALING]


def test_a_third_of_the_life_lost_within_a_second_asks_for_a_rejuvenation_whatever_is_left(sample):
    # user, 2026-10-12: "for `make osd` 30% life -- sounds right": the burst, not the level, is the alarm.
    assert stepped(PLAYER_HEALING, sample, [(100.0, 100), (100.5, 70)]) == [[], BURST]
    assert stepped(PLAYER_HEALING, sample, [(100.0, 100), (100.4, 90), (100.9, 70)]) == [[], [], BURST]


def test_a_smaller_or_a_slower_loss_is_no_burst(sample):
    assert stepped(PLAYER_HEALING, sample, [(100.0, 100), (100.5, 71)]) == [[], []]
    assert stepped(PLAYER_HEALING, sample, [(100.0, 100), (100.6, 85), (101.2, 70)]) == [[], [], []]


def test_the_burst_is_counted_from_the_most_life_of_the_last_second_so_a_refill_starts_it_anew(sample):
    readings = [(100.0, 100), (100.3, 70), (100.4, 100), (100.6, 80)]
    assert stepped(PLAYER_HEALING, sample, readings) == [[], BURST, [], []]


def test_the_mercenary_has_no_burst_rule_and_another_game_forgets_the_life_before(sample):
    assert stepped(MERC_HEALING, sample, [(100.0, 100), (100.5, 76)])[-1] == []
    potions = Mock(config=PLAYER_HEALING)
    controller = HealController(PLAYER_HEALING, potions)
    controller.step(sample(100.0, current_raw=10000, maximum_raw=10000))
    other = sample(100.5, current_raw=6900, maximum_raw=10000)
    controller.step(replace(other, session=None))  # out of the game between the two
    controller.step(other)
    assert potions.step.call_args_list[-1].args[1] == []


@pytest.mark.parametrize(
    'changes',
    [
        {'merc': None},
        {'merc': Mercenary(99, 0, 1000, 0, False)},
        {'merc': Mercenary(99, 500, 1000, 16384, False)},
        {'merc': Mercenary(99, 750, 1000, 24576, True)},
        {'session': None},
        {'current_raw': 0},
        {'healing_cells': ()},
        {'sampled_at': 90},
        {'sampled_at': 101},
    ],
)
def test_unknown_dead_threshold_empty_or_stale_never_sends(changes, sample, healing_setup):
    make, sent = healing_setup
    make(MERC_HEALING).step(sample(**changes))
    sent.assert_not_called()


def test_emergency_healing_fallback_and_player_without_merc(sample, healing_setup):
    make, sent = healing_setup
    assert make(PLAYER_HEALING).step(sample(current_raw=300, rejuvenation_cells=(), merc=None)).outcome == Outcome.SENT
    assert sent.call_args.args[0].potion == PotionType.HEALING


def test_dead_player_never_receives_potion(sample, healing_setup):
    make, sent = healing_setup
    make(PLAYER_HEALING).step(sample(current_raw=0))
    sent.assert_not_called()


def test_disabled_actor_never_sends(sample, healing_setup):
    make, sent = healing_setup
    assert make(with_overrides(PLAYER_HEALING, enabled=False)).step(sample()).outcome == Outcome.DISABLED
    sent.assert_not_called()


def test_invalid_sample_does_not_reset_backoff(sample, healing_setup, clock):
    make, sent = healing_setup
    controller = make(MERC_HEALING)
    controller.step(sample())
    clock.now = 103
    assert controller.step(sample(103)).outcome == Outcome.BACKOFF  # retry at 105
    assert controller.step(State(sampled_at=103, reason='incomplete read')).outcome == Outcome.UNAVAILABLE
    clock.now = 104
    assert controller.step(sample(104)).outcome == Outcome.BACKOFF
    clock.now = 105
    assert controller.step(sample(105)).outcome == Outcome.SENT
    assert sent.call_count == 2
