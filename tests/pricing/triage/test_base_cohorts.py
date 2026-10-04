from pricing.triage.adapters import from_listing
from pricing.triage.bands import build_bands
from pricing.triage.engine import assess
from pricing.triage.market_bases import FACETS
from tests.pricing.triage.test_bands import listing


POLICY = {
    'category': 'base',
    'require_bucket': True,
    'facets': FACETS,
    'compare_modifiers': {'937': {'min': 10, 'max': 15, 'label': 'durability'}},
}
RULE = {
    'category': 'base',
    'name': 'Archon Plate',
    'bucket': 'armor',
    'conditions': {'sockets': 4, 'ethereal': True, 'rarity': 'superior', 'empty_sockets': True},
}


def row(seller, durability, price):
    r = listing(seller, price) | {
        'category': 'base',
        'name': 'Archon Plate',
        'rarity': 'superior',
        'sockets': 4,
        'ethereal': True,
    }
    r['properties'].update({'425': 15, '937': durability})
    return r


def tables(rows):
    doc = build_bands(rows, [], rules=[RULE], policies=[POLICY])
    return {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': [RULE], 'policies': [POLICY]},
        'own': {'rows': []},
    }


def test_secondary_durability_rolls_merge_when_split_lacks_sellers():
    rows = [row(str(i), 10 + i, 2) for i in range(3)]
    data = tables(rows)
    result = assess(from_listing(rows[0]), data)
    assert result['verdict'] == 'slow'
    assert result['band']['sellers'] == 3
    assert result['decision_ist'] == 2
    for change in ({'ethereal': False}, {'sockets': 3}, {'base_modifiers': {'937': 10, '441': 45}}):
        assert assess(from_listing(rows[0]) | change, data)['band'] is None


def test_supported_secondary_price_difference_stays_split():
    rows = [row(str(i), 10, 1) for i in range(3)] + [row(str(i + 3), 15, 10) for i in range(3)]
    data = tables(rows)
    assert assess(from_listing(rows[0]), data)['decision_ist'] == 1
    assert assess(from_listing(rows[-1]), data)['decision_ist'] == 10


def test_declared_base_roll_range_pools_sellers_without_weakening_required_range():
    rule = {
        'category': 'base',
        'name': 'Sacred Targe',
        'bucket': 'resistance',
        'conditions': {'sockets': 4, 'ethereal': False, 'rarity': 'normal', 'empty_sockets': True},
        'properties': {'441': {'min': 40, 'max': 44}},
    }
    rows = []
    for i, resistance in enumerate((40, 41, 42)):
        r = listing(str(i), 2) | {
            'category': 'base',
            'name': 'Sacred Targe',
            'rarity': 'normal',
            'sockets': 4,
            'ethereal': False,
        }
        r['properties']['441'] = resistance
        rows.append(r)
    doc = build_bands(rows, [], rules=[rule], policies=[POLICY])
    data = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': [rule], 'policies': [POLICY]},
        'own': {'rows': []},
    }
    result = assess(from_listing(rows[0]), data)
    assert result['verdict'] == 'slow'
    assert result['band']['sellers'] == 3
    assert assess(from_listing(rows[0] | {'properties': rows[0]['properties'] | {'441': 39}}), data)['band'] is None
