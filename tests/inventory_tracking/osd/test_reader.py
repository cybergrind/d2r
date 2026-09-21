"""Potion feedback reflects successful key sends and survives subsequent samples."""

from unittest.mock import Mock, patch

import pytest

from inventory_tracking.osd.reader import LiveReader
from inventory_tracking.osd.state import State, display_lines


@pytest.mark.parametrize('column', [3, 4])
def test_successful_potion_send_shows_for_one_second_across_samples(tmp_path, column):
    reader = LiveReader(tmp_path)
    reader.send = Mock(return_value=True)
    with patch('inventory_tracking.osd.reader.time.monotonic', return_value=100):
        assert reader.send_potion(State(99.9), column)
    expected = [f'merc potion sent (Shift+{column})']
    assert display_lines(reader.latest(), now=100) == expected
    reader.set_state(State(100.5, reason='incomplete read'))
    assert display_lines(reader.latest(), now=100.999) == expected
    assert display_lines(reader.latest(), now=101) == []


def test_failed_or_rejected_input_does_not_show_potion_message(tmp_path):
    reader = LiveReader(tmp_path)
    reader.send = Mock(return_value=False)
    assert not reader.send_potion(State(100), 3)
    assert reader.latest().merc_potion_sent is None
    reader.send.side_effect = OSError('input failed')
    with pytest.raises(OSError, match='input failed'):
        reader.send_potion(State(100), 3)
    assert reader.latest().merc_potion_sent is None


def test_unsupported_build_never_starts_layout_reads(tmp_path):
    reader = LiveReader(tmp_path)
    with (
        patch('inventory_tracking.osd.reader.select_game_process', return_value=12),
        patch(
            'inventory_tracking.osd.reader.inspect_game',
            return_value={
                'memory_access': True,
                'executable_fingerprint': {'sha256': 'unknown'},
            },
        ),
        patch('inventory_tracking.osd.reader.inspect_images') as images,
        pytest.raises(ValueError, match='unsupported game build'),
    ):
        reader.connect(tmp_path)
    images.assert_not_called()


def test_restart_clears_old_values_before_rediscovery(tmp_path):
    import json

    from tests.inventory_tracking.osd.test_state import snapshot

    reader = LiveReader(tmp_path)
    observed = []
    original_set_state = reader.set_state

    def record(state):
        observed.append(state)
        original_set_state(state)

    def inspect(pid, images, capture, output, **kwargs):
        if pid == 10 and observed:
            return {'status': 'stale'}
        data = snapshot()
        if pid == 20:
            data['groups']['players']['units'][0]['unit_id'] = 17
            reader.stop_event.set()
        (output / 'units.json').write_text(json.dumps(data))
        return {'status': 'research'}

    with (
        patch.object(reader, 'connect', side_effect=[(10, {}, {}), (20, {}, {})]),
        patch.object(reader, 'set_state', side_effect=record),
        patch.object(reader.stop_event, 'wait', return_value=False),
        patch('inventory_tracking.osd.reader.inspect_units', side_effect=inspect),
    ):
        reader.run()
    assert [state.player_id for state in observed] == [7, None, 17]
    assert observed[1].current_raw is None
    assert json.loads((tmp_path / 'state.json').read_text())['player_id'] == 17
