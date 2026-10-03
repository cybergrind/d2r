from pricing.triage.engine import assess


def test_complete_paid_pattern_below_bucket_is_check_not_vendor():
    rule = {
        'category': 'magic',
        'name': 'Small Charm',
        'bucket': 'physical-life',
        'pattern': {'properties': {'damage': {'min': 1}, 'ar': {'min': 1}, 'life': {'min': 1}}},
        'properties': {'damage': {'min': 3}, 'ar': {'min': 10}, 'life': {'min': 16}},
        'labels': {'damage': 'max damage', 'ar': 'attack rating', 'life': 'life'},
        'pattern_label': 'Physical pattern complete',
        'premium': True,
    }
    tables = {'rules': {'keep_ist': 0.25, 'rows': [rule]}, 'own': {'rows': []}, 'bands': {}}
    item = {'category': 'magic', 'name': 'Small Charm', 'properties': {'damage': 2, 'ar': 18, 'life': 17}}
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert 'max damage 2 of 3' in result['reason']
    assert assess({**item, 'properties': {'damage': 3, 'ar': 18, 'life': 17}}, tables)['verdict'] == 'sell'
    assert assess({**item, 'properties': {'damage': 3, 'life': 17}}, tables)['verdict'] == 'vendor'


def test_keep_price_uses_q1_instead_of_high_median():
    tables = {
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': {'rows': []},
        'bands': {('sets', 'example', 'name'): {'q1_ist': 0.2, 'median_ist': 7, 'liquidity': 'liquid'}},
    }
    assert assess({'category': 'sets', 'name': 'Example'}, tables)['verdict'] == 'vendor'


def test_check_is_white_on_identify_and_scored_separately_from_sell():
    from inventory_tracking.corpus.score import score
    from inventory_tracking.identify.service import item_summary, result_lines
    from inventory_tracking.presentation import Tone
    from tests.inventory_tracking.identify.test_service import observation

    triage = {'verdict': 'check', 'reason': 'max damage 2 of 3', 'band': None}
    item = item_summary(observation(), {'triage': triage})
    lines = result_lines({'state': 'complete', 'items': [item], 'issues': []})
    assert any('CHECK' in line.text for line in lines)
    assert lines[-1].tone == Tone.DEFAULT
    scored = score([{'id': 'a', **triage}], {'a': 'check'})
    assert scored['check_recall'] == 1
    assert scored['checks'] == 1
    assert scored['keeps'] == 0


def test_imported_fine_life_acceptance_and_unrelated_stats():
    import json
    from pathlib import Path

    from pricing.triage.import_watches import compile_watches

    rows = compile_watches(json.loads(Path('pricing/data/appraisal-value-watch.json').read_text())['rows'])
    tables = {'rules': {'keep_ist': 0.25, 'rows': rows}, 'own': {'rows': []}, 'bands': {}}
    item = {'category': 'magic', 'name': 'Small Charm', 'properties': {'448': 2, '423': 18, '418': 17}}
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert 'max damage 2 of 3' in result['reason']
    assert assess({**item, 'properties': {'448': 3, '423': 18, '418': 17}}, tables)['verdict'] == 'sell'
    assert assess({**item, 'properties': {'448': 2, '418': 17}}, tables)['verdict'] == 'vendor'
    assert assess({**item, 'properties': {'418': 17}}, tables)['verdict'] == 'vendor'
    poison = {**item, 'properties': {'518': 175, '418': 17}}
    assert assess(poison, tables)['verdict'] == 'sell'
    assert assess({**item, 'properties': {'418': 17, 'duration': 6}}, tables)['verdict'] == 'vendor'
