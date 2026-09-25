import copy
import json
from pathlib import Path

import pytest

from inventory_tracking.items.decode import decode_items


FIXTURES = Path(__file__).parents[1] / 'fixtures'


def decoded(name):
    capture = json.loads((FIXTURES / f'{name}.json').read_text())
    row = capture['snapshot']['resources']['items'][0]
    observation = decode_items(capture['snapshot'], capture['report'], inventory_page=row['details']['inventory_page'])[
        0
    ]
    return observation


@pytest.fixture(scope='session')
def insight():
    """Runeword Insight in a Bill, personal stash (0,6), four filled sockets."""
    return decoded('insight_bill')


@pytest.fixture(scope='session')
def spirit():
    """Runeword Spirit Monarch, equipped slot 5."""
    return decoded('spirit_monarch')


@pytest.fixture(scope='session')
def magic_ring():
    """Magic ring in the main inventory (3,0), no item-data bytes."""
    return decoded('appraisal_ring')


@pytest.fixture(scope='session')
def set_helm(insight):
    """Synthetic set item derived from the Insight observation; only naming fields differ."""
    observation = copy.deepcopy(insight)
    observation['item'].update(
        name="Tal Rasha's Horadric Crest",
        base_name='Death Mask',
        base_code='xsk',
        rarity='set',
        set_name="Tal Rasha's Wrappings",
        sockets=0,
        socket_contents='empty',
        socket_items=[],
    )
    observation['item'].pop('runeword', None)
    observation['decoded_stats'] = [
        {
            'memory_stat': {'layer': 0, 'id': 7, 'raw': 45 * 256},
            'status': 'decoded',
            'name': 'maxhp',
            'text': '+45 to Life',
            'value': 45,
            'label': '+{{value}} to Life',
        }
    ]
    observation['unresolved_stats'] = []
    observation['source']['item_identity'] = {'table': 'set', 'table_id': 66, 'offset': 52}
    observation['source']['container'] = {'page': 4, 'name': 'Shared stash'}
    observation['source']['position'] = [2, 3]
    return observation
