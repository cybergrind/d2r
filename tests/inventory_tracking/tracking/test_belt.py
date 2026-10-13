import pytest

from inventory_tracking.models import PotionType
from inventory_tracking.tracking.belt import (
    BeltColumns,
    column_shortages,
    column_stock,
    potion_count,
    potion_kind,
    remember,
)


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


# --- an emptied column keeps the kind it last held (rca/2026-10-13/potions-findings.md §2.1, step 1) ---

R, H = PotionType.REJUVENATION, PotionType.HEALING
GAME = ('cs-2', 1770193399)
# Take 20261013T184953Z-108 (Chaos Sanctuary, 21:49:53.71): two rejuvenation columns and two healing ones.
ENTRY = (531, 531, 606, 606, 531, 531, 606, 606, 531, 531, None, 606, None, None, None, None)
# 21:50:13.77, the drinkers have emptied columns 3-4; 21:50:22.17, the rejuvenation picked up in column 1.
DRY = (531, 531, None, None, 531, 531, None, None, 531, 531, None, None, None, None, None, None)
AT_215022 = (531, 531, None, None, 531, 531, None, None, 531, 531, None, None, 531, None, None, None)


def folded(*belts, game=GAME):
    columns = BeltColumns()
    for belt in belts:
        columns = remember(columns, belt, game)
    return columns


def test_the_healing_columns_drunk_dry_still_ask_for_healing():
    # Read alone the belt of 21:50:22.3 wants no healing (the run left two super healing potions 3.6 and
    # 7.3 away); with what its columns held before, both empty columns are healing missing.
    assert column_shortages(AT_215022) == (9, 0)
    columns = folded(ENTRY, DRY, AT_215022)
    assert columns.kinds == (R, R, H, H)
    assert column_shortages(AT_215022, columns) == (1, 8)


def test_a_column_never_seen_filled_is_read_as_rejuvenation():
    # 01:01 on 2026-10-13 ("none the belt has a place for (short (8, 0))"): the service began with columns
    # 1-2 already empty and 3-4 full of healing. Nothing in that game says what 1-2 were for, so they stay
    # rejuvenation and a healing potion is not wanted: the healing columns were full (the log's (8, 5) ->
    # (8, 2) -> (8, 0) over five healing pickups).
    belt = (None, None, 606, 606) * 4
    columns = folded(belt)
    assert columns.kinds == (None, None, H, H)
    assert column_shortages(belt, columns) == (8, 0)


def test_a_new_game_or_another_belt_size_forgets_what_the_columns_held():
    columns = folded(ENTRY, DRY)
    assert remember(columns, DRY, GAME) is columns  # nothing new
    assert remember(columns, DRY, ('cs-3', 1770193399)).kinds == (R, R, None, None)
    assert column_shortages(DRY, remember(columns, DRY, ('cs-3', 1770193399))) == (10, 0)
    assert remember(columns, DRY, GAME, rows=3).kinds == (R, R, None, None)


def test_a_column_takes_the_kind_it_holds_now():
    columns = folded(ENTRY, DRY, (531, 531, 531, None) + (None,) * 12, (None,) * 16)
    assert columns.kinds == (R, R, R, H)
    assert column_shortages((None,) * 16, columns) == (12, 4)


def test_the_configured_layout_wins_over_what_the_columns_held():
    columns = folded(ENTRY, DRY)
    assert column_shortages(DRY, columns, (H, H, R, R)) == (10, 0)
    assert column_shortages(DRY, None, (R, R, H, H)) == (2, 8)
    # A column holding potions is read by them, whatever the layout.
    assert column_shortages(ENTRY, None, (H, H, H, H)) == (2, 3)
