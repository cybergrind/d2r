import copy
from dataclasses import replace
from unittest.mock import Mock

import pytest

from inventory_tracking.automation import Automation
from inventory_tracking.config import MERC_HEALING, PLAYER_HEALING
from inventory_tracking.models import Actor, Outcome
from inventory_tracking.state import from_research


def test_player_first_and_uniform_statuses(healing_setup, sample, clock):
    make, sent = healing_setup
    automation = Automation([make(MERC_HEALING), make(PLAYER_HEALING)])
    result = automation.step(sample())
    assert result[Actor.PLAYER].outcome == Outcome.SENT
    assert result[Actor.MERC].outcome == Outcome.STALE_BELT
    assert automation.events[0].request.actor == Actor.PLAYER
    assert sent.call_count == 1


def test_rejected_input_does_not_create_notification(healing_setup, sample):
    make, _ = healing_setup
    controller = make(PLAYER_HEALING)
    controller.potions.deliver = Mock(return_value=False)
    automation = Automation([controller])
    assert automation.step(sample())[Actor.PLAYER].outcome == Outcome.REJECTED
    assert automation.events == ()


def test_merc_healing_uses_valid_samples_without_menu_detection(snapshot, healing_setup):

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
    make, sent = healing_setup

    def attempt(sample):
        return make(MERC_HEALING).step(from_research(sample))

    attempt(data)
    assert sent.call_args.args[0].item.column == 3
    sent.reset_mock()
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
    sent.assert_not_called()


@pytest.mark.parametrize('target', ['player', 'merc'])
def test_live_belt_switch_to_all_rejuvenations_selects_actual_column(target, snapshot, healing_setup, clock):

    from inventory_tracking.mercenary import Mercenary

    data = snapshot()
    # Healing now occupies column 1; rejuvenations occupy every other column.
    data['groups']['items']['units'][0]['txt_id'] = 606
    initial = from_research(data)
    assert initial.healing_cells == ((1, 100),)
    make, send = healing_setup
    controller = make(PLAYER_HEALING if target == 'player' else MERC_HEALING)

    def injured(sample):
        return replace(sample, current_raw=10, maximum_raw=100, merc=Mercenary(42, 10, 100, 3276, True))

    # Consume the rejuvenation in column 2.
    controller.step(injured(initial))
    assert send.call_args.args[0].item.column == 2
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
    clock.now = 103
    controller.step(injured(updated))
    assert send.call_count == 2
    assert send.call_args.args[0].item.column == 3
