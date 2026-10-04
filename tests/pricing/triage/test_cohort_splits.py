from pricing.triage.cohort_splits import worthwhile
from tests.pricing.triage.test_bands import listing


def test_split_requires_independent_sellers_and_material_q1_difference():
    low = [listing(str(i), 1) for i in range(3)]
    high = [listing(str(i + 3), 1.5) for i in range(3)]
    assert worthwhile([low, high])
    assert not worthwhile([low, high[:2]])
    assert not worthwhile([low, [r | {'ask_ist': 1.49} for r in high]])
    assert not worthwhile([low, [r | {'seller_id': 'same'} for r in high]])
    assert not worthwhile([low])


def test_roll_split_needs_three_sellers_on_both_sides():
    from pricing.triage.cohort_splits import roll_split

    rows = [listing(i, 0.1) | {'properties': {'roll': 1}} for i in range(3)]
    rows += [listing(i + 3, 1) | {'properties': {'roll': 3}} for i in range(3)]
    assert roll_split(rows, 'roll')
    assert not roll_split(rows[:-1], 'roll')
    assert not roll_split([r | {'ask_ist': 1} for r in rows], 'roll')


def test_runeword_base_splits_are_retained_only_with_supported_price_difference():
    from pricing.triage.bands import build_bands
    from pricing.triage.engine import assess

    def evaluate(prices, base, ethereal=True):
        rows = [
            listing(f'{code}-{i}', price, base_code=code, ethereal=True) | {'category': 'runewords'}
            for code, group in prices.items()
            for i, price in enumerate(group)
        ]
        document = build_bands(rows, [], policies=[{'category': 'runewords', 'facets': ['base_code', 'ethereal']}])
        tables = {
            'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in document['bands']},
            'rules': {
                'keep_ist': 0.25,
                'rows': [],
                'policies': [{'category': 'runewords', 'facets': ['base_code', 'ethereal']}],
            },
            'own': {'rows': []},
        }
        return assess({'category': 'runewords', 'name': 'Example', 'base_code': base, 'ethereal': ethereal}, tables)

    prices = {'base-a': [1, 1, 1], 'base-b': [1.2, 1.2, 1.2]}
    assert evaluate(prices, 'base-b')['band']['sellers'] == 6
    assert evaluate(prices, 'base-b')['decision_ist'] == 1
    assert evaluate(prices, 'base-b', ethereal=False)['verdict'] == 'check'
    assert evaluate(prices, 'base-b', ethereal=None)['verdict'] == 'check'
    prices['base-b'] = [2, 2, 2]
    assert evaluate(prices, 'base-b')['band']['sellers'] == 3
    assert evaluate(prices, 'base-b')['decision_ist'] == 2
    assert evaluate(prices, None)['verdict'] == 'check'
    prices['base-b'] = [2, 2]
    assert evaluate(prices, 'base-b')['band']['sellers'] == 5


def test_numeric_cohorts_split_roll_ranges_when_exact_rolls_are_sparse():
    from pricing.triage.named_cohorts import compile_named, lookup

    rows = [listing(i, 1 if i < 3 else 5) for i in range(6)]
    for i, row in enumerate(rows):
        row['properties']['roll'] = i + 1
    reference = compile_named('uniques', 'Example', rows, [], facets=['property:roll'])[0]

    def price(roll):
        return lookup({'ethereal': False, 'properties': {'roll': roll}}, reference)

    assert price(3)['q1_ist'] == 1
    assert price(4)['q1_ist'] == 5
    assert price(4)['sellers'] == 3
    assert price(3.5)['q1_ist'] == 1
    assert price(0) is None
    assert price(None) is None
    sparse = compile_named('uniques', 'Example', rows[:-1], [], facets=['property:roll'])[0]
    assert lookup({'ethereal': False, 'properties': {'roll': 4}}, sparse)['sellers'] == 5


def test_numeric_cohorts_can_retain_multiple_supported_price_steps():
    from pricing.triage.named_cohorts import compile_named, lookup

    rows = [listing(i, (1, 5, 20)[i // 3]) for i in range(9)]
    for i, row in enumerate(rows):
        row['properties']['roll'] = i + 1
    reference = compile_named('uniques', 'Example', rows, [], facets=['property:roll'])[0]
    for roll, expected in ((1, 1), (4, 5), (7, 20)):
        band = lookup({'ethereal': False, 'properties': {'roll': roll}}, reference)
        assert band['q1_ist'] == expected
        assert band['sellers'] == 3
    assert lookup({'ethereal': False, 'properties': {'roll': float('nan')}}, reference) is None
