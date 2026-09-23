from unittest.mock import patch

import pytest

from inventory_tracking.models import ObservationStatus
from inventory_tracking.native.layout import SHOW_ITEMS_RVA
from inventory_tracking.tracking.show_items import observe_show_items


TOKEN = {'pid': 12, 'start_ticks': 'abc'}
IMAGES = {'identity': TOKEN, 'candidate_base': 0x140000000}
ADDRESS = IMAGES['candidate_base'] + SHOW_ITEMS_RVA
MAPPING = {'start': ADDRESS, 'end': ADDRESS + 4096, 'permissions': 'rw-p', 'path': ''}


@pytest.mark.parametrize(
    ('reads', 'expected'),
    [
        ([b'\x00', b'\x00'], False),
        ([b'\x01', b'\x01'], True),
        ([b'\x00', b'\x01'], None),
        ([b'\x02'], None),
        ([b''], None),
    ],
)
def test_label_observation_rejects_partial_invalid_and_changing_reads(reads, expected):
    with (
        patch('inventory_tracking.tracking.show_items.identity', return_value=TOKEN),
        patch('inventory_tracking.tracking.show_items.process_mappings', return_value=[MAPPING]),
        patch('inventory_tracking.tracking.show_items.os.open', return_value=9),
        patch('inventory_tracking.tracking.show_items.os.close') as close,
        patch('inventory_tracking.tracking.show_items.os.pread', side_effect=reads) as read,
    ):
        observation = observe_show_items(12, IMAGES)
    assert observation.value is expected
    assert (observation.status == ObservationStatus.UNAVAILABLE) == (expected is None)
    assert all(call.args == (9, 1, ADDRESS) for call in read.call_args_list)
    close.assert_called_once_with(9)


@pytest.mark.parametrize('change', ['identity', 'mapping', 'access'])
def test_label_observation_suppresses_process_mapping_and_access_failures(change):
    with (
        patch(
            'inventory_tracking.tracking.show_items.identity',
            side_effect=[TOKEN, {}] if change == 'identity' else [TOKEN, TOKEN],
        ),
        patch(
            'inventory_tracking.tracking.show_items.process_mappings',
            side_effect=[[MAPPING], []] if change == 'mapping' else [[MAPPING], [MAPPING]],
        ),
        patch('inventory_tracking.tracking.show_items.os.open', return_value=9),
        patch('inventory_tracking.tracking.show_items.os.close'),
        patch(
            'inventory_tracking.tracking.show_items.os.pread',
            side_effect=PermissionError('denied') if change == 'access' else None,
            return_value=b'\x00',
        ),
    ):
        assert observe_show_items(12, IMAGES).status == ObservationStatus.UNAVAILABLE
