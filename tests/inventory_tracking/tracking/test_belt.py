import pytest

from inventory_tracking.models import PotionType
from inventory_tracking.tracking.belt import column_shortages, column_stock, potion_count, potion_kind


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


def test_column_stock_counts_only_the_requested_kind_in_that_column():
    contents = [531, 606, 606, 606, None, 531, 606, 606, None, None, None, 606, None, None, None, 606]
    assert column_stock(contents, 1, PotionType.REJUVENATION) == 1
    assert column_stock(contents, 2, PotionType.REJUVENATION) == 1
    assert column_stock(contents, 2, PotionType.HEALING) == 1
    assert column_stock(contents, 3, PotionType.HEALING) == 2
    assert column_stock(contents, 4, PotionType.HEALING) == 4
