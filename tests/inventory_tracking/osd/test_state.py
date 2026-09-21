"""OSD must never turn unknown or stale inventory into pickup advice."""

import copy
from dataclasses import replace

import pytest

from inventory_tracking.osd.state import State, display_lines, from_research


def snapshot():
    player = {
        'unit_id': 7,
        'details': {'full_stats': [{'layer': 0, 'id': 6, 'raw': 1526 * 256}, {'layer': 0, 'id': 7, 'raw': 1545 * 256}]},
    }
    items = [
        {'unit_id': i + 100, 'txt_id': 531 if i < 5 else 606, 'mode': 2, 'details': {'owner_id': 7, 'x': i, 'y': 0}}
        for i in range(12)
    ]
    return {
        'status': 'research',
        'identity': {'pid': 1, 'start_ticks': '2'},
        'sample_monotonic': 100,
        'groups': {
            name: {'complete': True, 'units': units} for name, units in [('players', [player]), ('items', items)]
        },
    }


def test_health_and_missing_counts_not_remaining_stock():
    state = from_research(snapshot())
    assert display_lines(state, now=101) == ['juv 11']


def test_full_targets_hide_deficit_lines():
    state = from_research(snapshot())
    assert display_lines(state, now=101, rejuvenation_target=5, healing_target=7) == []


def test_health_threshold_includes_exactly_seventy_percent():
    state = replace(
        from_research(snapshot()),
        maximum_raw=1000 * 256,
        current_raw=700 * 256,
        rejuvenations=8,
        healing=8,
        belt_contents=None,
    )
    assert display_lines(state, now=101) == ['700/1000']
    assert display_lines(replace(state, current_raw=700 * 256 + 1), now=101) == []
    assert display_lines(replace(state, current_raw=699 * 256), now=101) == ['699/1000']


def test_stale_and_future_samples_do_not_show_old_health_or_deficits():
    state = from_research(snapshot())
    assert display_lines(state, now=110) == []
    assert display_lines(state, now=99) == []


def test_menu_and_ambiguous_players_are_unavailable():
    data = snapshot()
    data['groups']['players']['units'] = []
    assert from_research(data).reason == 'outside game'
    data = snapshot()
    second = copy.deepcopy(data['groups']['players']['units'][0])
    second['unit_id'] = 8
    data['groups']['players']['units'].append(second)
    assert from_research(data).reason == 'ambiguous player'


def test_incomplete_read_and_duplicate_cells_are_unavailable():
    data = snapshot()
    data['groups']['items']['complete'] = False
    assert from_research(data).reason == 'incomplete read'
    data = snapshot()
    data['groups']['items']['units'][1]['details']['x'] = 0
    assert from_research(data).reason == 'inconsistent belt'


def test_empty_belt_counts_all_missing_but_other_owners_are_not_counted():
    data = snapshot()
    for item in data['groups']['items']['units']:
        item['details']['owner_id'] = 9
    assert display_lines(from_research(data), now=101) == [
        'juv 16',
    ]


def test_duplicate_life_stat_is_rejected():
    data = snapshot()
    stats = data['groups']['players']['units'][0]['details']['full_stats']
    stats.append(stats[0].copy())
    assert from_research(data).current_raw is None


def test_incomplete_read_and_startup_are_quiet():
    assert display_lines(State(100, reason='incomplete read'), now=101) == []
    assert display_lines(State(100, reason='connecting'), now=101) == []


def test_refill_clears_previous_shortage():
    state = replace(from_research(snapshot()), rejuvenations=8, healing=7, belt_contents=None)
    assert display_lines(state, now=101) == ['hp 1']
    assert display_lines(replace(state, healing=8), now=101) == []


def test_heal_uses_only_bottom_healing_potions():
    data = snapshot()
    items = data['groups']['items']['units']
    items[2]['txt_id'] = 602
    items[3]['txt_id'] = 605
    assert from_research(data).healing_cells == ((3, 102), (4, 103))
    items[2]['txt_id'] = 531
    items[3]['mode'] = 0
    assert from_research(data).healing_cells == ()


