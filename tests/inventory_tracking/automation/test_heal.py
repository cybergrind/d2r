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
        (MERC_HEALING, 50, [PotionType.HEALING]),
        (MERC_HEALING, 49, [PotionType.REJUVENATION, PotionType.HEALING]),
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


def test_invalid_sample_does_not_reset_suspension(sample, healing_setup, clock):
    make, sent = healing_setup
    controller = make(MERC_HEALING)
    controller.step(sample())
    clock.now = 103
    assert controller.step(sample(103)).outcome == Outcome.SUSPENDED
    assert controller.step(State(sampled_at=103, reason='incomplete read')).outcome == Outcome.UNAVAILABLE
    clock.now = 106
    assert controller.step(sample(106)).outcome == Outcome.SUSPENDED
    assert sent.call_count == 1
