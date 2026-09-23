from unittest.mock import patch

import pytest

from inventory_tracking.models import Observation
from inventory_tracking.reader import LiveReader


def test_unsupported_build_never_starts_layout_reads(tmp_path):
    reader = LiveReader(tmp_path)
    with (
        patch('inventory_tracking.reader.select_game_process', return_value=12),
        patch(
            'inventory_tracking.reader.inspect_game',
            return_value={
                'memory_access': True,
                'executable_fingerprint': {'sha256': 'unknown'},
            },
        ),
        patch('inventory_tracking.reader.inspect_images') as images,
        pytest.raises(ValueError, match='unsupported game build'),
    ):
        reader.connect(tmp_path)
    images.assert_not_called()


def test_restart_clears_old_values_before_rediscovery(tmp_path, snapshot):
    import json

    reader = LiveReader(tmp_path)
    observed = []
    original_set_state = reader.set_state

    def record(state):
        observed.append(state)
        original_set_state(state)

    def inspect(pid, images, capture, **kwargs):
        if pid == 10 and observed:
            return {'status': 'stale'}
        data = snapshot()
        if pid == 20:
            data['groups']['players']['units'][0]['unit_id'] = 17
            reader.stop_event.set()
        return data

    with (
        patch.object(reader, 'connect', side_effect=[(10, {}, {}), (20, {}, {})]),
        patch.object(reader, 'set_state', side_effect=record),
        patch.object(reader.stop_event, 'wait', return_value=False),
        patch('inventory_tracking.reader.sample_units', side_effect=inspect),
        patch('inventory_tracking.reader.observe_show_items', return_value=Observation(100, False)) as show_items,
        patch('inventory_tracking.reader.observe_consume', return_value=Observation.unavailable()) as consume,
    ):
        reader.run()
    assert [state.session.player_id if state.session else None for state in observed] == [7, None, 17]
    assert observed[1].health is None
    assert observed[0].show_items.value is False
    assert observed[1].show_items.value is None
    assert show_items.call_count == 2
    assert consume.call_count == 2
    assert json.loads((tmp_path / 'state.json').read_text())['session'][2] == 17


@pytest.mark.parametrize('column', [3, 4])
def test_delivery_message_survives_incomplete_samples_for_one_second(tmp_path, healing_setup, sample, column):
    from inventory_tracking.automation import Automation
    from inventory_tracking.config import MERC_HEALING
    from inventory_tracking.models import BeltCell, State
    from inventory_tracking.osd.presenter import Presenter

    make, _ = healing_setup
    automation = Automation([make(MERC_HEALING)])
    presenter = Presenter()
    reader = LiveReader(tmp_path, automation=automation, observer=presenter.update)
    automation.step(sample(healing_cells=(BeltCell(column, 101),)))
    reader.set_state(State(sampled_at=100.5, reason='incomplete read'))
    expected = [f'merc potion sent (Shift+{column})']
    assert presenter.render(now=100.999) == expected
    assert presenter.render(now=101) == []
