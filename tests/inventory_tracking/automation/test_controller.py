import copy
from dataclasses import replace

import pytest

from inventory_tracking.automation.controller import Automation
from inventory_tracking.config import MERC_HEALING, PLAYER_HEALING
from inventory_tracking.models import Actor, Outcome, Refusal
from inventory_tracking.tracking.state import from_research
from tests.inventory_tracking.conftest import belt_of
from tests.inventory_tracking.input.fakes import FakeDelivery


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
    controller.potions.delivery = FakeDelivery(refusal=Refusal.UNFOCUSED)
    automation = Automation([controller])
    assert automation.step(sample())[Actor.PLAYER].outcome == Outcome.REJECTED
    assert automation.events == ()


def test_merc_healing_uses_valid_samples_without_menu_detection(snapshot, healing_setup):

    data = snapshot()
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

    from inventory_tracking.models import PlayerHealth
    from inventory_tracking.native.mercenary import Mercenary

    data = snapshot()
    # Healing now occupies column 1; rejuvenations occupy every other column.
    data['groups']['items']['units'][0]['txt_id'] = 606
    initial = from_research(data)
    assert belt_of(initial).healing_cells == ((1, 100),)
    make, send = healing_setup
    controller = make(PLAYER_HEALING if target == 'player' else MERC_HEALING)

    def injured(sample):
        return replace(sample, health=PlayerHealth(10, 100), merc=Mercenary(42, 10, 100, 3276, True))

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
    assert belt_of(updated).healing_cells == ()
    assert belt_of(updated).rejuvenation_cells == ((3, 102), (4, 103))
    clock.now = 103
    controller.step(injured(updated))
    assert send.call_count == 2
    assert send.call_args.args[0].item.column == 3


def test_core_identity_change_clears_events_but_missing_merc_does_not(healing_setup, sample, clock):
    from inventory_tracking.models import SessionIdentity

    make, _ = healing_setup
    automation = Automation([make(PLAYER_HEALING)])
    automation.step(sample())
    assert automation.events
    clock.now = 100.1
    automation.step(sample(100.1, merc=None))
    automation.step(sample(100.2, reason='incomplete read', session=None))
    assert automation.events
    clock.now = 100.3
    automation.step(sample(100.3, session=SessionIdentity(1, '2', 8)))
    assert automation.events == ()


def test_new_player_publishes_empty_events_through_reader(tmp_path, healing_setup, sample, clock):
    from inventory_tracking.models import SessionIdentity
    from inventory_tracking.tracking.reader import LiveReader

    make, _ = healing_setup
    automation = Automation([make(PLAYER_HEALING)])
    reader = LiveReader(tmp_path, automation=automation)
    automation.step(sample())
    reader.set_state(sample())
    assert reader.latest().events
    clock.now = 100.5
    changed = sample(100.5, session=SessionIdentity(1, '2', 8))
    automation.step(changed)
    reader.set_state(changed)
    assert reader.latest().events == ()
