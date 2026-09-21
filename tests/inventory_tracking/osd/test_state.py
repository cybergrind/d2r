"""OSD must never turn unknown or stale inventory into pickup advice."""

from dataclasses import replace

import pytest

from inventory_tracking.config import OSD
from inventory_tracking.models import State
from inventory_tracking.osd.state import display_lines
from inventory_tracking.state import from_research


def test_health_and_missing_counts_not_remaining_stock(snapshot):
    state = from_research(snapshot())
    assert display_lines(state, now=101) == ['juv 11']


def test_full_targets_hide_deficit_lines(snapshot):
    state = from_research(snapshot())
    assert display_lines(state, now=101, config=replace(OSD, rejuvenation_target=5, healing_target=7)) == []


def test_health_threshold_includes_exactly_seventy_percent(snapshot):
    state = replace(
        from_research(snapshot()),
        maximum_raw=1000 * 256,
        current_raw=700 * 256,
        belt_contents=(531,) * 16,
    )
    assert display_lines(state, now=101) == ['700/1000']
    assert display_lines(replace(state, current_raw=700 * 256 + 1), now=101) == []
    assert display_lines(replace(state, current_raw=699 * 256), now=101) == ['699/1000']


def test_stale_and_future_samples_do_not_show_old_health_or_deficits(snapshot):
    state = from_research(snapshot())
    assert display_lines(state, now=110) == []
    assert display_lines(state, now=99) == []


def test_empty_belt_counts_all_missing_but_other_owners_are_not_counted(snapshot):
    data = snapshot()
    for item in data['groups']['items']['units']:
        item['details']['owner_id'] = 9
    assert display_lines(from_research(data), now=101) == [
        'juv 16',
    ]


def test_incomplete_read_and_startup_are_quiet():
    assert display_lines(State(100, reason='incomplete read'), now=101) == []
    assert display_lines(State(100, reason='connecting'), now=101) == []


def test_refill_clears_previous_shortage(snapshot):
    state = replace(from_research(snapshot()), belt_contents=(531, 531, 606, 606) * 3 + (531, 531, 606, None))
    assert display_lines(state, now=101) == ['hp 1']
    assert display_lines(replace(state, belt_contents=(531, 531, 606, 606) * 4), now=101) == []


@pytest.mark.parametrize(
    ('contents', 'expected'),
    [
        ([None] * 16, ['juv 16']),
        ([531] * 16, []),
        ([530] * 12 + [None] * 4, ['juv 4']),
        ([602, 531, 606, 531] * 3 + [None] * 4, ['juv 2', 'hp 2']),
        ([None, 531, 531, 531] + [606, 531, 531, 531] * 3, ['hp 1']),
        ([531, None, None, None] + [606, None, None, None] * 3, ['juv 15']),
    ],
)
def test_dynamic_shortages_follow_column_bottom_or_empty_default(contents, expected, snapshot):
    data = snapshot()
    data['groups']['items']['units'] = [
        {'unit_id': i + 100, 'txt_id': item, 'mode': 2, 'details': {'owner_id': 7, 'x': i, 'y': 0}}
        for i, item in enumerate(contents)
        if item is not None
    ]
    assert display_lines(from_research(data), now=101) == expected


@pytest.mark.parametrize(('fraction', 'visible'), [(32768, False), (21300, False), (21299, True)])
def test_merc_health_display_is_strictly_below_65_percent(fraction, visible):
    from inventory_tracking.mercenary import Mercenary

    state = State(100, 1000, 1000, merc=Mercenary(42, 256000 * fraction // 32768, 256000, fraction, True))
    lines = display_lines(state, now=100)
    assert bool(lines) == visible
    if visible:
        assert lines[0].startswith('merc ~')


def test_explicit_targets_count_all_potion_tiers(snapshot):
    data = snapshot()
    for item in data['groups']['items']['units']:
        item['txt_id'] = 530 if item['txt_id'] == 531 else 602
    assert (
        display_lines(from_research(data), now=100, config=replace(OSD, rejuvenation_target=5, healing_target=7)) == []
    )


def test_injected_osd_visibility_and_notification_duration():
    from inventory_tracking.config import OSD
    from inventory_tracking.models import Actor, BeltCell, PotionRequest, PotionSent, PotionType

    event = PotionSent(PotionRequest(Actor.PLAYER, PotionType.HEALING, BeltCell(3, 101)), 100)
    config = replace(OSD, player_health_percent=90, notification_seconds=0.5)
    state = State(100, 800 * 256, 1000 * 256, events=(event,), belt_contents=(531,) * 16)
    assert display_lines(state, now=100.4, config=config) == ['player potion sent (3)', '800/1000']
    assert display_lines(state, now=100.5, config=config) == ['800/1000']
