from pricing.triage.engine import assess, prepare_tables
from pricing.triage.learned_patterns import derive, guard
from tests.pricing.triage.test_bands import listing


def member(seller, price=1, **changes):
    row = listing(seller, price)
    row.update(
        category='rare',
        rarity='rare',
        name='Ring',
        item_type='ring',
        ethereal=False,
        sockets=0,
        socket_contents='empty',
    )
    row['properties'].update({'418': 30, '437': 15})
    row.update(changes)
    return row


def drop(**changes):
    return dict(
        category='rare',
        family='ring',
        name='Ring',
        base_name='Ring',
        ethereal=False,
        sockets=0,
        socket_contents='empty',
        properties={'418': 35, '437': 16},
        **changes,
    )


def test_learning_requires_independent_scoped_sellers_and_keeps_cheap_reference_rows():
    rows = [member(i) for i in range(3)]
    assert not derive([*rows[:2], dict(rows[0], listing_id='duplicate')], {'418', '437'}, 0.25)
    foreign = dict(rows[2], properties={**rows[2]['properties'], '800': True})
    assert not derive([*rows[:2], foreign], {'418', '437'}, 0.25)
    learned = derive([*rows, member(4, 0.01)], {'418', '437'}, 0.25)
    assert len(learned) == 1
    assert learned[0]['reference_band']['sellers'] == 4
    assert learned[0]['reference_band']['q1_ist'] < 1


def test_guard_rejects_whole_pattern_without_lowering_thresholds():
    patterns = derive([member(i) for i in range(3)], {'418', '437'}, 0.25)
    corpus = [drop() for _ in range(9)] + [drop() for _ in range(91)]
    for item in corpus[9:]:
        item['properties'] = {}
    assert guard(patterns, corpus, ['vendor'] * 100) == []
    corpus[8]['properties'] = {}
    assert guard(patterns, corpus, ['vendor'] * 100) == patterns


def test_learned_pattern_is_check_with_reference_never_a_sale_price():
    learned = derive([member(i) for i in range(3)], {'418', '437'}, 0.25)
    tables = prepare_tables({'bands': [], 'learned_patterns': learned}, {'rows': [], 'keep_ist': 0.25}, {'rows': []})
    result = assess(drop(), tables)
    assert result['verdict'] == 'check'
    assert result['decision_ist'] is None
    assert result['band'] is None
    assert result['reference_band']['sellers'] == 3
    for field, value in [('ethereal', True), ('sockets', 1), ('socket_contents', 'filled')]:
        assert assess(drop() | {field: value}, tables)['verdict'] == 'vendor'


def test_learning_rejects_undated_invalid_asks_and_counts_cheapest_seller_vote():
    rows = [member(i) for i in range(3)]
    for changes in ({'observed_at': None}, {'ask_ist': float('inf')}, {'ask_ist': True}):
        assert not derive([*rows[:2], rows[2] | changes], {'418', '437'}, 0.25)
    cheaper = rows[2] | {'listing_id': 'cheaper-copy', 'ask_ist': 0.01}
    assert not derive([*rows, cheaper], {'418', '437'}, 0.25)


def test_learning_does_not_combine_best_axes_or_drop_other_affixes():
    rows = [member(i) for i in range(6)]
    for i, row in enumerate(rows):
        row['properties'].update({'418': 40 if i < 3 else 20, '437': 10 if i < 3 else 20})
    learned = derive(rows, {'418', '437'}, 0.25)
    tables = prepare_tables({'bands': [], 'learned_patterns': learned}, {'rows': [], 'keep_ist': 0.25}, {'rows': []})
    # No listed copy combines both low axes. The rectangular minima are not evidence.
    assert assess(drop() | {'properties': {'418': 20, '437': 10}}, tables)['verdict'] == 'vendor'
    assert assess(drop() | {'properties': {'418': 40, '437': 10}}, tables)['verdict'] == 'check'
    for row in rows:
        row['properties']['429'] = 20
    learned = derive(rows, {'418', '437', '429'}, 0.25)
    tables = prepare_tables({'bands': [], 'learned_patterns': learned}, {'rows': [], 'keep_ist': 0.25}, {'rows': []})
    assert assess(drop() | {'properties': {'418': 40, '437': 20}}, tables)['verdict'] == 'vendor'


def test_shared_combination_survives_different_secondary_affixes():
    rows = [member(i) for i in range(3)]
    for row, extra in zip(rows, ('429', '427', '428'), strict=True):
        row['properties'][extra] = 10
    patterns = derive(rows, {'418', '437', '429', '427', '428'}, 0.25)
    tables = prepare_tables({'bands': [], 'learned_patterns': patterns}, {'rows': [], 'keep_ist': 0.25}, {'rows': []})
    assert assess(drop(), tables)['verdict'] == 'check'


def test_guard_rejects_pattern_that_disagrees_with_guide_negative():
    patterns = derive([member(i) for i in range(3)], {'418', '437'}, 0.25)
    assert guard(patterns, [], [], negatives=[drop()]) == []
