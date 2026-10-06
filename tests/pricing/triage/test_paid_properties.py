from pricing.triage.paid_properties import fit, score, split_sellers


def test_paid_properties_ignore_common_filler_and_count_strong_rolls():
    listed = [{'properties': {'speed': 20, 'resist': 30, 'defense': 50}} for _ in range(6)]
    corpus = [{'properties': {'speed': 20, 'resist': 8, 'defense': 50}} for _ in range(100)]
    model = fit(listed, corpus, ['vendor'] * 100)
    assert model['properties'] == {'resist': 30}
    assert model['threshold'] == 1
    assert score(corpus[0], model) == 0
    assert score(listed[0], model) == 1


def test_threshold_counts_existing_checks_and_uses_smallest_safe_count():
    listed = [{'properties': {'a': 10, 'b': 20}} for _ in range(6)]
    corpus = [{'properties': {}} for _ in range(100)]
    for item in corpus[:9]:
        item['properties'] = {'a': 10}
    corpus[0]['properties']['b'] = 20
    verdicts = ['vendor'] * 100
    verdicts[-1] = 'check'
    model = fit(listed, corpus, verdicts)
    assert model['threshold'] == 2
    assert model['corpus_checks'] == 2


def test_no_corpus_evidence_cannot_infer_paid_properties():
    assert fit([{'properties': {'a': 10}}] * 6, [], [])['properties'] == {}


def test_seller_holdout_never_splits_copies_and_is_input_order_independent():
    rows = [{'seller_id': str(i), 'listing_id': str(j)} for i in range(9) for j in range(2)]
    training, held = split_sellers(rows)
    assert len({r['seller_id'] for r in held}) == 3
    assert not {r['seller_id'] for r in held} & {r['seller_id'] for r in training}
    assert {r['seller_id'] for r in split_sellers(rows[::-1])[1]} == {r['seller_id'] for r in held}


def test_family_score_is_review_only_and_does_not_create_a_price():
    from pricing.triage.engine import assess, prepare_tables

    model = {'category': 'rare', 'family': 'ring', 'properties': {'418': 30}, 'threshold': 1, 'references': {}}
    tables = prepare_tables(
        {'bands': [], 'paid_scores': {'models': [model]}}, {'rows': [], 'keep_ist': 0.25}, {'rows': []}
    )
    item = {'category': 'rare', 'family': 'ring', 'name': 'Ring', 'properties': {'418': 35}}
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['decision_ist'] is None
    assert result['band'] is None
    assert assess(item | {'properties': {'418': 20}}, tables)['verdict'] == 'vendor'


def test_compilation_holds_sellers_out_and_vetoes_saved_false_positives():
    from pricing.triage.paid_properties import compile_scores, lookup
    from tests.pricing.triage.test_learned_patterns import drop, member

    rows = [member(str(i)) for i in range(12)]
    training, held = split_sellers(rows)
    # A property unique to holdout sellers must never enter the trained model.
    held_sellers = {row['seller_id'] for row in held}
    for row in rows:
        if row['seller_id'] in held_sellers:
            row['properties']['429'] = 99
    corpus = [drop() | {'properties': {}} for _ in range(100)]
    compiled = compile_scores(rows, corpus, ['vendor'] * 100, {'418', '437', '429'}, 0.25)
    model = compiled['models'][0]
    assert '429' not in model['properties']
    assert model['threshold'] == 1
    assert compiled['validation'][0]['held_out_sellers'] == len(held)
    assert compiled['validation'][0]['held_out_recall'] == 1
    assert lookup(drop(), compiled['models'])['reference_band']['sellers'] == len(training)
    vetoed = compile_scores(rows, corpus, ['vendor'] * 100, {'418', '437'}, 0.25, negatives=[drop()])
    assert lookup(drop(), vetoed['models']) is None
