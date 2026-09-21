from dataclasses import replace

import pytest

from inventory_tracking.config import PLAYER_HEALING, OSDConfig
from inventory_tracking.models import PotionType


def test_healing_maps_are_complete_validated_and_defensively_copied():
    values = {PotionType.HEALING: 7, PotionType.REJUVENATION: 0.5}
    config = replace(PLAYER_HEALING, cooldowns=values)
    values[PotionType.HEALING] = 99
    assert config.cooldowns[PotionType.HEALING] == 7
    with pytest.raises(TypeError):
        config.cooldowns[PotionType.HEALING] = 99
    with pytest.raises(ValueError, match='every potion'):
        replace(config, cooldowns={PotionType.HEALING: 3})


@pytest.mark.parametrize('value', [0, -1, float('nan'), float('inf')])
def test_invalid_durations_rejected(value):
    with pytest.raises(ValueError, match='sample_max_age'):
        replace(PLAYER_HEALING, sample_max_age=value)
    with pytest.raises(ValueError, match='notification_seconds'):
        OSDConfig(notification_seconds=value)


def test_threshold_order_and_range_validated():
    with pytest.raises(ValueError, match='must not exceed'):
        replace(PLAYER_HEALING, thresholds={PotionType.HEALING: 30, PotionType.REJUVENATION: 40})
    with pytest.raises(ValueError, match='percentages'):
        replace(PLAYER_HEALING, thresholds={PotionType.HEALING: 101, PotionType.REJUVENATION: 20})
