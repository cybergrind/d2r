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


def test_paid_scorer_is_diagnostic_only_and_cannot_change_live_verdict():
    from pricing.triage.engine import assess, prepare_tables

    model = {
        'category': 'rare',
        'family': 'ring',
        'properties': {'418': 30, '437': 15},
        'threshold': 2,
        'references': {},
        'corpus_items': 100,
        'supporters': [{'seller_id': str(i), 'paid_properties': ['418', '437'], 'ask_ist': 1} for i in range(3)],
        'conditions': {'ethereal': False, 'sockets': 0, 'socket_contents': 'empty', 'base_tier': 'not_applicable'},
    }
    tables = prepare_tables(
        {'bands': [], 'paid_scores': {'models': [model]}}, {'rows': [], 'keep_ist': 0.25}, {'rows': []}
    )
    item = {
        'category': 'rare',
        'family': 'ring',
        'name': 'Ring',
        'properties': {'418': 35, '437': 16},
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
    }
    from pricing.triage.paid_properties import lookup

    assert lookup(item, [model]) is not None
    result = assess(item, tables)
    assert result['verdict'] == 'vendor'
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
    assert model['threshold'] == 2
    assert compiled['validation'][0]['held_out_sellers'] == len(held)
    assert compiled['validation'][0]['held_out_recall'] == 1
    assert lookup(drop(), compiled['models'])['reference_band']['sellers'] == len(training)
    vetoed = compile_scores(rows, corpus, ['vendor'] * 100, {'418', '437'}, 0.25, negatives=[drop()])
    assert lookup(drop(), vetoed['models']) is None


def test_a_secondary_roll_never_listed_without_the_main_one_does_not_flag_on_its_own():
    # Magic Demon Heart with 43 life and 37 fire resist and no Necromancer skills was CHECK
    # ("1 paid properties meet family threshold 1") on 2026-10-06. Listed heads are paid for
    # their skills; life and resistance only ever accompany them.
    from pricing.triage.paid_properties import compile_scores, lookup
    from tests.pricing.triage.test_learned_patterns import drop, member

    rows = [member(str(i)) for i in range(12)]  # every seller: 418 (main) and 437 (secondary)
    corpus = [drop() | {'properties': {}} for _ in range(100)]
    models = compile_scores(rows, corpus, ['vendor'] * 100, {'418', '437'}, 0.25)['models']
    assert lookup(drop() | {'properties': {'437': 16}}, models) is None
    assert lookup(drop() | {'properties': {'418': 35}}, models) is None
    assert lookup(drop(), models) is not None


def test_a_family_with_almost_no_observed_drops_gets_no_model():
    # Magic Crown, 198% enhanced defence and nothing else, was CHECK on 2026-10-06: the magic
    # helm model was fitted against one drop, so the rarity-wide 8% cap could not reject it.
    from pricing.triage.paid_properties import compile_scores, lookup
    from tests.pricing.triage.test_learned_patterns import drop, member

    rows = [member(str(i)) for i in range(12)]
    other = [drop() | {'family': 'amul', 'properties': {}} for _ in range(99)]
    corpus = [drop() | {'properties': {}}, *other]
    models = compile_scores(rows, corpus, ['vendor'] * 100, {'418', '437'}, 0.25)['models']
    assert lookup(drop(), models) is None


