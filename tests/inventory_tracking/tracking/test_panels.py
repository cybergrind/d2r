from unittest.mock import patch

import pytest

from inventory_tracking.models import ObservationStatus
from inventory_tracking.native.layout import PANEL_FLAGS, UI_PANELS_RVA, UI_PANELS_SIZE
from inventory_tracking.tracking.panels import decode_panels, observe_panels


TOKEN = {'pid': 12, 'start_ticks': 'abc'}
IMAGES = {'identity': TOKEN, 'candidate_base': 0x140000000}
ADDRESS = IMAGES['candidate_base'] + UI_PANELS_RVA
MAPPING = {'start': ADDRESS, 'end': ADDRESS + 4096, 'permissions': 'rw-p', 'path': ''}


def flags(*names):
    raw = bytearray(UI_PANELS_SIZE)
    for name in names:
        raw[PANEL_FLAGS[name]] = 1
    return bytes(raw)


def test_decode_names_the_stash_session_layout():
    # Byte pattern of the 2026-09-23 stash-session attachments: inventory + stash open.
    panels = decode_panels(flags('inventory', 'stash'))
    assert {name for name, open_ in panels.items() if open_} == {'inventory', 'stash'}
    assert decode_panels(bytes(UI_PANELS_SIZE)) == dict.fromkeys(PANEL_FLAGS, False)


@pytest.mark.parametrize(
    ('raw', 'message'),
    [(bytes(UI_PANELS_SIZE - 1), 'Short panel'), (b'\x02' + bytes(UI_PANELS_SIZE - 1), 'Invalid panel')],
)
def test_decode_rejects_short_and_non_boolean_arrays(raw, message):
    with pytest.raises(ValueError, match=message):
        decode_panels(raw)


@pytest.mark.parametrize(
    ('reads', 'expected'),
    [
        ([flags(), flags()], False),
        ([flags('inventory', 'stash'), flags('inventory', 'stash')], True),
        ([flags('stash'), flags()], None),
        ([b'\x05' * UI_PANELS_SIZE], None),
        ([b''], None),
    ],
)
def test_observation_rejects_partial_invalid_and_changing_reads(reads, expected):
    with (
        patch('inventory_tracking.tracking.panels.identity', return_value=TOKEN),
        patch('inventory_tracking.tracking.panels.process_mappings', return_value=[MAPPING]),
        patch('inventory_tracking.tracking.panels.os.open', return_value=9),
        patch('inventory_tracking.tracking.panels.os.close') as close,
        patch('inventory_tracking.tracking.panels.os.pread', side_effect=reads) as read,
    ):
        observation = observe_panels(12, IMAGES)
    assert (None if observation.value is None else observation.value['stash']) is expected
    assert (observation.status == ObservationStatus.UNAVAILABLE) == (expected is None)
    assert all(call.args == (9, UI_PANELS_SIZE, ADDRESS) for call in read.call_args_list)
    close.assert_called_once_with(9)


def test_observation_suppresses_identity_changes():
    with (
        patch('inventory_tracking.tracking.panels.identity', side_effect=[TOKEN, {}]),
        patch('inventory_tracking.tracking.panels.process_mappings', return_value=[MAPPING]),
        patch('inventory_tracking.tracking.panels.os.open', return_value=9),
        patch('inventory_tracking.tracking.panels.os.close'),
        patch('inventory_tracking.tracking.panels.os.pread', return_value=flags()),
    ):
        assert observe_panels(12, IMAGES).status == ObservationStatus.UNAVAILABLE
