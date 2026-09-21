import pytest

from inventory_tracking.config import (
    OSD,
    PLAYER_HEALING,
    BeltWidgetConfig,
    NotificationsWidgetConfig,
    PortalWidgetConfig,
    with_overrides,
)
from inventory_tracking.models import PotionType


def test_healing_maps_are_complete_validated_and_defensively_copied():
    values = {PotionType.HEALING: 7, PotionType.REJUVENATION: 0.5}
    config = with_overrides(PLAYER_HEALING, cooldowns=values)
    values[PotionType.HEALING] = 99
    assert config.cooldowns[PotionType.HEALING] == 7
    with pytest.raises(TypeError):
        config.cooldowns[PotionType.HEALING] = 99  # pyrefly: ignore[unsupported-operation]
    with pytest.raises(ValueError, match='every potion'):
        with_overrides(config, cooldowns={PotionType.HEALING: 3})


@pytest.mark.parametrize('value', [0, -1, float('nan'), float('inf')])
def test_invalid_durations_rejected(value):
    with pytest.raises(ValueError, match='sample_max_age'):
        with_overrides(PLAYER_HEALING, sample_max_age=value)
    with pytest.raises(ValueError, match='seconds'):
        NotificationsWidgetConfig(seconds=value)
    with pytest.raises(ValueError, match='max_age'):
        with_overrides(OSD, max_age=value)


def test_threshold_order_and_range_validated():
    with pytest.raises(ValueError, match='must not exceed'):
        with_overrides(PLAYER_HEALING, thresholds={PotionType.HEALING: 30, PotionType.REJUVENATION: 40})
    with pytest.raises(ValueError, match='thresholds'):
        with_overrides(PLAYER_HEALING, thresholds={PotionType.HEALING: 101, PotionType.REJUVENATION: 20})


@pytest.mark.parametrize(
    ('changes', 'message'),
    [
        ({'rejuvenation_target': 17}, 'less than or equal to 16'),
        ({'rejuvenation_target': True}, 'integer'),
        ({'rejuvenation_target': 10, 'healing_target': 7}, 'belt slots'),
        ({'healing_target': -1}, 'greater than or equal to 0'),
    ],
)
def test_belt_targets_must_be_integers_that_fit_the_belt(changes, message):
    with pytest.raises(ValueError, match=message):
        BeltWidgetConfig(**changes)


def test_portal_trigger_must_stay_below_capacity():
    assert PortalWidgetConfig(trigger_remaining=0, capacity=1).trigger_remaining == 0
    with pytest.raises(ValueError, match='capacity'):
        PortalWidgetConfig(trigger_remaining=20, capacity=20)


def test_nested_widget_config_cannot_be_mutated_through_the_parent():
    with pytest.raises(ValueError, match='frozen'):
        OSD.belt.rejuvenation_target = 3  # pyrefly: ignore[read-only]
    with pytest.raises(ValueError, match='frozen'):
        OSD.max_age = 5  # pyrefly: ignore[read-only]
    assert OSD.belt.rejuvenation_target is None


def test_with_overrides_revalidates_and_rejects_unknown_fields():
    changed = with_overrides(OSD, max_age=4, belt=BeltWidgetConfig(healing_target=4))
    assert (changed.max_age, changed.belt.healing_target, OSD.max_age) == (4, 4, 2.0)
    with pytest.raises(ValueError, match='monitor'):
        with_overrides(OSD, monitor=-1)
    with pytest.raises(ValueError, match='Extra inputs'):
        with_overrides(OSD, unknown=1)
