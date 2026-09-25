from pricing.knowledge.assessment.maintenance.guide_spans import audit_spans


def test_span_reconciliation_distinguishes_empty_missing_conflicting_and_stale_rows():
    mentions = [
        {'label': 'Insight', 'item_id': 'word'},
        {'label': '', 'item_id': ''},
        {'label': 'Spirit', 'item_id': 'other'},
        {'label': '', 'item_id': 'word'},
    ]
    rows = [
        {
            'id': 'good',
            'source_id': 'source',
            'source_locator': '/item-spans/0',
            'details': {'original_label': 'Insight', 'raw_item_id': 'word'},
        },
        {
            'id': 'wrong',
            'source_id': 'source',
            'source_locator': '/item-spans/2',
            'details': {'original_label': 'Different', 'raw_item_id': 'other'},
        },
        {'id': 'stale', 'source_id': 'source', 'source_locator': '/item-spans/99', 'details': {}},
    ]
    result = audit_spans(mentions, 'source', rows, {'word': {'name': 'Insight'}})
    assert [r['status'] for r in result['spans']] == [
        'represented',
        'empty_unresolved_span',
        'conflict',
        'missing_occurrence',
    ]
    assert result['unaccounted_occurrence_ids'] == ['stale', 'wrong']
    assert result['complete'] is False
