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
    lower = assess(from_listing(rows[0]), tables)
    assert lower['verdict'] == 'slow'
    assert lower['band']['price_basis'] == 'base_floor'
    relaxed = assess(from_listing(rows[2] | {'sockets': 2}), tables)
    assert relaxed['decision_ist'] == 1.5
    assert relaxed['band']['relaxed_facets'] == ['base_ed', 'sockets']
    for change in ({'sockets': None}, {'ethereal': True}, {'socket_contents': 'filled'}):
        assert assess(from_listing(rows[2] | change), tables)['band'] is None
    for props in ({'510': 60}, {'423': 110}):
        result = assess(from_listing(rows[2] | {'properties': props}), tables)
        assert result['verdict'] == 'vendor'
    lower = assess(from_listing(rows[2] | {'properties': {'510': 50, '423': 100}}), tables)
    assert lower['band']['price_basis'] == 'base_floor'


def test_guide_native_damage_shield_remains_check_without_matching_asks():
    from pricing.triage.guide_cases import item_from_spec

    rules, policies = native_shield_rules()
    tables = {'bands': {}, 'rules': {'rows': rules, 'policies': policies, 'keep_ist': 0.25}, 'own': {'rows': []}}
    for name in ('Sacred Targe', 'Sacred Rondache'):
        for ethereal in (False, True):
            spec = {
                'base': name,
                'rarity': 'normal',
                'ethereal': ethereal,
                'sockets': 4,
                'stats': {'17:0': 51, '18:0': 51, '19:0': 101},
            }
            result = assess(item_from_spec(spec), tables)
            assert result['verdict'] == 'check'
            assert result['decision_ist'] is None
            assert 'fewer than three sellers' in result['reason']
            assert assess(item_from_spec(spec | {'socket_contents': 'filled'}), tables)['verdict'] == 'vendor'
            weak = spec | {'stats': {'17:0': 50, '18:0': 50, '19:0': 100}}
            assert assess(item_from_spec(weak), tables)['verdict'] == 'vendor'


def test_superior_durability_does_not_disable_joint_shield_roll_comparisons():
    rules, policies = native_shield_rules()
    for policy in policies:
        policy['compare_modifiers'] = {'937': {'min': 10, 'max': 15, 'label': '% maximum durability'}}
    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Sacred Targe')
    rows = []
    for n, (damage, attack, durability, price) in enumerate(
        [(51, 101, 10, 1), (55, 105, 11, 2), (60, 110, 12, 3), (65, 121, 15, 100)]
    ):
        row = listing(str(n), price) | {
            'category': 'base',
            'name': base['name'],
            'base_code': base['code'],
            'rarity': 'superior',
            'sockets': 4,
            'ethereal': False,
        }
        row['properties'].update({'425': 15, '510': damage, '423': attack, '937': durability})
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
    assert result['decision_ist'] == 1.5
    lower = assess(from_listing(rows[0]), tables)
    assert lower['decision_ist'] == 1.75
    assert lower['band']['price_basis'] == 'base_floor'
    assert assess(from_listing(rows[2] | {'ethereal': True}), tables)['decision_ist'] is None
