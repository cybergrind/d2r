import copy

import pytest

from inventory_tracking.state import from_research


def test_menu_and_ambiguous_players_are_unavailable(snapshot):
    data = snapshot()
    data['groups']['players']['units'] = []
    assert from_research(data).reason == 'outside game'
    data = snapshot()
    second = copy.deepcopy(data['groups']['players']['units'][0])
    second['unit_id'] = 8
    data['groups']['players']['units'].append(second)
    assert from_research(data).reason == 'ambiguous player'


def test_incomplete_read_and_duplicate_cells_are_unavailable(snapshot):
    data = snapshot()
    data['groups']['items']['complete'] = False
    assert from_research(data).reason == 'incomplete read'
    data = snapshot()
    data['groups']['items']['units'][1]['details']['x'] = 0
    assert from_research(data).reason == 'inconsistent belt'


def test_duplicate_life_stat_is_rejected(snapshot):
    data = snapshot()
    stats = data['groups']['players']['units'][0]['details']['full_stats']
    stats.append(stats[0].copy())
    assert from_research(data).current_raw is None


def test_heal_uses_only_bottom_healing_potions(snapshot):
    data = snapshot()
    items = data['groups']['items']['units']
    items[2]['txt_id'] = 602
    items[3]['txt_id'] = 605
    assert from_research(data).healing_cells == ((3, 102), (4, 103))
    items[2]['txt_id'] = 531
    items[3]['mode'] = 0
    assert from_research(data).healing_cells == ()


def test_rejuvenation_requires_bottom_cell_and_player_can_heal_without_merc(snapshot):
    data = snapshot()
    data['groups']['items']['units'][0]['txt_id'] = 530
    state = from_research(data)
    assert state.gameplay_ready
    assert state.merc is None
    assert state.rejuvenation_cells == ((1, 100), (2, 101), (3, 102), (4, 103))
    data['groups']['items']['units'][0]['mode'] = 0
    data['groups']['items']['units'][1]['txt_id'] = 606
    assert from_research(data).rejuvenation_cells == ((3, 102), (4, 103))


@pytest.mark.parametrize('class_id', [530, 531, 602, 603, 604, 605, 606])
def test_potion_type_detected_in_every_bottom_column(class_id, snapshot):
    data = snapshot()
    for item in data['groups']['items']['units']:
        item['txt_id'] = class_id
    state = from_research(data)
    expected = tuple((i + 1, i + 100) for i in range(4))
    assert state.rejuvenation_cells == (expected if class_id in (530, 531) else ())
    assert state.healing_cells == (() if class_id in (530, 531) else expected)
