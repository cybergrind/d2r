from pricing.triage.compiled_rolls import compile_model, lookup
from tests.pricing.triage.test_bands import listing


MODEL = {
    'name': 'Example',
    'ethereal': False,
    'socket_contents': 'empty',
    'deciding': {'skill': {'min': 1, 'max': 3, 'better': 'higher', 'label': 'Skill'}},
    'validation': {'use_roll_model': True},
}


def cohort():
    rows = []
    for i in range(4):
        r = listing(i, 0.2 if i == 0 else 2)
        r.update(ethereal=False, socket_contents='empty')
        r['properties']['skill'] = 2 if i == 0 else 3
        rows.append(r)
    return rows


def test_compiled_comparisons_keep_sparse_rolls_check_and_below_listed_rolls_vendor():
    model = compile_model(MODEL, cohort())
    item = {
        'category': 'uniques',
        'name': 'Example',
        'ethereal': False,
        'socket_contents': 'empty',
        'properties': {'skill': 2},
    }
    result = lookup(item, [model], keep_ist=0.25)
    assert result['verdict'] == 'check'
    assert result['comparison_band']['q1_ist'] == 0.2
    assert result['comparison_band']['sellers'] == 1
    assert result['band'] is None
    result = lookup(item | {'properties': {'skill': 1}}, [model], keep_ist=0.25)
    assert result['verdict'] == 'vendor'
    assert result['band'] is None
    assert result['upper_bound_ist'] == 0.2
    result = lookup(item | {'properties': {}}, [model], keep_ist=0.25)
    assert result['verdict'] == 'check'
    assert result['band'] is None


def test_models_cannot_cross_ethereal_or_socket_variants():
    model = compile_model(MODEL, cohort())
    item = {
        'category': 'uniques',
        'name': 'Example',
        'ethereal': True,
        'socket_contents': 'empty',
        'properties': {'skill': 3},
    }
    assert lookup(item, [model], keep_ist=0.25) is None
    assert lookup(item | {'ethereal': False, 'socket_contents': 'filled'}, [model], keep_ist=0.25) is None


def test_generic_comparison_runs_when_validation_is_tied_or_unavailable():
    for error in (None, 1):
        report = MODEL | {
            'validation': {'use_roll_model': False, 'roll_median_error': error, 'name_median_error': error}
        }
        assert compile_model(report, cohort()) is not None


def test_generic_comparison_falls_back_only_when_validation_is_worse():
    report = MODEL | {'validation': {'use_roll_model': False, 'roll_median_error': 2, 'name_median_error': 1}}
    assert compile_model(report, cohort()) is None


def test_model_overrides_name_price_and_report_names_the_comparison():
    from inventory_tracking.appraisal.triage import headline
    from pricing.triage.bands import band_for
    from pricing.triage.engine import assess

    model = compile_model(MODEL, cohort())
    tables = {
        'bands': {('uniques', 'example', 'name'): band_for('uniques', 'Example', cohort())},
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': {'rows': []},
        'roll_models': [model],
    }
    item = {
        'category': 'uniques',
        'name': 'Example',
        'ethereal': False,
        'socket_contents': 'empty',
        'properties': {'skill': 2},
    }
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['decision_ist'] is None
    assert 'Skill 2' in headline(result)
    assert 'comparable-or-worse' in headline(result)


def test_socket_counts_partition_calibration_prices_and_runtime_lookup():
    from pricing.triage.analyze_rolls import analyze

    rows = []
    for sockets, price in ((1, 0.1), (3, 10), (None, 100)):
        for i in range(3):
            row = listing(f'{sockets}-{i}', price, ethereal=False, socket_contents='empty', sockets=sockets)
            row['properties']['skill'] = 3
            rows.append(row)
    definitions = [
        {
            'name': 'Example',
            'roll_ranges': {
                '1': {'min': 1, 'max': 3, 'better': 'higher', 'property': 'Skill'},
            },
        }
    ]
    game = {'stats': {'1': {'property_id': 'skill'}}, 'skills': {}}
    reports = analyze(rows, definitions, game)
    assert len(reports) == 3
    assert {r['sockets'] for r in reports} == {1, 3, None}
    models = [compile_model(report, rows) for report in reports]
    item = {
        'category': 'uniques',
        'name': 'Example',
        'ethereal': False,
        'socket_contents': 'empty',
        'sockets': 1,
        'properties': {'skill': 3},
    }
    result = lookup(item, models, keep_ist=0.25)
    assert result['verdict'] == 'vendor'
    assert result['band']['q1_ist'] == 0.1
    assert result['band']['sellers'] == 3
    result = lookup(item | {'sockets': 3}, models, keep_ist=0.25)
    assert result['verdict'] == 'slow'
    assert result['band']['q1_ist'] == 10
    assert lookup(item | {'sockets': 2}, models, keep_ist=0.25) is None
    assert lookup(item | {'sockets': None}, models, keep_ist=0.25)['band']['q1_ist'] == 100


