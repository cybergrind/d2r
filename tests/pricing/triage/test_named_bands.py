from pricing.triage.bands import build_bands
from pricing.triage.engine import assess
from tests.pricing.triage.test_bands import listing


def tables(rows, rules=()):
    bands = build_bands(rows, [], rules=rules)['bands']
    return {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in bands},
        'rules': {'keep_ist': 0.25, 'rows': list(rules)},
        'own': {'rows': []},
    }


def test_non_ethereal_drop_never_borrows_ethereal_or_unknown_asks():
    rows = [
        {**listing(i, price), 'ethereal': eth, 'properties': {**listing(i)['properties'], '738': eth}}
        for i, (price, eth) in enumerate(
            [(0.674, None), (0.789, None), (2.585, None), (11.421, True), (11.421, True), (79.947, True)]
        )
    ]
    result = assess({'category': 'uniques', 'name': 'Example', 'ethereal': False}, tables(rows))
    assert result['verdict'] == 'check'
    assert result['band'] is None or result['band']['median_ist'] is None
    assert result['reference_band']['median_ist'] == 7.003
    assert 'name band is reference only' in result['reason']
    assert assess({'category': 'uniques', 'name': 'Example', 'ethereal': True}, tables(rows))['verdict'] == 'slow'


def test_roll_bands_are_disjoint_and_take_precedence_over_name():
    rules = [
        {'category': 'uniques', 'name': 'Example', 'bucket': 'perfect', 'properties': {'425': 120}},
        {
            'category': 'uniques',
            'name': 'Example',
            'bucket': 'ordinary',
            'properties': {'425': {'min': 90, 'max': 119}},
        },
    ]
    rows = [
        {**listing(i, price), 'properties': {**listing(i)['properties'], '425': roll}}
        for i, (price, roll) in enumerate([(0.1, 100)] * 3 + [(10, 120)] * 3)
    ]
    data = tables(rows, rules)
    low = assess({'category': 'uniques', 'name': 'Example', 'ethereal': False, 'properties': {'425': 100}}, data)
    assert low['verdict'] == 'vendor'
    assert low['band']['median_ist'] == 0.1
    assert low['band']['sellers'] == 3
    high = assess({'category': 'uniques', 'name': 'Example', 'ethereal': False, 'properties': {'425': 120}}, data)
    assert high['verdict'] == 'slow'
    assert high['band']['median_ist'] == 10
    missing = assess({'category': 'uniques', 'name': 'Example'}, data)
    assert missing['verdict'] == 'vendor'
    assert missing['bucket'] == 'name'  # Supported cheap name; no premium ethereal/socket variant.


def test_runeword_ethereal_stays_separate_when_base_has_no_supported_split():
    policies = [{'category': 'runewords', 'facets': ['base_code', 'ethereal']}]
    rows = [{**listing(i, 8), 'category': 'runewords', 'base_code': 'base-a', 'ethereal': True} for i in range(3)]
    doc = build_bands(rows, [], policies=policies)
    data = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': [], 'policies': policies},
        'own': {'rows': []},
    }
    good = {'category': 'runewords', 'name': 'Example', 'base_code': 'base-a', 'ethereal': True}
    assert assess(good, data)['verdict'] == 'slow'
    for base in ('base-b', None):
        assert assess(good | {'base_code': base}, data)['verdict'] == 'slow'
    for change in [{'ethereal': False}, {'ethereal': None}]:
        result = assess({**good, **change}, data)
        assert result['verdict'] == 'check'
        assert result['band'] is None


def test_single_roll_group_uses_merged_price_until_a_supported_split_exists():
    rules = [{'category': 'uniques', 'name': 'Example', 'bucket': 'perfect', 'properties': {'425': 120}}]
    policies = [{'category': 'uniques', 'name': 'Example', 'require_bucket': True}]
    rows = [{**listing(i, 10), 'properties': {**listing(i)['properties'], '425': 120}} for i in range(3)]
    doc = build_bands(rows, [], rules=rules, policies=policies)
    data = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': rules, 'policies': policies},
        'own': {'rows': []},
    }
    assert (
        assess({'category': 'uniques', 'name': 'Example', 'ethereal': False, 'properties': {'425': 120}}, data)[
            'verdict'
        ]
        == 'slow'
    )
    for props in ({}, {'425': 100}):
        result = assess({'category': 'uniques', 'name': 'Example', 'ethereal': False, 'properties': props}, data)
        assert result['verdict'] == 'slow'
        assert result['band']['sellers'] == 3


def test_thin_premium_roll_group_keeps_merged_cohort():
    rules = [
        {'category': 'uniques', 'name': 'Example', 'bucket': 'perfect', 'properties': {'425': 120}},
        {'category': 'uniques', 'name': 'Example', 'bucket': 'other', 'properties': {'425': {'min': 90, 'max': 120}}},
    ]
    rows = [{**listing(i, 1), 'properties': {**listing(i)['properties'], '425': 100}} for i in range(3)]
    rows.append({**listing(4, 100), 'properties': {**listing(4)['properties'], '425': 120}})
    policies = [{'category': 'uniques', 'name': 'Example', 'require_bucket': True}]
    doc = build_bands(rows, [], rules=rules, policies=policies)
    data = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': rules, 'policies': policies},
        'own': {'rows': []},
    }
    result = assess({'category': 'uniques', 'name': 'Example', 'ethereal': False, 'properties': {'425': 120}}, data)
    assert result['verdict'] == 'slow'
    assert result['band']['sellers'] == 4
    assert result['band']['q1_ist'] == 1


