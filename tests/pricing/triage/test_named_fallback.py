from pricing.triage.bands import build_bands
from pricing.triage.engine import assess
from tests.pricing.triage.test_bands import listing


def tables(rows, rules=(), policies=()):
    bands = build_bands(rows, [], rules=rules, policies=policies)['bands']
    return {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in bands},
        'rules': {'keep_ist': 0.25, 'rows': list(rules), 'policies': list(policies)},
        'own': {'rows': []},
    }


def row(seller, price, **facets):
    return listing(seller, price) | {
        'ethereal': False,
        'base_code': 'base-a',
        'sockets': 0,
        'socket_contents': 'empty',
        **facets,
    }


def item(**facets):
    return {
        'category': 'uniques',
        'name': 'Example',
        'ethereal': False,
        'base_code': 'base-a',
        'sockets': 1,
        'socket_contents': 'empty',
        **facets,
    }


def test_named_fallback_drops_sockets_then_base_but_not_ethereal():
    data = tables([row(i, 1) for i in range(3)])
    for change in ({}, {'base_code': 'base-b'}):
        result = assess(item(**change), data)
        assert result['verdict'] == 'slow'
        assert result['band']['sellers'] == 3
    assert assess(item(ethereal=True), data)['verdict'] == 'check'
    assert assess(item(ethereal=None), data)['verdict'] == 'check'


def test_named_exact_cohort_wins_and_expensive_socket_variant_is_protected():
    rows = [row(i, 0.1) for i in range(10)] + [row(20, 5, sockets=1)]
    data = tables(rows)
    assert assess(item(sockets=0), data)['verdict'] == 'vendor'
    assert assess(item(), data)['verdict'] == 'check'
    assert assess(item(sockets=None, socket_contents=None), data)['verdict'] == 'check'


def test_named_low_price_is_not_overridden_by_paid_pattern():
    rules = [
        {
            'category': 'uniques',
            'name': 'Example',
            'properties': {'425': 100},
            'pattern': {'properties': {'425': {'min': 1}}},
            'pattern_label': 'Paid roll',
        }
    ]
    data = tables([row(i, 0.1) for i in range(3)], rules)
    assert assess(item(sockets=0, properties={'425': 80}), data)['verdict'] == 'vendor'


def test_paid_named_pattern_uses_supported_broader_band():
    rules = [
        {
            'category': 'uniques',
            'name': 'Example',
            'bucket': 'high',
            'properties': {'425': 120},
            'pattern': {'properties': {'425': {'min': 1}}},
        }
    ]
    policies = [{'category': 'uniques', 'name': 'Example', 'require_bucket': True}]
    data = tables([row(i, 1, properties=listing(i)['properties'] | {'425': 100}) for i in range(3)], rules, policies)
    assert assess(item(properties={'425': 99}), data)['verdict'] == 'slow'


def test_plain_nonethereal_item_uses_cheap_name_despite_one_optimistic_base_ask():
    rows = [row(i, 0.1, base_code=None) for i in range(9)] + [row(10, 6)]
    result = assess(item(sockets=0), tables(rows))
    assert result['verdict'] == 'vendor'
    assert result['band']['sellers'] == 10