def test_named_roll_models_separate_original_upgraded_and_unknown_bases():
    from pricing.triage.analyze_rolls import analyze

    rows = []
    for base, price in [('original', 0.1), ('upgraded', 10), (None, 100)]:
        for i in range(3):
            row = listing(f'{base}-{i}', price, ethereal=False, socket_contents='empty', base_code=base)
            row['properties']['skill'] = 3
            rows.append(row)
    definitions = [
        {'name': 'Example', 'roll_ranges': {'1': {'min': 1, 'max': 3, 'better': 'higher', 'property': 'Skill'}}}
    ]
    reports = analyze(rows, definitions, {'stats': {'1': {'property_id': 'skill'}}, 'skills': {}})
    assert len(reports) == 3
    models = [compile_model(report, rows) for report in reports]
    item = {
        'category': 'uniques',
        'name': 'Example',
        'ethereal': False,
        'socket_contents': 'empty',
        'properties': {'skill': 3},
        'base_code': 'original',
    }
    assert lookup(item, models, keep_ist=0.25)['band']['q1_ist'] == 0.1
    assert lookup(item | {'base_code': 'upgraded'}, models, keep_ist=0.25)['band']['q1_ist'] == 10
    assert lookup(item | {'base_code': None}, models, keep_ist=0.25)['band']['q1_ist'] == 100


def test_production_coarse_policy_discards_unproven_roll_split():
    assert compile_model(MODEL, cohort(), require_supported_split=True) is None
    rows = cohort()
    low = rows[0]
    rows += [low | {'seller_id': f'low-{i}', 'listing_id': f'low-{i}'} for i in range(2)]
    model = compile_model(MODEL, rows, require_supported_split=True)
    assert model is not None
    assert list(model['deciding']) == ['skill']


def test_captured_deciding_skill_uses_native_identity_without_market_mapping():
    from pricing.triage.adapters import from_drop

    observation = {
        'item': {
            'name': 'Example',
            'rarity': 'unique',
            'ethereal': False,
            'sockets': 0,
            'socket_contents': 'empty',
            'affixes': [],
        },
        'decoded_stats': [{'memory_stat': {'id': 107, 'layer': 111, 'raw': 2}, 'status': 'decoded', 'value': 2}],
    }
    item = from_drop(observation)
    rows = [r | {'sockets': 0} for r in cohort()]
    report = MODEL | {'sockets': 0, 'deciding': {'skill': MODEL['deciding']['skill'] | {'native_key': '107:111'}}}
    model = compile_model(report, rows)
    result = lookup(item, [model], keep_ist=0.25)
    assert result['comparison_band']['sellers'] == 1
    assert result['band'] is None
    assert result['comparison_band']['q1_ist'] == 0.2
    assert 'Skill 2' in result['reason']
    # An all-class skill is a different stat, even with the same skill parameter.
    observation['decoded_stats'][0]['memory_stat']['id'] = 97
    assert lookup(from_drop(observation), [model], keep_ist=0.25)['band'] is None
    observation['decoded_stats'][0]['memory_stat']['id'] = 107
    observation['decoded_stats'][0]['status'] = 'unresolved'
    assert lookup(from_drop(observation), [model], keep_ist=0.25)['band'] is None


