from dataclasses import replace

import pytest

from inventory_tracking.mercenary import Mercenary
from inventory_tracking.models import BeltCell, State


@pytest.fixture
def sample():
    def make(now=100, **changes):
        return replace(
            State(
                now,
                500,
                1000,
                player_id=7,
                process_id=1,
                process_start='2',
                merc=Mercenary(99, 500, 1000, 16384, True),
                healing_cells=(BeltCell(3, 101), BeltCell(4, 102)),
                rejuvenation_cells=(BeltCell(1, 103),),
                belt_ids=(101, 102, 103),
                gameplay_ready=True,
            ),
            **changes,
        )

    return make


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

    from inventory_tracking.heal import HealController
    from inventory_tracking.potion_ledger import PotionLedger
    from inventory_tracking.potions import PotionsController

    sent = Mock()

    def deliver(state, request, *, max_age, before_send):
        before_send()
        sent(request)
        return True

    def make(config):
        return HealController(
            config, PotionsController(config, PotionLedger(tmp_path, boot_id='test'), deliver, clock=clock)
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
