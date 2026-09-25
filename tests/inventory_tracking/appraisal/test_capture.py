import copy
import json
from pathlib import Path

import pytest

from inventory_tracking.appraisal import capture as appraisal_capture
from inventory_tracking.appraisal.capture import AppraisalCapture, selected_observation


@pytest.fixture
def fixture():
    return json.loads((Path(__file__).parents[1] / 'fixtures/appraisal_ring.json').read_text())


def test_freeze_decodes_only_requested_ring(fixture):
    snapshot = fixture['snapshot']
    report = fixture['report']
    selected = snapshot['resources']['items'][0]['unit_id']
    extra = copy.deepcopy(snapshot['resources']['items'][0])
    extra['unit_id'] = selected + 1
    snapshot['resources']['items'].append(extra)
    result = selected_observation(snapshot, report, selected)
    assert result['source']['unit_id'] == selected
    assert len(snapshot['resources']['items']) == 2


def test_selected_item_disappearing_is_not_replaced_by_other_ring(fixture):
    with pytest.raises(ValueError, match='Selected item missing'):
        selected_observation(fixture['snapshot'], fixture['report'], -1)


def test_cube_decode_requires_matching_selected_page_and_owner(fixture):
    row = fixture['snapshot']['resources']['items'][0]
    row['details']['inventory_page'] = 3
    result = selected_observation(fixture['snapshot'], fixture['report'], row['unit_id'], inventory_page=3)
    assert result['source']['container'] == {'page': 3, 'name': 'Horadric Cube'}
    with pytest.raises(ValueError, match='No owned inventory items'):
        selected_observation(fixture['snapshot'], fixture['report'], row['unit_id'])
    row['details']['owner_id'] += 1
    with pytest.raises(ValueError, match='No owned inventory items'):
        selected_observation(fixture['snapshot'], fixture['report'], row['unit_id'], inventory_page=3)


def test_moving_ring_between_containers_suppresses_result(monkeypatch):
    token = {'pid': 1, 'start_ticks': '2'}
    capture = AppraisalCapture(1, {'identity': token}, {})
    original = {'address': 1, 'unit_id': 2, 'data_pointer': 3, 'stats_pointer': 4, 'details': {'inventory_page': 3}}
    current = copy.deepcopy(original)
    current['details']['inventory_page'] = 0
    monkeypatch.setattr(appraisal_capture, 'game_focused', lambda _: True)
    monkeypatch.setattr(appraisal_capture, 'identity', lambda _: token)
    monkeypatch.setattr(capture, 'selection', lambda: (None, {'item': current}))
    assert not capture.still_selected({'identity': token, 'selection': {'item': original}})


@pytest.mark.parametrize('quality', [1, 2, 3, 4, 5, 6, 7, 8, 9])
@pytest.mark.parametrize('category', ['weapons', 'armor', 'misc'])
def test_selected_nonring_all_qualities_and_empty_stats(fixture, quality, category):
    from inventory_tracking.items.metadata import metadata

    row = fixture['snapshot']['resources']['items'][0]
    class_id, base = next((k, v) for k, v in metadata()['bases'].items() if v['category'] == category)
    row['txt_id'] = int(class_id)
    row['details']['quality'] = quality
    for array in row['resource_stats']['arrays']:
        array['stats'] = []
    result = selected_observation(fixture['snapshot'], fixture['report'], row['unit_id'])
    assert result['item']['base_name'] == base['name']
    assert result['item']['affixes'] == []
    assert result['appraisal_ready'] is False