def test_coarse_roll_model_pools_bases_but_requires_supported_price_splits():
    from pricing.triage.analyze_rolls import analyze

    rows = []
    for i in range(19):
        row = listing(
            i,
            0.789 if i != 1 else 0.2,
            ethereal=False,
            socket_contents='empty',
            sockets=0,
            base_code='original' if i % 2 else None,
        )
        row['properties']['skill'] = i + 1 if i < 2 else 3
        rows.append(row)
    definitions = [
        {'name': 'Example', 'roll_ranges': {'1': {'min': 1, 'max': 3, 'better': 'higher', 'property': 'Skill'}}}
    ]
    reports = analyze(
        rows,
        [*definitions, {'name': 'Unlisted'}],
        {'stats': {'1': {'property_id': 'skill'}}, 'skills': {}},
        coarse=True,
    )
    assert len(reports) == 1
    guard = compile_model(reports[0], rows, require_supported_split=True)
    assert guard['reference_only'] is True
    # Offline diagnostic comparisons remain available, but cannot set a live price.
    models = [compile_model(reports[0], rows)]
    item = {
        'category': 'uniques',
        'name': 'Example',
        'ethereal': False,
        'socket_contents': 'empty',
        'sockets': 0,
        'base_code': 'original',
        'properties': {'skill': 2},
    }
    result = lookup(item, models, keep_ist=0.25)
    assert result['verdict'] == 'check'
    assert result['comparison_band']['sellers'] == 2
    assert abs(result['comparison_band']['q1_ist'] - 0.34725) < 1e-9
    guarded = lookup(item, [guard], keep_ist=0.25)
    assert guarded['verdict'] == 'check'
    assert guarded['band'] is None
    assert lookup(item | {'ethereal': True}, models, keep_ist=0.25) is None


def test_coarse_models_preserve_supported_base_premiums_and_reject_socket_contents():
    from pricing.triage.analyze_rolls import analyze

    rows = []
    for base, price in [('original', 0.1), ('upgraded', 10)]:
        for i in range(3):
            row = listing(f'{base}-{i}', price, ethereal=False, socket_contents='empty', sockets=0, base_code=base)
            row['properties']['skill'] = 3
            rows.append(row)
    definitions = [
        {'name': 'Example', 'roll_ranges': {'1': {'min': 1, 'max': 3, 'better': 'higher', 'property': 'Skill'}}}
    ]
    reports = analyze(
        rows,
        [*definitions, {'name': 'Unlisted'}],
        {'stats': {'1': {'property_id': 'skill'}}, 'skills': {}},
        coarse=True,
    )
    models = [compile_model(r, rows) for r in reports]
    assert len(models) == 2
    item = {
        'category': 'uniques',
        'name': 'Example',
        'ethereal': False,
        'socket_contents': 'empty',
        'sockets': 0,
        'base_code': 'original',
        'properties': {'skill': 3},
    }
    assert lookup(item, models, keep_ist=0.25)['band']['q1_ist'] == 0.1
    assert lookup(item | {'base_code': 'upgraded'}, models, keep_ist=0.25)['band']['q1_ist'] == 10
    assert lookup(item | {'base_code': None}, models, keep_ist=0.25) is None
    for contents in ('filled', 'unknown', None):
        assert lookup(item | {'socket_contents': contents}, models, keep_ist=0.25) is None


