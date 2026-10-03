import json

from pricing.triage.adapters import expanded_properties, from_drop
from pricing.triage.engine import DATA, matches


def capture(code, stat, value):
    return {
        'item': {'base_code': code, 'name': 'Example', 'rarity': 'unique', 'affixes': []},
        'source': {},
        'decoded_stats': [
            {
                'status': 'decoded',
                'value': value,
                'name': 'armorclass',
                'memory_stat': {'id': stat, 'layer': 0, 'raw': value},
            }
        ],
    }


def test_total_armor_defense_is_available_without_relabeling_flat_ring_defense():
    assert from_drop(capture('uap', 31, 130))['properties']['1855'] == 130
    assert '1855' not in from_drop(capture('rin', 31, 10))['properties']


def test_all_resistance_floor_requires_all_four_components():
    assert expanded_properties({'427': 30, '428': 25, '426': 25, '401': 25})['441'] == 25
    assert '441' not in expanded_properties({'427': 30, '428': 25, '426': 25})


def test_imported_named_rules_distinguish_percent_from_flat_reduction_and_absorb():
    rows = json.loads((DATA / 'rules.json').read_text())['rows']
    cases = [
        ("Verdungo's Hearty Cord", 'vit>=38 & PDR 15', {'582': 40, '1865': 15}, '1865', '413'),
        ('Wisp Projector', '20 MF & 20 absorb', {'461': 20, '1866': 20}, '1866', '689'),
    ]
    for name, bucket, props, percent, flat in cases:
        rule = next(r for r in rows if r.get('name') == name and r.get('bucket') == bucket)
        item = {'category': 'uniques', 'name': name, 'properties': props}
        assert matches(item, rule)
        assert not matches(item | {'properties': {flat if k == percent else k: v for k, v in props.items()}}, rule)


def test_recognized_named_pattern_without_a_price_remains_check():
    from pricing.triage.engine import assess

    rows = json.loads((DATA / 'rules.json').read_text())['rows']
    rules = [r for r in rows if r.get('name') == "Verdungo's Hearty Cord"]
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': rules}, 'own': {'rows': []}}
    item = {'category': 'uniques', 'name': "Verdungo's Hearty Cord", 'properties': {'582': 31, '1865': 12}}
    assert assess(item, tables)['verdict'] == 'check'
    assert assess(item | {'properties': {}}, tables)['verdict'] == 'check'
