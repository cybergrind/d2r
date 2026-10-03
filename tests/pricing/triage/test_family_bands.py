from pricing.triage.adapters import from_listing
from pricing.triage.bands import build_bands
from pricing.triage.engine import assess
from tests.pricing.triage.test_bands import listing


RULE = {
    'category': 'magic',
    'name': 'Small Charm',
    'bucket': 'fine-life',
    'properties': {'448': 3, '423': {'min': 10, 'max': 20}, '418': {'min': 16, 'max': 20}},
    'pattern': {'properties': {'448': {'min': 1}, '423': {'min': 1}, '418': {'min': 1}}},
}


def charm(seller, life, price):
    row = listing(seller, price)
    row.update(name='Small Charm', category='charms', rarity='magic')
    row['properties'].update({'448': 3, '423': 18, '418': life})
    return row


def test_family_band_prices_matching_rolls_without_borrowing_perfect_asks():
    rows = [charm(i, 17, 2) for i in range(3)] + [charm(i + 3, 20, 50) for i in range(3)]
    document = build_bands(rows, [], rules=[RULE])
    tables = {
        'bands': {(r['category'], r['name'].casefold(), r['bucket']): r for r in document['bands']},
        'rules': {'keep_ist': 0.25, 'rows': [RULE]},
        'own': {'rows': []},
    }
    result = assess(from_listing(rows[0]), tables)
    assert result['decision_ist'] == 2
    assert result['band']['sellers'] == 3
    assert result['verdict'] == 'slow'
    unseen = from_listing(charm(10, 16, 1))
    result = assess(unseen, tables)
    assert result['band'] is None
    assert result['verdict'] == 'check'
    assert result['reference_band']['median_ist'] == 26


def test_family_band_does_not_pool_stacks_or_sellers():
    rows = [charm(1, 17, 2), {**charm(1, 17, 100), 'listing_id': 'second'}, {**charm(2, 17, 50), 'amount': 40}]
    document = build_bands(rows, [], rules=[RULE])
    bands = [r for r in document['bands'] if r['category'] == 'family' and r.get('roll_properties')]
    assert len(bands) == 1
    assert bands[0]['sellers'] == 1
    assert bands[0]['median_ist'] == 2