def test_failed_validation_keeps_sparse_deciding_roll_check_with_reference_only():
    rows = cohort()
    rows.extend(rows[-1] | {'seller_id': f'extra-{i}', 'listing_id': f'extra-{i}'} for i in range(15))
    report = MODEL | {
        'coarse_facets': [],
        'deciding': {'skill': MODEL['deciding']['skill'] | {'sample_size': 19, 'top_count': 18}},
        'validation': {'roll_median_error': 0.556, 'name_median_error': 0.342},
    }
    model = compile_model(report, rows, require_supported_split=True)
    assert model is not None
    item = {
        'category': 'uniques',
        'name': 'Example',
        'ethereal': False,
        'socket_contents': 'empty',
        'properties': {'skill': 2},
    }
    result = lookup(item, [model], keep_ist=0.25)
    assert result['verdict'] == 'check'
    assert result['band'] is None
    assert result['reference_band']['sellers'] == 19
    assert 'listed copies are mostly' in result['reason']
    # Low rolls remain CHECK even without comparable sellers or with three.
    assert lookup(item | {'properties': {'skill': 1}}, [model], keep_ist=0.25)['verdict'] == 'check'
    lower = rows[0] | {'properties': {'skill': 2}}
    expanded = rows + [lower | {'seller_id': f'low-{i}', 'listing_id': f'low-{i}'} for i in range(3)]
    supported = compile_model(report, expanded, require_supported_split=True)
    assert lookup(item, [supported], keep_ist=0.25)['verdict'] == 'check'
    # The rejected model cannot price top or unknown rolls.
    for props in ({'skill': 3}, {}):
        assert lookup(item | {'properties': props}, [model], keep_ist=0.25) is None
    # A sparse draft without a robust selection signal cannot create this guard.
    weak = report | {'deciding': {'skill': MODEL['deciding']['skill'] | {'sample_size': 2, 'top_count': 2}}}
    assert compile_model(weak, rows, require_supported_split=True) is None


def test_guide_deciding_rolls_survive_unsupported_price_split_without_inventing_price():
    from pricing.triage.analyze_rolls import analyze, guide_rolls

    html = """<tr data-roll-name="Example" data-roll-ethereal="false"
        data-roll-floors='{"skill": 2, "leech": 10}'><td>Guide thresholds</td></tr>"""
    rules = guide_rolls(html, 'guide.html#worked')
    rows = cohort()
    for i, row in enumerate(rows):
        row['properties']['leech'] = 8 if i == 0 else 12
    definitions = [
        {
            'name': 'Example',
            'roll_ranges': {
                '1': {'min': 1, 'max': 3, 'better': 'higher', 'property': 'Skill'},
                '2': {'min': 8, 'max': 12, 'better': 'higher', 'property': 'Leech'},
            },
        }
    ]
    game = {'stats': {'1': {'property_id': 'skill'}, '2': {'property_id': 'leech'}}, 'skills': {}}
    report = analyze(rows, definitions, game, coarse=True, guide_rules=rules)[0]
    model = compile_model(report, rows, require_supported_split=True)
    assert model is not None
    item = {
        'category': 'uniques',
        'name': 'Example',
        'ethereal': False,
        'socket_contents': 'empty',
        'properties': {'skill': 2, 'leech': 9},
    }
    result = lookup(item, [model], keep_ist=0.25)
    assert result['verdict'] == 'check'
    assert result['band'] is None
    assert result['upper_bound_ist'] is None
    assert result['reference_band']['sellers'] == 4
    assert 'guide' in result['reason']
    assert 'mostly' not in result['reason']
    # The guide floor is not the native maximum; reaching it removes this cap.
    assert lookup(item | {'properties': {'skill': 2, 'leech': 10}}, [model], keep_ist=0.25) is None
    assert lookup(item | {'ethereal': True}, [model], keep_ist=0.25) is None
    # Missing deciding data cannot silently restore a name-level estimate.
    assert lookup(item | {'properties': {'skill': 2}}, [model], keep_ist=0.25)['verdict'] == 'check'


def test_guide_price_requires_held_out_support_even_when_each_split_has_sellers():
    rows = cohort()
    rows += [rows[0] | {'seller_id': f'low-{i}', 'listing_id': f'low-{i}'} for i in range(2)]
    report = MODEL | {
        'deciding': {'skill': MODEL['deciding']['skill'] | {'guide_floor': 3, 'guide_source': 'guide.html'}},
        'validation': {'evaluated': 0, 'use_roll_model': False, 'roll_median_error': None, 'name_median_error': None},
    }
    model = compile_model(report, rows, require_supported_split=True)
    item = {
        'category': 'uniques',
        'name': 'Example',
        'ethereal': False,
        'socket_contents': 'empty',
        'properties': {'skill': 2},
    }
    result = lookup(item, [model], keep_ist=0.25)
    assert result['verdict'] == 'check'
    assert result['band'] is None
    assert result['upper_bound_ist'] is None