@pytest.mark.parametrize('restart', [None, 'new_pid', 'reused_pid'])
def test_freeze_reads_selected_item_stats_only(fixture, monkeypatch, restart):
    snapshot = fixture['snapshot']
    row = copy.deepcopy(snapshot['resources']['items'][0])
    arrays = row.pop('resource_stats')
    row.update(address=100, data_pointer=200, stats_pointer=300)
    # A rare item must reach decoding; no magic-ring filter remains.
    row['details']['quality'] = 6
    snapshot.pop('resources')
    token = snapshot['identity']
    images = {'identity': token}
    capture = {'session': 'new'}
    connections = []

    def reconnect():
        connections.append(True)
        return token['pid'], images, capture

    old_token = dict(token)
    if restart == 'new_pid':
        old_token['pid'] += 1
    elif restart == 'reused_pid':
        old_token['start_ticks'] = 'old'

    def current_identity(pid):
        if pid != token['pid']:
            raise ProcessLookupError('old game exited')
        return token

    source = AppraisalCapture(old_token['pid'], {'identity': old_token}, {}, reconnect=reconnect)
    monkeypatch.setattr(appraisal_capture, 'identity', current_identity)
    monkeypatch.setattr(
        source,
        'selection',
        lambda: ({'snapshot': snapshot}, {'item': row, 'container': {'page': 0, 'name': 'Main inventory'}}),
    )
    monkeypatch.setattr(appraisal_capture, 'game_focused', lambda current: current['identity'] == token)
    reads = []

    def verify(pid, images, item, expected=None, **kwargs):
        assert pid == token['pid']
        assert images['identity'] == token
        reads.append(item['unit_id'])
        assert expected is None or expected == arrays
        return arrays

    monkeypatch.setattr(appraisal_capture, 'verify_item', verify)
    frozen = source.freeze()
    assert reads == [row['unit_id'], row['unit_id']]
    assert frozen['observation']['item']['rarity'] == 'rare'
    assert snapshot['resources']['selected_only']
    assert len(snapshot['resources']['items']) == 1
    assert connections == ([True] if restart else [])
    if restart:
        assert source.images is images
        assert source.capture is capture
        assert not source.still_selected({'identity': old_token})


def test_failed_reconnect_retries_next_request_without_reading_old_memory(monkeypatch):
    attempts = []

    def reconnect():
        attempts.append(True)
        raise ValueError('game image unavailable')

    source = AppraisalCapture(1, {'identity': {'pid': 1, 'start_ticks': 'old'}}, {}, reconnect=reconnect)
    monkeypatch.setattr(appraisal_capture, 'identity', lambda _: {'pid': 1, 'start_ticks': 'new'})
    monkeypatch.setattr(appraisal_capture, 'game_focused', lambda _: pytest.fail('stale focus checked'))
    for _ in range(2):
        with pytest.raises(ValueError, match='game image unavailable'):
            source.freeze()
    assert len(attempts) == 2