def test_merc_healing_uses_valid_samples_without_menu_detection():
    from inventory_tracking.merc_heal import MercHealController

    data = snapshot()
    data['gameplay_ready'] = False  # Old UI offsets are invalid for this build.
    data['groups']['items']['units'][2]['txt_id'] = 606
    data['groups']['monsters'] = {
        'complete': True,
        'units': [
            {
                'unit_id': 42,
                'txt_id': 338,
                'mode': 1,
                'details': {
                    'monster_data_u32': [0] * 21 + [7],
                    'full_stats': [
                        {'layer': 0, 'id': 6, 'raw': 16384},
                        {'layer': 0, 'id': 7, 'raw': 2090 * 256},
                    ],
                },
            }
        ],
    }
    sent = []

    def attempt(sample):
        MercHealController().step(from_research(sample), 100.1, lambda state, column: sent.append(column))

    attempt(data)
    assert sent == [3]
    sent.clear()
    for change in ('incomplete', 'identity', 'dead_player', 'dead_merc'):
        invalid = copy.deepcopy(data)
        if change == 'incomplete':
            invalid['groups']['monsters']['complete'] = False
        elif change == 'identity':
            invalid.pop('identity')
        elif change == 'dead_player':
            invalid['groups']['players']['units'][0]['details']['full_stats'][0]['raw'] = 0
        else:
            invalid['groups']['monsters']['units'][0]['mode'] = 12
        attempt(invalid)
    assert sent == []


def test_rejuvenation_requires_bottom_cell_and_player_can_heal_without_merc():
    data = snapshot()
    data['groups']['items']['units'][0]['txt_id'] = 530
    state = from_research(data)
    assert state.gameplay_ready
    assert state.merc is None
    assert state.rejuvenation_cells == ((1, 100), (2, 101), (3, 102), (4, 103))
    data['groups']['items']['units'][0]['mode'] = 0
    data['groups']['items']['units'][1]['txt_id'] = 606
    assert from_research(data).rejuvenation_cells == ((3, 102), (4, 103))


@pytest.mark.parametrize('target', ['player', 'merc'])
def test_live_belt_switch_to_all_rejuvenations_selects_actual_column(target):
    from unittest.mock import Mock

    from inventory_tracking.merc_heal import MercHealController
    from inventory_tracking.mercenary import Mercenary

    data = snapshot()
    # Healing now occupies column 1; rejuvenations occupy every other column.
    data['groups']['items']['units'][0]['txt_id'] = 606
    initial = from_research(data)
    assert initial.healing_cells == ((1, 100),)
    controller = MercHealController(target)
    send = Mock(return_value=True)

    def injured(sample):
        return replace(sample, current_raw=10, maximum_raw=100, merc=Mercenary(42, 10, 100, 3276, True))

    # Consume the rejuvenation in column 2.
    controller.step(injured(initial), 100, send)
    assert send.call_args.args[1] == 2
    # Belt is switched entirely to rejuvenations. First two bottom cells empty;
    # potions above them cannot be used. Column 3 is the first usable potion.
    data['sample_monotonic'] = 103
    items = data['groups']['items']['units']
    data['groups']['items']['units'] = items[2:]
    for item in data['groups']['items']['units']:
        item['txt_id'] = 531
    updated = from_research(data)
    assert updated.healing_cells == ()
    assert updated.rejuvenation_cells == ((3, 102), (4, 103))
    controller.step(injured(updated), 103, send)
    assert send.call_count == 2
    assert send.call_args.args[1] == 3


@pytest.mark.parametrize('class_id', [530, 531, 602, 603, 604, 605, 606])
def test_potion_type_detected_in_every_bottom_column(class_id):
    data = snapshot()
    for item in data['groups']['items']['units']:
        item['txt_id'] = class_id
    state = from_research(data)
    expected = tuple((i + 1, i + 100) for i in range(4))
    assert state.rejuvenation_cells == (expected if class_id in (530, 531) else ())
    assert state.healing_cells == (() if class_id in (530, 531) else expected)


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
def test_dynamic_shortages_follow_column_bottom_or_empty_default(contents, expected):
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

    state = State(100, 1000, 1000, 8, 8, merc=Mercenary(42, 256000 * fraction // 32768, 256000, fraction, True))
    lines = display_lines(state, now=100)
    assert bool(lines) == visible
    if visible:
        assert lines[0].startswith('merc ~')