def test_base_socket_contents_quality_and_count_cannot_cross_price_bands():
    policies = [{'category': 'base', 'facets': ['rarity', 'ethereal', 'sockets', 'socket_contents']}]
    good = {
        'category': 'base',
        'name': 'Example',
        'rarity': 'superior',
        'ethereal': False,
        'sockets': 4,
        'socket_contents': 'empty',
    }
    rows = [{**listing(i, 10), **good} for i in range(3)]
    doc = build_bands(rows, [], policies=policies)
    data = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': [], 'policies': policies},
        'own': {'rows': []},
    }
    assert assess(good, data)['verdict'] == 'slow'
    for change in [
        {'sockets': 0},
        {'sockets': 3},
        {'sockets': None},
        {'rarity': 'normal'},
        {'ethereal': True},
        {'socket_contents': 'filled'},
        {'socket_contents': 'unknown'},
    ]:
        result = assess({**good, **change}, data)
        assert result['band'] is None
        assert result['verdict'] == 'vendor'


def test_unknown_ethereal_never_prices_known_noneth_even_without_ethereal_sellers():
    rows = [{**listing(i, 10), 'properties': {**listing(i)['properties'], '738': None}} for i in range(3)]
    result = assess({'category': 'uniques', 'name': 'Example', 'ethereal': False}, tables(rows))
    assert result['band'] is None or result['band']['median_ist'] is None
    assert result['verdict'] == 'check'
    assert result['reference_band']['median_ist'] == 10
    unknown = assess({'category': 'uniques', 'name': 'Example', 'ethereal': None}, tables(rows))
    assert unknown['band']['median_ist'] == 10


def test_named_fallback_bands_never_pool_socket_counts_or_contents():
    for category, name in [('uniques', 'Tomb Reaver'), ('sets', "Griswold's Heart")]:
        rows = []
        for count, contents, price in [(1, 'empty', 0.1), (3, 'empty', 10), (3, 'filled', 50)]:
            for i in range(3):
                rows.append(
                    listing(f'{count}-{contents}-{i}', price)
                    | {
                        'category': category,
                        'name': name,
                        'ethereal': False,
                        'sockets': count,
                        'socket_contents': contents,
                    }
                )
        item = {'category': category, 'name': name, 'ethereal': False, 'sockets': 1, 'socket_contents': 'empty'}
        for policies in ([], [{'category': category, 'name': name, 'facets': ['ethereal']}]):
            doc = build_bands(rows, [], policies=policies)
            data = {
                'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
                'rules': {'keep_ist': 0.25, 'rows': [], 'policies': policies},
                'own': {'rows': []},
            }
            low = assess(item, data)
            assert low['verdict'] == 'vendor'
            assert low['band']['q1_ist'] == 0.1
            high = assess(item | {'sockets': 3}, data)
            assert high['verdict'] == 'slow'
            assert high['band']['q1_ist'] == 10
            assert high['band']['sellers'] == 3
            filled = assess(item | {'sockets': 3, 'socket_contents': 'filled'}, data)
            assert filled['decision_ist'] == 10
            assert assess(item | {'sockets': 2}, data)['verdict'] == 'vendor'
            assert assess(item | {'sockets': None}, data)['band'] is None
            # Insert prices are excluded, so unknown contents cannot inflate this known count.
            assert assess(item | {'socket_contents': 'unknown'}, data)['decision_ist'] == 0.1


def test_named_fallback_cannot_pool_original_upgraded_or_unknown_bases():
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import build_bands
    from pricing.triage.engine import assess
    from tests.pricing.triage.test_bands import listing

    rows = [
        listing(f'{base}-{i}', price, base_code=base)
        for base, price in [('original', 0.1), ('upgraded', 10), (None, 100)]
        for i in range(3)
    ]
    doc = build_bands(rows, [])
    tables = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': {'rows': []},
    }
    for i, price in [(0, 0.1), (3, 10)]:
        assert assess(from_listing(rows[i]), tables)['band']['q1_ist'] == price
    assert assess(from_listing(rows[6]), tables)['verdict'] == 'check'


def test_filled_unique_uses_bare_item_price_and_excludes_socketed_listing_premiums():
    rows = [listing(i, 0.6, ethereal=False, sockets=0, socket_contents='empty') for i in range(10)]
    rows += [listing(f'filled-{i}', 8, ethereal=False, sockets=1, socket_contents='filled') for i in range(10)]
    item = {'category': 'uniques', 'name': 'Example', 'ethereal': False, 'sockets': 1, 'socket_contents': 'filled'}
    result = assess(item, tables(rows))
    assert result['decision_ist'] == 0.6
    assert result['band']['sellers'] == 10
    assert result['reference_band']['sellers'] == 10
    assert item['sockets'] == 1
    assert item['socket_contents'] == 'filled'
    assert assess(item | {'ethereal': True}, tables(rows))['decision_ist'] is None
    assert assess(item, tables(rows[10:]))['decision_ist'] is None


def test_completed_runeword_still_prices_the_completed_socketed_item():
    rows = [
        listing(i, 8, ethereal=False, sockets=4, socket_contents='filled') | {'category': 'runewords'} for i in range(3)
    ]
    result = assess(
        {'category': 'runewords', 'name': 'Example', 'ethereal': False, 'sockets': 4, 'socket_contents': 'filled'},
        tables(rows),
    )
    assert result['decision_ist'] == 8


def test_unpriced_empty_listing_cannot_replace_excluded_filled_ask():
    rows = [listing('empty', None, ethereal=False, sockets=0, socket_contents='empty')]
    rows += [listing(i, 8, ethereal=False, sockets=1, socket_contents='filled') for i in range(3)]
    result = assess(
        {'category': 'uniques', 'name': 'Example', 'ethereal': False, 'sockets': 1, 'socket_contents': 'filled'},
        tables(rows),
    )
    assert result['verdict'] == 'check'
    assert result['decision_ist'] is None
