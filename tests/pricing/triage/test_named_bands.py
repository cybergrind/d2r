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
        {**listing(i, price), 'ethereal': eth}
        for i, (price, eth) in enumerate(
            [(0.674, None), (0.789, None), (2.585, None), (11.421, True), (11.421, True), (79.947, True)]
        )
    ]
    result = assess({'category': 'uniques', 'name': 'Example', 'ethereal': False}, tables(rows))
    assert result['verdict'] == 'vendor'
    assert result['band'] is None or result['band']['median_ist'] is None
    assert result['reference_band']['median_ist'] == 7.003
    assert 'non-ethereal' in result['reason']
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
    low = assess({'category': 'uniques', 'name': 'Example', 'properties': {'425': 100}}, data)
    assert low['verdict'] == 'vendor'
    assert low['band']['median_ist'] == 0.1
    assert low['band']['sellers'] == 3
    high = assess({'category': 'uniques', 'name': 'Example', 'properties': {'425': 120}}, data)
    assert high['verdict'] == 'slow'
    assert high['band']['median_ist'] == 10
    missing = assess({'category': 'uniques', 'name': 'Example'}, data)
    assert missing['bucket'] == 'name|ethereal:unknown'


def test_runeword_base_and_ethereal_are_both_required_for_price():
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
    for change in [{'base_code': 'base-b'}, {'base_code': None}, {'ethereal': False}, {'ethereal': None}]:
        result = assess({**good, **change}, data)
        assert result['verdict'] == 'vendor'
        assert result['band'] is None


def test_required_roll_bucket_cannot_fall_back_to_mixed_name_price():
    rules = [{'category': 'uniques', 'name': 'Example', 'bucket': 'perfect', 'properties': {'425': 120}}]
    policies = [{'category': 'uniques', 'name': 'Example', 'require_bucket': True}]
    rows = [{**listing(i, 10), 'properties': {**listing(i)['properties'], '425': 120}} for i in range(3)]
    doc = build_bands(rows, [], rules=rules, policies=policies)
    data = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': rules, 'policies': policies},
        'own': {'rows': []},
    }
    assert assess({'category': 'uniques', 'name': 'Example', 'properties': {'425': 120}}, data)['verdict'] == 'slow'
    for props in ({}, {'425': 100}):
        result = assess({'category': 'uniques', 'name': 'Example', 'properties': props}, data)
        assert result['verdict'] == 'vendor'
        assert result['band'] is None


def test_thin_premium_roll_bucket_does_not_borrow_ordinary_roll_band():
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
    assert assess({'category': 'uniques', 'name': 'Example', 'properties': {'425': 120}}, data)['band'] is None


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
    rows = [listing(i, 10) for i in range(3)]
    result = assess({'category': 'uniques', 'name': 'Example', 'ethereal': False}, tables(rows))
    assert result['band'] is None or result['band']['median_ist'] is None
    assert result['verdict'] == 'vendor'
    assert result['reference_band']['median_ist'] == 10
    unknown = assess({'category': 'uniques', 'name': 'Example', 'ethereal': None}, tables(rows))
    assert unknown['band']['median_ist'] == 10
