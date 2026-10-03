from inventory_tracking.items.metadata import metadata
from pricing.triage.adapters import from_listing
from pricing.triage.bands import build_bands
from pricing.triage.engine import assess
from pricing.triage.import_bases import native_shield_rules
from tests.pricing.triage.test_bands import listing


def test_native_damage_shield_compares_both_rolls_and_preserves_variants():
    rules, policies = native_shield_rules()
    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Sacred Targe')
    rows = []
    for n, (damage, attack, price) in enumerate(
        [(51, 101, 1), (55, 105, 2), (60, 110, 3), (65, 121, 100), (65, 101, 90), (51, 121, 80)]
    ):
        row = listing(str(n), price) | {
            'category': 'base',
            'name': 'Sacred Targe',
            'base_code': base['code'],
            'rarity': 'normal',
            'sockets': 4,
        }
        row['properties'].update({'510': damage, '423': attack})
        rows.append(row)
    document = build_bands(rows, [], rules=rules, policies=policies)
    tables = {
        'rules': {'keep_ist': 0.25, 'rows': rules, 'policies': policies},
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in document['bands']},
        'own': {'rows': []},
    }
    result = assess(from_listing(rows[2]), tables)
    assert result['verdict'] == 'slow'
    assert result['band']['sellers'] == 3
    assert result['band']['q1_ist'] == 1.5
    assert assess(from_listing(rows[0]), tables)['verdict'] == 'check'
    for change in ({'sockets': 2}, {'sockets': None}, {'ethereal': True}, {'socket_contents': 'filled'}):
        assert assess(from_listing(rows[2] | change), tables)['band'] is None
    for props in ({'510': 60}, {'423': 110}, {'510': 50, '423': 100}):
        result = assess(from_listing(rows[2] | {'properties': props}), tables)
        assert result['verdict'] == 'vendor'
