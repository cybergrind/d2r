import copy

from inventory_tracking.collection.fingerprint import fingerprint, memory_stats


def test_fingerprint_ignores_location_and_session_fields(insight):
    observation = insight
    moved = copy.deepcopy(observation)
    moved['source'].update(unit_id=1, owner_id=2, player_id=2, item_owner_id=2, captured_at='later', position=[9, 9])
    moved['source']['container'] = {'page': 0, 'name': 'Main inventory'}
    moved['source']['viewer_context'] = {'player_id': 2, 'level': 1}
    assert fingerprint(moved) == fingerprint(observation)


def test_fingerprint_changes_with_any_stat_socket_or_identity(insight):
    observation = insight
    base = fingerprint(observation)
    changed = copy.deepcopy(observation)
    changed['decoded_stats'][0]['memory_stat']['raw'] += 1
    assert fingerprint(changed) != base
    changed = copy.deepcopy(observation)
    changed['item']['socket_items'] = changed['item']['socket_items'][:-1]
    assert fingerprint(changed) != base
    changed = copy.deepcopy(observation)
    changed['item']['ethereal'] = True
    assert fingerprint(changed) != base
    changed = copy.deepcopy(observation)
    changed['source']['item_identity'] = {'table': 'runeword', 'table_id': 1, 'offset': 72}
    assert fingerprint(changed) != base


def test_memory_stats_collects_single_combined_and_unresolved_entries():
    observation = {
        'decoded_stats': [
            {'memory_stat': {'layer': 0, 'id': 7, 'raw': 8960}},
            {'memory_stats': [{'layer': 0, 'id': 17, 'raw': 41}, {'layer': 0, 'id': 18, 'raw': 41}]},
        ],
        'unresolved_stats': [{'layer': 3, 'id': 188, 'raw': 1, 'status': 'unresolved'}],
    }
    assert memory_stats(observation) == [(0, 7, 8960), (0, 17, 41), (0, 18, 41), (3, 188, 1)]
