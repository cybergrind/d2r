from dataclasses import replace

import pytest

from inventory_tracking.models import BeltCell, BeltSnapshot, PlayerHealth, SessionIdentity, State
from inventory_tracking.native.mercenary import Mercenary


SESSION = SessionIdentity(1, '2', 7)
HEALING_CELLS = (BeltCell(3, 101), BeltCell(4, 102))
REJUVENATION_CELLS = (BeltCell(1, 103),)


def make_state(
    now=100,
    *,
    current_raw=500,
    maximum_raw=1000,
    belt_contents=(None,) * 16,
    healing_cells=HEALING_CELLS,
    rejuvenation_cells=REJUVENATION_CELLS,
    belt_ids=(101, 102, 103),
    **changes,
):
    """A complete, healthy, in-game sample; flat keywords fill the nested records, others replace fields."""
    return replace(
        State(
            sampled_at=now,
            session=SESSION,
            health=PlayerHealth(current_raw, maximum_raw),
            merc=Mercenary(99, 500, 1000, 16384, True),
            belt=BeltSnapshot(belt_contents, healing_cells, rejuvenation_cells, belt_ids),
        ),
        **changes,
    )


def belt_of(state: State) -> BeltSnapshot:
    assert state.belt is not None
    return state.belt


@pytest.fixture
def sample():
    return make_state


@pytest.fixture
def clock():
    class Clock:
        now = 100.0

        def __call__(self):
            return self.now

    return Clock()


@pytest.fixture
def healing_setup(tmp_path, clock):
    from unittest.mock import Mock

    from inventory_tracking.automation.heal import HealController
    from inventory_tracking.automation.ledger import PotionLedger
    from inventory_tracking.automation.potions import PotionsController

    sent = Mock()

    from tests.inventory_tracking.input.fakes import FakeDelivery

    delivery = FakeDelivery(clock=clock, on_send=sent)

    def make(config):
        return HealController(
            config, PotionsController(config, PotionLedger(tmp_path, boot_id='test'), delivery, clock=clock)
        )

    return make, sent


@pytest.fixture
def snapshot():
    def make():
        player = {
            'unit_id': 7,
            'details': {
                'full_stats': [{'layer': 0, 'id': 6, 'raw': 1526 * 256}, {'layer': 0, 'id': 7, 'raw': 1545 * 256}]
            },
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

    return make
