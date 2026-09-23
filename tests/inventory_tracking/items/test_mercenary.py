import json
from pathlib import Path

import pytest

from inventory_tracking.items.decode import decode_items
from inventory_tracking.native.layout import HIRELING_CLASS_ID
from inventory_tracking.tracking.state import select_player


def capture():
    saved = json.loads((Path(__file__).parents[1] / 'fixtures/insight_bill.json').read_text())
    snapshot = saved['snapshot']
    player_id, _ = select_player(snapshot['groups']['players']['units'])
    snapshot['groups']['monsters'] = {
        'complete': True,
        'units': [
            {
                'unit_id': 123456,
                'type': 1,
                'txt_id': HIRELING_CLASS_ID,
                'identity_stable': True,
                'details': {'monster_data_u32': [0] * 21 + [player_id]},
            }
        ],
    }
    row = snapshot['resources']['items'][0]
    row['mode'] = 1
    row['details'].update(owner_id=0xFFFFFFFF, inventory_page=255)
    return saved


def decode(saved):
    return decode_items(
        saved['snapshot'], saved['report'], inventory_page=255, inventory_owner_id=123456, inventory_owner_type=1
    )


def test_merc_item_retains_item_identity_and_typed_owner():
    result = decode(capture())[0]
    assert result['item']['name'] == 'Insight'
    assert result['source']['container']['name'] == 'Mercenary equipment'
    assert result['source']['owner_id'] == 123456
    assert result['source']['owner_type'] == 1


def test_merc_item_decode_rechecks_local_player_association():
    saved = capture()
    saved['snapshot']['groups']['monsters']['units'][0]['details']['monster_data_u32'][21] += 1
    with pytest.raises(ValueError, match='local mercenary'):
        decode(saved)
