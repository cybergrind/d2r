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


def test_shared_combination_needs_sellers_without_other_valuable_affixes():
    rows = [member(i) for i in range(3)]
    for row, extra in zip(rows, ('429', '427', '428'), strict=True):
        row['properties'][extra] = 10
    patterns = derive(rows, {'418', '437', '429', '427', '428'}, 0.25)
    tables = prepare_tables({'bands': [], 'learned_patterns': patterns}, {'rows': [], 'keep_ist': 0.25}, {'rows': []})
    assert assess(drop(), tables)['verdict'] == 'vendor'
    # The pair becomes supported only when three sellers price the pair itself.
    patterns = derive(rows + [member(i) for i in range(3, 6)], {'418', '437', '429', '427', '428'}, 0.25)
    tables = prepare_tables({'bands': [], 'learned_patterns': patterns}, {'rows': [], 'keep_ist': 0.25}, {'rows': []})
    assert assess(drop(), tables)['verdict'] == 'check'


def test_guard_rejects_pattern_that_disagrees_with_guide_negative():
    patterns = derive([member(i) for i in range(3)], {'418', '437'}, 0.25)
    assert guard(patterns, [], [], negatives=[drop()]) == []


def test_a_stat_pair_shared_by_sellers_priced_for_other_stats_is_not_a_pattern():
    # Rare War Boots, 20 run/walk + 5 dexterity + 8 fire resist, were CHECK with a
    # 10.37 Ist reference on 2026-10-06. Every listed copy carried two or three high
    # resists: the run/walk + dexterity pair is all they share, and it is not what is paid for.
    def boots(seller, **resists):
        row = member(seller, 20, name='War Boots', item_type='boot')
        row['properties'] = {k: v for k, v in row['properties'].items() if k not in ('418', '437')}
        row['properties'].update({'480': 20, '429': 3 + seller, **resists})
        return row

    rows = [
        boots(0, **{'427': 35, '428': 30}),
        boots(1, **{'426': 38, '428': 33}),
        boots(2, **{'426': 30, '427': 31}),
    ]
    ids = {'480', '429', '426', '427', '428'}
    learned = derive(rows, ids, 0.25)
    tables = prepare_tables({'bands': [], 'learned_patterns': learned}, {'rows': [], 'keep_ist': 0.25}, {'rows': []})
    weak = drop() | {
        'family': 'boot',
        'name': 'War Boots',
        'base_name': 'War Boots',
        'properties': {'480': 20, '429': 5, '427': 8},
    }
    assert assess(weak, tables)['verdict'] == 'vendor'
    listed = weak | {'properties': {'480': 20, '429': 5, '427': 35, '428': 30}}
    assert assess(listed, tables)['verdict'] == 'vendor'
    # One matching seller is insufficient. Supply two more independent copies
    # of the full resistance combination for the positive three-seller case.
    for seller in (3, 4):
        row = boots(seller, **{'427': 35, '428': 30})
        row['properties']['429'] = 5
        rows.append(row)
    learned = derive(rows, ids, 0.25)
    tables = prepare_tables({'bands': [], 'learned_patterns': learned}, {'rows': [], 'keep_ist': 0.25}, {'rows': []})
    assert assess(listed, tables)['verdict'] == 'check'
    assert assess(weak, tables)['verdict'] == 'vendor'
