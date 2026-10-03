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


def test_compiled_comparisons_keep_low_rolls_cheap_and_missing_rolls_unpriced():
    model = compile_model(MODEL, cohort())
    item = {
        'category': 'uniques',
        'name': 'Example',
        'ethereal': False,
        'socket_contents': 'empty',
        'properties': {'skill': 2},
    }
    result = lookup(item, [model], keep_ist=0.25)
    assert result['verdict'] == 'vendor'
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
    assert compile_model(MODEL | {'validation': {'use_roll_model': False}}, cohort()) is None


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
    assert result['verdict'] == 'vendor'
    assert result['decision_ist'] == 0.2
    assert 'Skill 2' in headline(result)
    assert 'comparable-or-worse' in headline(result)