def test_models_do_not_transfer_across_ethereal_sockets_or_base_tier():
    from inventory_tracking.items.metadata import metadata
    from pricing.triage.guide_cases import item_from_spec
    from pricing.triage.paid_properties import compile_scores, lookup
    from tests.pricing.triage.test_learned_patterns import member

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Corona')
    rows = [
        member(
            str(i),
            category='magic',
            rarity='magic',
            name='Corona',
            base_code=base['code'],
            item_type='helm',
            ethereal=True,
            sockets=2,
        )
        for i in range(12)
    ]

    def item(name='Corona', ethereal=True, sockets=2, stats=None):
        return item_from_spec(
            {'base': name, 'rarity': 'magic', 'ethereal': ethereal, 'sockets': sockets, 'stats': stats or {}}
        )

    corpus = [item() for _ in range(100)]
    compiled = compile_scores(rows, corpus, ['vendor'] * 100, {'418', '437'}, 0.25)
    good = item(stats={'7:0': 35, '0:0': 16})
    assert lookup(good, compiled['models']) is not None
    for wrong in (
        good | {'ethereal': False},
        good | {'sockets': 0},
        item('Crown', stats={'7:0': 35, '0:0': 16}),
        good | {'ethereal': None},
    ):
        assert lookup(wrong, compiled['models']) is None


def test_two_secondary_properties_cannot_replace_the_listed_skill_combination():
    from pricing.triage.paid_properties import compile_scores, lookup
    from tests.pricing.triage.test_learned_patterns import drop, member

    rows = [member(str(i)) for i in range(12)]
    for row in rows:
        row['properties'].update({'418': 40, '437': 20, '429': 30})
    corpus = [drop() | {'properties': {}} for _ in range(100)]
    compiled = compile_scores(rows, corpus, ['vendor'] * 100, {'418', '437', '429'}, 0.25)
    assert lookup(drop() | {'properties': {'418': 45, '437': 25}}, compiled['models']) is None
    assert lookup(drop() | {'properties': {'418': 45, '437': 25, '429': 35}}, compiled['models']) is not None


def test_three_folds_cover_each_seller_once_without_copy_leakage():
    rows = [{'seller_id': str(i), 'listing_id': str(j)} for i in range(12) for j in range(2)]
    held_sets = []
    for fold in range(3):
        training, held = split_sellers(rows, fold)
        held_sets.append({row['seller_id'] for row in held})
        assert not held_sets[-1] & {row['seller_id'] for row in training}
    assert set.union(*held_sets) == {str(i) for i in range(12)}
    assert sum(map(len, held_sets)) == 12


def test_three_fold_diagnostics_do_not_inflate_live_attention():
    from pricing.triage.engine import prepare_tables
    from pricing.triage.paid_validation import validate
    from tests.pricing.triage.test_learned_patterns import drop, member

    rows = [member(str(i)) for i in range(12)]
    corpus = [drop() | {'properties': {}} for _ in range(100)]
    tables = prepare_tables({'bands': []}, {'rows': [], 'keep_ist': 0.25}, {'rows': []})
    report = validate(rows, corpus, ['vendor'] * 100, {'418', '437'}, tables)
    assert report['rare_magic_added_votes'] == 12
    assert report['decision'] == 'remove'
    held = report['out_of_sample']['categories']['rare']
    assert held['flagged_valuable'] == 0
    assert held['attention_with_scorer'] == 12
    assert held['scorer_added_valuable'] == 12
    assert report['models']['folds'] == [{'fitted': 1, 'deployable': 1, 'vetoed_or_over_threshold': 0}] * 3


def test_two_sellers_and_duplicate_copies_cannot_support_a_subset():
    from pricing.triage.paid_properties import compile_scores, lookup
    from tests.pricing.triage.test_learned_patterns import drop, member

    rows = [member(str(i)) for i in range(12)]
    training, _ = split_sellers(rows)
    subset_sellers = {row['seller_id'] for row in training[:2]}
    for row in rows:
        if row['seller_id'] not in subset_sellers:
            row['properties']['429'] = 30
    rows.extend(dict(training[0], listing_id=f'extra-{i}') for i in range(10))
    corpus = [drop() | {'properties': {}} for _ in range(100)]
    compiled = compile_scores(rows, corpus, ['vendor'] * 100, {'418', '437', '429'}, 0.25)
    assert lookup(drop(), compiled['models']) is None
    assert lookup(drop() | {'properties': {'418': 35, '437': 16, '429': 35}}, compiled['models']) is not None