def test_held_out_validation_keeps_independently_declared_guide_axes():
    from pricing.triage.roll_comparisons import leave_one_out

    spec = MODEL['deciding']['skill'] | {'guide_source': 'guide.html', 'guide_floor': 3}
    rows = cohort()
    # Too few training sellers to discover an axis; the guide supplied it before
    # any seller was held out. Both predictors must still be scored.
    result = leave_one_out(rows, {'skill': spec}, ranges={'skill': spec})
    assert result['evaluated'] > 0
    assert result['roll_median_error'] is not None
    assert result['name_median_error'] is not None


def test_completed_runewords_calibrate_filled_recipe_sockets_without_mixing_bases():
    from pricing.triage.analyze_rolls import analyze

    rows = []
    for base, price in (('shield', 1), ('sword', 10)):
        for i in range(20):
            row = listing(f'{base}-{i}', price, ethereal=False, socket_contents='filled', sockets=4, base_code=base)
            row['category'] = 'runewords'
            row['properties']['cast'] = 25 if i == 0 else 35
            rows.append(row)
    definition = {
        'name': 'Example',
        'roll_ranges': {
            '105': {'min': 25, 'max': 35, 'better': 'higher', 'property': 'cast3'},
        },
    }
    reports = analyze(rows, [definition], {'stats': {'105': {'property_id': 'cast'}}, 'skills': {}}, coarse=True)
    assert len(reports) == 2
    assert {r['base_code'] for r in reports} == {'shield', 'sword'}
    models = [compile_model(r, rows, require_supported_split=True) for r in reports]
    assert all(models)
    item = {
        'category': 'runewords',
        'name': 'Example',
        'base_code': 'shield',
        'ethereal': False,
        'sockets': 4,
        'socket_contents': 'filled',
        'properties': {'cast': 25},
    }
    result = lookup(item, models, keep_ist=0.25)
    assert result['verdict'] == 'check'
    assert result['band'] is None
    assert result['reference_band']['q1_ist'] == 1
    assert lookup(item | {'base_code': 'sword'}, models, keep_ist=0.25)['reference_band']['q1_ist'] == 10
    for changes in ({'base_code': None}, {'ethereal': True}, {'sockets': 3}, {'socket_contents': 'empty'}):
        assert lookup(item | changes, models, keep_ist=0.25) is None


def split_cohort():
    """Ten sellers at each of two skill rolls, the better roll asking four times as much."""
    rows = []
    for i in range(20):
        r = listing(i, 0.5 if i < 10 else 2)
        r.update(ethereal=False, socket_contents='empty')
        r['properties']['skill'] = (2 if i % 2 else 1) if i < 10 else 3
        rows.append(r)
    return rows


def test_price_split_roll_has_one_cell_per_side_of_the_boundary():
    from pricing.triage.roll_comparisons import price_split_stats

    ranges = {'skill': {'min': 1, 'max': 3, 'better': 'higher', 'label': 'Skill'}}
    deciding = price_split_stats(split_cohort(), ranges, {})
    assert deciding['skill']['price_split'] == 3
    model = compile_model(MODEL | {'deciding': deciding}, split_cohort())
    item = {
        'category': 'uniques',
        'name': 'Example',
        'ethereal': False,
        'socket_contents': 'empty',
        'properties': {'skill': 1},
    }
    low = lookup(item, [model], keep_ist=0.25)
    assert (low['band']['q1_ist'], low['band']['sellers']) == (0.5, 10)
    assert lookup(item | {'properties': {'skill': 2}}, [model], keep_ist=0.25)['band'] == low['band']
    assert lookup(item | {'properties': {'skill': 3}}, [model], keep_ist=0.25)['band']['sellers'] == 20
    assert lookup(item | {'properties': {}}, [model], keep_ist=0.25) is None


def test_price_split_needs_a_held_out_gain_over_the_name_median():
    from pricing.triage.roll_comparisons import price_split_stats

    rows = split_cohort()
    for i, row in enumerate(rows):
        row['ask_ist'] = 1 + i % 3  # asks unrelated to the roll
    ranges = {'skill': {'min': 1, 'max': 3, 'better': 'higher', 'label': 'Skill'}}
    assert price_split_stats(rows, ranges, {}) == {}
