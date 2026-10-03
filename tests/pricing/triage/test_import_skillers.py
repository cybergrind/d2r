from pricing.triage.engine import assess
from pricing.triage.import_skillers import compile_skillers


def test_documented_life_skiller_requires_tree_and_life_without_invented_price():
    source = {
        'CH-skiller-example': {
            'class': 'charm-grand-skiller',
            'bucket_def': 'Grand Charm (prop 443)',
            'split': {'CH-skiller-example-life': {'n_priced': 3, 'median_ist': 100}},
        }
    }
    rules = compile_skillers(source)
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': rules}, 'own': {'rows': []}}
    item = {'category': 'magic', 'name': 'Grand Charm', 'properties': {'443': 1, '418': 20}}
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['decision_ist'] is None
    for properties in ({'443': 1}, {'418': 20}, {'499': 1, '418': 20}):
        assert assess(item | {'properties': properties}, tables)['verdict'] == 'vendor'
    assert assess(item | {'name': 'Small Charm'}, tables)['verdict'] == 'vendor'


def test_no_life_rule_from_unpriced_or_plain_only_evidence():
    source = {
        'CH-skiller-example': {
            'class': 'charm-grand-skiller',
            'bucket_def': 'Grand Charm (prop 443)',
            'split': {'CH-skiller-example-plain': {'n_priced': 5}, 'CH-skiller-example-life': {'n_priced': 0}},
        }
    }
    assert not any(rule.get('pattern') for rule in compile_skillers(source))


def test_plain_skiller_cannot_borrow_life_or_fhr_prices():
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import build_bands
    from tests.pricing.triage.test_bands import listing

    source = {'tree': {'class': 'charm-grand-skiller', 'bucket_def': 'Grand Charm (prop 443)'}}
    rules = compile_skillers(source)
    rows = []
    for i, (suffix, price) in enumerate([({}, 0.5)] * 3 + [({'418': 40}, 50)] * 3 + [({'430': 12}, 10)] * 3):
        row = listing(i, price)
        row.update(name='Grand Charm', category='charms', rarity='magic')
        row['properties'].update({'443': 1, **suffix})
        rows.append(row)
    document = build_bands(rows, [], rules=rules)
    tables = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in document['bands']},
        'rules': {'keep_ist': 0.25, 'rows': rules},
        'own': {'rows': []},
    }
    for index, price in ((0, 0.5), (3, 50), (6, 10)):
        result = assess(from_listing(rows[index]), tables)
        assert result['decision_ist'] == price
        assert result['band']['sellers'] == 3


def test_life_skiller_uses_no_better_life_rolls_but_not_other_trees_or_suffixes():
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import build_bands
    from tests.pricing.triage.test_bands import listing

    rules = compile_skillers({'tree': {'class': 'charm-grand-skiller', 'bucket_def': 'Grand Charm (prop 443)'}})
    rows = []
    for i, (props, price) in enumerate(
        [
            ({'443': 1, '418': 20}, 1),
            ({'443': 1, '418': 25}, 2),
            ({'443': 1, '418': 30}, 3),
            ({'443': 1, '418': 45}, 100),
            ({'443': 1, '418': 20, '430': 12}, 100),
            ({'516': 1, '418': 20}, 100),
        ]
    ):
        row = listing(i, price)
        row.update(name='Grand Charm', category='charms', rarity='magic')
        row['properties'].update(props)
        rows.append(row)
    document = build_bands(rows, [], rules=rules)
    tables = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in document['bands']},
        'rules': {'keep_ist': 0.25, 'rows': rules},
        'own': {'rows': []},
    }
    target = from_listing(rows[2])
    result = assess(target, tables)
    assert result['verdict'] == 'slow'
    assert result['decision_ist'] == 1.5
    assert 'comparable-or-worse life ≤30' in result['reason']
    assert result['band']['sellers'] == 3
    low = assess(from_listing(rows[0]), tables)
    assert low['verdict'] != 'sell'
    assert low['band']['sellers'] == 1