def test_slow_reconnect_requires_fresh_hotkey_before_sampling(monkeypatch):
    now = [0.0]
    token = {'pid': 2, 'start_ticks': 'new'}
    connections = []

    def reconnect():
        connections.append(True)
        now[0] += 2
        return 2, {'identity': token}, {}

    source = AppraisalCapture(1, {'identity': {'pid': 1, 'start_ticks': 'old'}}, {}, reconnect=reconnect)
    monkeypatch.setattr(appraisal_capture.time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(appraisal_capture, 'identity', lambda _: token)
    monkeypatch.setattr(appraisal_capture, 'game_focused', lambda _: True)
    samples = []

    def selection():
        samples.append(True)
        raise ValueError('No inventory item under the mouse')

    monkeypatch.setattr(source, 'selection', selection)
    with pytest.raises(ValueError, match='Game reconnected; press Alt\\+D again'):
        source.freeze()
    assert not samples
    with pytest.raises(ValueError, match='No inventory item'):
        source.freeze()
    assert samples == [True]
    assert connections == [True]


def test_metadata_changes_during_selected_read_reject(monkeypatch):
    token = {'pid': 1, 'start_ticks': '2'}
    item = {'data_pointer': 100, 'stats_pointer': 200, 'details': {}}

    class Reader:
        def __init__(self, *_):
            self.calls = 0
            self.ranges = []

        def read(self, address, size):
            self.calls += 1
            return bytes([self.calls]) * size

    monkeypatch.setattr(appraisal_capture, 'identity', lambda _: token)
    monkeypatch.setattr(appraisal_capture, 'process_mappings', lambda _: [])
    monkeypatch.setattr(appraisal_capture.os, 'open', lambda *_: 123)
    monkeypatch.setattr(appraisal_capture.os, 'close', lambda _: None)
    monkeypatch.setattr(appraisal_capture, 'ResearchReader', Reader)
    monkeypatch.setattr(appraisal_capture, 'unit_matches', lambda *_: True)
    monkeypatch.setattr(appraisal_capture, 'describe_item', lambda *_: {})
    monkeypatch.setattr(appraisal_capture, 'read_item_arrays', lambda *_: {'complete': True, 'arrays': []})
    with pytest.raises(ValueError, match='metadata changed'):
        appraisal_capture.verify_item(1, {'identity': token}, item)


def test_shared_stash_decode_requires_native_selection_provenance(fixture):
    sample = json.loads((Path(__file__).parents[1] / 'fixtures/hover_stash_sequence.json').read_text())[2]
    snapshot = sample['snapshot']
    item = next(u for u in snapshot['groups']['items']['units'] if u['unit_id'] == 985832484)
    row = {k: copy.deepcopy(item[k]) for k in ('unit_id', 'txt_id', 'mode', 'details')}
    row['resource_stats'] = {'complete': True, 'arrays': [{'header_offset': 0xE8, 'stats': []}]}
    snapshot['resources'] = {'complete': True, 'items': [row]}
    report = fixture['report']
    report['game']['identity'] = snapshot['identity']
    with pytest.raises(ValueError, match='No owned inventory items'):
        selected_observation(snapshot, report, item['unit_id'], inventory_page=4)
    result = selected_observation(
        snapshot, report, item['unit_id'], inventory_page=4, selection_sample=sample, image_base=0x140000000
    )
    assert result['source']['owner_id'] == 142258002
    assert result['source']['player_id'] == 284532388
    assert result['source']['container']['name'] == 'Shared stash'
    row['details']['owner_id'] = 284532388
    with pytest.raises(ValueError, match='provenance mismatch'):
        selected_observation(
            snapshot, report, item['unit_id'], inventory_page=4, selection_sample=sample, image_base=0x140000000
        )


@pytest.mark.parametrize('index', [0, 1, 2, 3])
def test_panel_selection_reaches_decoder_with_correct_owner_and_mode(fixture, index):
    sample = json.loads((Path(__file__).parents[1] / 'fixtures/hover_panels_sequence.json').read_text())[index]
    snapshot = sample['snapshot']
    item = snapshot['groups']['items']['units'][0]
    row = {k: copy.deepcopy(item[k]) for k in ('unit_id', 'txt_id', 'mode', 'details')}
    row['resource_stats'] = {'complete': True, 'arrays': [{'header_offset': 0xE8, 'stats': []}]}
    snapshot['resources'] = {'complete': True, 'items': [row]}
    report = fixture['report']
    report['game']['identity'] = snapshot['identity']
    result = selected_observation(
        snapshot,
        report,
        item['unit_id'],
        inventory_page=item['details']['inventory_page'],
        selection_sample=sample,
        image_base=0x140000000,
    )
    assert result['source']['owner_type'] == (0 if index < 2 else 1)
    assert result['source']['owner_id'] == (284532388 if index < 2 else 492907658)
    if index >= 2:
        with pytest.raises(ValueError, match='Unsupported inventory container'):
            selected_observation(snapshot, report, item['unit_id'], inventory_page=1)


@pytest.mark.parametrize('local_damage', [False, True])
def test_revalidation_ignores_research_candidates_but_checks_stat_values(monkeypatch, local_damage):
    token = {'pid': 1, 'start_ticks': '2'}
    item = {'data_pointer': 100, 'stats_pointer': 200, 'details': {}}
    arrays = {'complete': True, 'arrays': [{'header_offset': 232, 'stats': [{'id': 19, 'layer': 0, 'raw': 75}]}]}

    class Reader:
        def __init__(self, *_):
            self.ranges = []

        def read(self, address, size):
            return bytes(size)

    monkeypatch.setattr(appraisal_capture, 'identity', lambda _: token)
    monkeypatch.setattr(appraisal_capture, 'process_mappings', lambda _: [])
    monkeypatch.setattr(appraisal_capture.os, 'open', lambda *_: 123)
    monkeypatch.setattr(appraisal_capture.os, 'close', lambda _: None)
    monkeypatch.setattr(appraisal_capture, 'ResearchReader', Reader)
    monkeypatch.setattr(appraisal_capture, 'unit_matches', lambda *_: True)
    monkeypatch.setattr(appraisal_capture, 'describe_item', lambda *_: {})
    monkeypatch.setattr(appraisal_capture, 'read_item_arrays', lambda *_: copy.deepcopy(arrays))
    damage = [{'id': 17, 'layer': 0, 'raw': 80}, {'id': 18, 'layer': 0, 'raw': 80}]
    if local_damage:
        monkeypatch.setattr(appraisal_capture, 'owned_damage_modifiers', lambda *_: copy.deepcopy(damage))
    frozen = appraisal_capture.verify_item(1, {'identity': token}, item)
    assert frozen['stat_diagnostics']['validated'] is False
    appraisal_capture.verify_item(1, {'identity': token}, item, frozen)
    if local_damage:
        damage[0]['raw'] = 81
    else:
        arrays['arrays'][0]['stats'][0]['raw'] = 76
    with pytest.raises(ValueError, match='stats changed'):
        appraisal_capture.verify_item(1, {'identity': token}, item, frozen)


def test_unknown_panel_gets_one_bounded_alt_d_discovery_capture(monkeypatch):
    source = AppraisalCapture(1, {'identity': {}, 'candidate_base': 0x140000000}, {})
    sample = {'after': {'widgets': {'mouse': {'address': 123}}}}
    calls = []
    monkeypatch.setattr(appraisal_capture, 'game_focused', lambda _: True)
    monkeypatch.setattr(source, 'sample_selection', lambda *, all_grids=False: calls.append(all_grids) or sample)
    monkeypatch.setattr(
        appraisal_capture,
        'resolve_selection',
        lambda *_: {'status': 'unavailable', 'reason': 'Unsupported inventory widget'},
    )
    with pytest.raises(ValueError, match='Unsupported inventory widget') as caught:
        source.freeze()
    assert calls == [False, True]
    assert caught.value.diagnostics['expanded'] == sample
    assert caught.value.diagnostics['validated'] is False


def test_empty_slot_does_not_trigger_expanded_discovery(monkeypatch):
    source = AppraisalCapture(1, {'identity': {}, 'candidate_base': 0x140000000}, {})
    calls = []
    monkeypatch.setattr(appraisal_capture, 'game_focused', lambda _: True)
    monkeypatch.setattr(source, 'sample_selection', lambda *, all_grids=False: calls.append(all_grids) or {})
    monkeypatch.setattr(appraisal_capture, 'resolve_selection', lambda *_: {'status': 'no_item'})
    with pytest.raises(ValueError, match='No inventory item under the mouse'):
        source.freeze()
    assert calls == [False]


def test_failed_discovery_preserves_original_panel_evidence(monkeypatch):
    source = AppraisalCapture(1, {'identity': {}, 'candidate_base': 0x140000000}, {})
    sample = {'after': {'widgets': {'mouse': {'address': 123}}}}

    def capture(*, all_grids=False):
        if all_grids:
            raise ValueError('Process changed')
        return sample

    monkeypatch.setattr(appraisal_capture, 'game_focused', lambda _: True)
    monkeypatch.setattr(source, 'sample_selection', capture)
    monkeypatch.setattr(
        appraisal_capture,
        'resolve_selection',
        lambda *_: {'status': 'unavailable', 'reason': 'Unsupported inventory widget'},
    )
    with pytest.raises(ValueError, match='Unsupported inventory widget') as caught:
        source.freeze()
    assert caught.value.diagnostics['initial'] == sample
    assert caught.value.diagnostics['discovery_error'] == 'Process changed'
