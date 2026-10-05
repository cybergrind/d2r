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


def test_torch_class_is_an_identity_even_with_similar_prices_or_sparse_sellers():
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import build_bands
    from pricing.triage.engine import assess
    from pricing.triage.roll_cohorts import groups, matches_cohort

    rows = []
    for prop, price, count in [('514', 1, 3), ('442', 1.2, 3), ('1862', 50, 1)]:
        for index in range(count):
            row = listing(f'{prop}-{index}', price)
            row.update(
                name='Hellfire Torch', category='uniques', rarity='unique', socket_contents='empty', ethereal=False
            )
            row['properties'].update({prop: 3})
            rows.append(row)
    document = build_bands(rows, [])
    tables = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in document['bands']},
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': {'rows': []},
    }
    assert assess(from_listing(rows[0]), tables)['decision_ist'] == 1
    assert assess(from_listing(rows[3]), tables)['decision_ist'] == 1.2
    for props in ({'1862': 3}, {'453': 3}, {}, {'514': 3, '442': 3}):
        result = assess(from_listing(rows[0] | {'properties': props}), tables)
        assert result['verdict'] == 'check'
        assert result['decision_ist'] is None
    cohorts = groups(rows)
    assert sorted(len(members) for _, members in cohorts) == [1, 3, 3]
    for identity, members in cohorts:
        assert all(matches_cohort(from_listing(row), identity) for row in members)
        foreign = rows[3] if members[0]['properties'].get('514') == 3 else rows[0]
        assert not matches_cohort(from_listing(foreign), identity)


def test_exclusive_unique_bonuses_cannot_share_bands_or_roll_models():
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import build_bands
    from pricing.triage.engine import assess
    from pricing.triage.roll_cohorts import groups, matches_cohort

    for name, left, right in (
        ('Wraithstep', {'1546': 1}, {'1548': 1}),
        ('Opalvein', {'1879': 3}, {'510': 20}),
        ("Ormus' Robes", {'703': 3}, {'602': 3}),
    ):
        rows = []
        for variant, price in ((left, 1), (right, 1.2)):
            for i in range(3):
                row = listing(f'{price}-{i}', price)
                row.update(name=name, category='uniques', rarity='unique', ethereal=False, socket_contents='empty')
                row['properties'].update(variant)
                rows.append(row)
        bands = build_bands(rows, [])['bands']
        tables = {
            'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in bands},
            'rules': {'keep_ist': 0.25, 'rows': []},
            'own': {'rows': []},
        }
        assert assess(from_listing(rows[0]), tables)['decision_ist'] == 1
        assert assess(from_listing(rows[3]), tables)['decision_ist'] == 1.2
        for properties in ({}, left | right):
            result = assess(from_listing(rows[0] | {'properties': properties}), tables)
            assert result['verdict'] == 'check'
            assert result['decision_ist'] is None
        cohorts = groups(rows)
        assert sorted(len(members) for _, members in cohorts) == [3, 3]
        assert not matches_cohort(from_listing(rows[0]), {'ethereal': False, 'coarse_facets': []})
