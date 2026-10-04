import json

from inventory_tracking.appraisal.feedback import flag
from inventory_tracking.corpus.build import item_id


def record():
    return {
        'state': 'complete',
        'request_id': 3,
        'result': {
            'extraction': {'item': {'name': 'Example', 'rarity': 'unique'}, 'decoded_stats': []},
            'triage': {'verdict': 'slow', 'decision_ist': 0.6},
        },
    }


def test_disagreement_preserves_capture_and_verdict_without_inventing_label(tmp_path):
    current = record()
    assert flag(current, tmp_path, 'run/request-3')
    rows = json.loads((tmp_path / 'disagreements.json').read_text())
    identifier = item_id(current['result']['extraction'])
    assert rows[identifier]['observation'] == current['result']['extraction']
    assert rows[identifier]['triage']['verdict'] == 'slow'
    assert rows[identifier]['source'] == 'run/request-3'
    assert rows[identifier]['status'] == 'pending'
    assert not (tmp_path / 'labels.json').exists()
    assert not flag(current, tmp_path, 'run/request-3')
    assert len(json.loads((tmp_path / 'disagreements.json').read_text())) == 1


def test_empty_pending_or_rejected_card_cannot_flag_stale_item(tmp_path):
    for current in (None, {'state': 'pending'}, {'state': 'rejected'}, {'state': 'complete', 'result': {}}):
        assert not flag(current, tmp_path, 'run')
    assert not (tmp_path / 'disagreements.json').exists()
