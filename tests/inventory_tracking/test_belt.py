import pytest

from inventory_tracking.belt import column_shortages, potion_count, potion_kind
from inventory_tracking.models import PotionType


@pytest.mark.parametrize(
    ('class_id', 'kind'),
    [
        (530, PotionType.REJUVENATION),
        (531, PotionType.REJUVENATION),
        (602, PotionType.HEALING),
        (603, PotionType.HEALING),
        (604, PotionType.HEALING),
        (605, PotionType.HEALING),
        (606, PotionType.HEALING),
        (None, None),
        (999, None),
    ],
)
def test_classification_and_family_counts(class_id, kind):
    assert potion_kind(class_id) == kind
    if kind:
        assert potion_count([class_id, None, class_id], kind) == 2


def test_unrecognized_column_target_does_not_request_health_or_rejuvenation():
    assert column_shortages([999, 531, 606, 531] + [None, 531, 606, 531] * 3) == (0, 0)
