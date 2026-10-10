import json
from unittest.mock import patch

import pytest

from inventory_tracking.models import Observation
from inventory_tracking.tracking.reader import LiveReader


def test_unsupported_build_never_starts_layout_reads(tmp_path):
    reader = LiveReader(tmp_path)
    with (
        patch('inventory_tracking.tracking.reader.select_game_process', return_value=12),
        patch(
            'inventory_tracking.tracking.reader.inspect_game',
            return_value={
                'memory_access': True,
                'executable_fingerprint': {'sha256': 'unknown'},
            },
        ),
        patch('inventory_tracking.tracking.reader.inspect_images') as images,
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
        patch('inventory_tracking.tracking.reader.sample_units', side_effect=inspect),
        patch(
            'inventory_tracking.tracking.reader.observe_show_items', return_value=Observation(100, False)
        ) as show_items,
        patch('inventory_tracking.tracking.reader.observe_consume', return_value=Observation.unavailable()) as consume,
        patch('inventory_tracking.tracking.reader.observe_shop_panel', return_value=Observation.unavailable()) as shop,
    ):
        reader.run()
    assert [state.session.player_id if state.session else None for state in observed] == [7, None, 17]
    assert shop.call_count == consume.call_count
    assert observed[1].health is None
    assert observed[0].show_items.value is False
    assert observed[1].show_items.value is None
    assert show_items.call_count == 2
    assert consume.call_count == 2
    assert json.loads((tmp_path / 'state.json').read_text())['session'][2] == 17


@pytest.mark.parametrize('column', [3, 4])
def test_delivery_message_survives_incomplete_samples_for_one_second(tmp_path, healing_setup, sample, column):
    from inventory_tracking.automation.controller import Automation
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


def test_stale_image_capture_is_retried_as_not_ready(tmp_path):
    from inventory_tracking.native.session import GameNotReady

    reader = LiveReader(tmp_path)
    with (
        patch('inventory_tracking.tracking.reader.select_game_process', return_value=12),
        patch(
            'inventory_tracking.tracking.reader.inspect_game',
            return_value={
                'memory_access': True,
                'executable_fingerprint': {'sha256': 'supported'},
            },
        ),
        patch('inventory_tracking.tracking.reader.SUPPORTED_SHA256', 'supported'),
        patch('inventory_tracking.tracking.reader.inspect_images', return_value={'status': 'candidate'}),
        patch(
            'inventory_tracking.tracking.reader.capture_image',
            return_value={'status': 'stale', 'error': 'Process or PE headers changed before capture'},
        ),
        pytest.raises(GameNotReady, match='changed'),
    ):
        reader.connect(tmp_path)


@pytest.mark.parametrize(
    'images',
    [{'status': 'stale', 'error': 'Mappings changed during discovery'}, {'status': 'no_candidate'}],
)
def test_game_image_not_found_yet_is_retried_as_not_ready(tmp_path, images):
    # D2R.exe starting or exiting: the image is not (or no longer) mapped; serve waits instead of crashing.
    from inventory_tracking.native.session import GameNotReady

    reader = LiveReader(tmp_path)
    with (
        patch('inventory_tracking.tracking.reader.select_game_process', return_value=12),
        patch(
            'inventory_tracking.tracking.reader.inspect_game',
            return_value={'memory_access': True, 'executable_fingerprint': {'sha256': 'supported'}},
        ),
        patch('inventory_tracking.tracking.reader.SUPPORTED_SHA256', 'supported'),
        patch('inventory_tracking.tracking.reader.inspect_images', return_value=images),
        pytest.raises(GameNotReady, match='game image unavailable'),
    ):
        reader.connect(tmp_path)


def test_the_unit_table_is_remembered_per_build_and_taken_from_the_cache_in_the_menus(tmp_path):
    # user, 2026-10-10: `make serve` restarted in the lobby never attached (the signature's code page is
    # still encrypted there), so the macro request did nothing. The table's RVA is a constant of the build.
    from inventory_tracking.native.session import GameNotReady

    cache = tmp_path / 'unit-table.json'
    captured = {
        'status': 'captured', 'base': 0x1000, 'sha256': 'of this memory image', 'identity': {'pid': 12},
        'unit_table_candidates': [{'signature_address': 0x1234, 'table_rva': 0x500, 'table_address': 0x1500}],
    }  # fmt: skip
    in_menus = dict(captured, base=0x7000, sha256='of another image', unit_table_candidates=[])
    patches = (
        patch('inventory_tracking.tracking.reader.select_game_process', return_value=12),
        patch(
            'inventory_tracking.tracking.reader.inspect_game',
            return_value={'memory_access': True, 'executable_fingerprint': {'sha256': 'supported'}, 'identity': {}},
        ),
        patch('inventory_tracking.tracking.reader.SUPPORTED_SHA256', 'supported'),
        patch('inventory_tracking.tracking.reader.inspect_images', return_value={'status': 'candidate'}),
    )
    with patches[0], patches[1], patches[2], patches[3]:
        with patch('inventory_tracking.tracking.reader.capture_image', return_value=dict(captured)):
            LiveReader(tmp_path / 'run1', table_cache=cache).connect(tmp_path)
        assert json.loads(cache.read_text()) == {'supported': {'table_rva': 0x500, 'signature_rva': 0x234}}
        with patch('inventory_tracking.tracking.reader.capture_image', return_value=dict(in_menus)):
            _, _, capture = LiveReader(tmp_path / 'run2', table_cache=cache).connect(tmp_path)
        assert capture['unit_table_candidates'] == [
            {'signature_address': 0x7234, 'table_rva': 0x500, 'table_address': 0x7500}
        ]
        cache.write_text(json.dumps({'an older build': {'table_rva': 0x900, 'signature_rva': 0x1}}))
        with (
            patch('inventory_tracking.tracking.reader.capture_image', return_value=dict(in_menus)),
            pytest.raises(GameNotReady, match='unit table unavailable'),
        ):
            LiveReader(tmp_path / 'run3', table_cache=cache).connect(tmp_path)
