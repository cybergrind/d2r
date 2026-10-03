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
    assert result['band']['q1_ist'] == 0.2
    assert result['band']['sellers'] == 1
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
    assert result['decision_ist'] == 0.2
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
