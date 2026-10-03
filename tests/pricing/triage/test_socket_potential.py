from pricing.triage.socket_potential import preparation


def test_known_level_and_quality_control_socket_outcomes_without_pricing():
    rules = {'socket_caps': {'Example': [3, 4, 6]}}
    item = {'category': 'base', 'name': 'Example', 'rarity': 'normal', 'sockets': 0, 'item_level': 30}
    result = preparation(item, rules)
    assert result == {'larzuk': [4], 'cube': [1, 2, 3, 4], 'conditional': False}
    assert preparation(item | {'rarity': 'superior'}, rules)['cube'] == []
    assert preparation(item | {'item_level': None}, rules) == {
        'larzuk': [3, 4, 6],
        'cube': [1, 2, 3, 4, 5, 6],
        'conditional': True,
    }
    for change in ({'sockets': None}, {'sockets': 2}, {'rarity': 'magic'}, {'category': 'runewords'}):
        assert preparation(item | change, rules) is None


def test_socket_preparation_is_visible_without_changing_the_price_or_verdict():
    from inventory_tracking.appraisal.triage import headline
    from pricing.triage.engine import assess

    tables = {
        'rules': {'rows': [], 'keep_ist': 0.25, 'socket_caps': {'Example': [3, 4, 6]}},
        'bands': {},
        'own': {'rows': []},
    }
    item = {'category': 'base', 'name': 'Example', 'rarity': 'superior', 'sockets': 0, 'item_level': 30}
    result = assess(item, tables)
    assert result['verdict'] == 'vendor'
    assert result['band'] is None
    assert headline(result).endswith('Larzuk: 4 sockets')
    unknown = assess(item | {'item_level': None, 'rarity': 'normal'}, tables)
    assert 'Larzuk: 3/4/6 sockets (item level unknown)' in headline(unknown)
    assert 'cube: 1-6 sockets' in headline(unknown)


def test_unsocketed_paid_pattern_requires_a_possible_preparation_outcome():
    from pricing.triage.engine import assess

    rule = {
        'category': 'base',
        'name': 'Example',
        'properties': {'765': 3},
        'pattern': {'conditions': {'sockets': 0, 'rarity': {'in': ['normal', 'superior']}}, 'properties': {'765': 3}},
        'pattern_label': 'Unsocketed paid base; needs three sockets',
        'required_socket_counts': [3],
    }
    tables = {
        'rules': {'rows': [rule], 'keep_ist': 0.25, 'socket_caps': {'Example': [2, 3, 3]}},
        'bands': {},
        'own': {'rows': []},
    }
    item = {'category': 'base', 'name': 'Example', 'rarity': 'normal', 'sockets': 0, 'properties': {'765': 3}}
    assert assess(item | {'item_level': 20}, tables)['verdict'] == 'vendor'
    for level in (None, 30):
        result = assess(item | {'item_level': level}, tables)
        assert result['verdict'] == 'check'
        assert result['band'] is None
    assert assess(item | {'properties': {'765': 2}}, tables)['verdict'] == 'vendor'
    tables['rules']['socket_caps']['Example'] = [5, 6, 6]
    rule['required_socket_counts'] = [4, 5]
    assert assess(item | {'item_level': 80}, tables)['verdict'] == 'check'
    assert assess(item | {'item_level': 80, 'rarity': 'superior'}, tables)['verdict'] == 'vendor'
    assert assess(item | {'item_level': 20, 'rarity': 'superior'}, tables)['verdict'] == 'check'
    tables['rules']['socket_caps'] = {}
    assert assess(item, tables)['verdict'] == 'vendor'


def test_generated_unsocketed_rule_uses_zero_socket_capture_without_borrowing_price():
    from pricing.triage.adapters import from_listing
    from pricing.triage.engine import assess
    from pricing.triage.import_bases import staffmod_rules
    from tests.pricing.triage.test_bands import listing

    rules, policies = staffmod_rules()
    row = listing('helm', 1) | {'category': 'base', 'name': 'Fanged Helm', 'rarity': 'normal', 'sockets': 0}
    row['properties']['765'] = 3
    tables = {
        'rules': {'rows': rules, 'policies': policies, 'keep_ist': 0.25, 'socket_caps': {'Fanged Helm': [2, 3, 3]}},
        'bands': {},
        'own': {'rows': []},
    }
    item = from_listing(row)
    result = assess(item | {'item_level': 40}, tables)
    assert result['verdict'] == 'check'
    assert 'needs 3 sockets' in result['reason']
    assert result['band'] is None
    assert assess(item | {'item_level': 20}, tables)['verdict'] == 'vendor'


def test_unsocketed_abyss_and_bone_spear_need_attainable_sockets():
    from pricing.triage.adapters import from_listing
    from pricing.triage.engine import assess
    from pricing.triage.import_bases import staffmod_rules
    from tests.pricing.triage.test_bands import listing

    rules, policies = staffmod_rules()
    for name, prop, skill in [('Blasphemous Grimoire', '1579', 'Abyss'), ('Bone Wand', '756', 'Bone Spear')]:
        row = listing('caster-base', 1) | {'category': 'base', 'name': name, 'rarity': 'normal', 'sockets': 0}
        row['properties'][prop] = 3
        item = from_listing(row) | {'item_level': 80}
        tables = {
            'rules': {'rows': rules, 'policies': policies, 'keep_ist': 0.25, 'socket_caps': {name: [2, 2, 2]}},
            'bands': {},
            'own': {'rows': []},
        }
        result = assess(item, tables)
        assert result['verdict'] == 'check'
        assert f'+3 {skill}' in result['reason']
        assert 'needs 2 sockets' in result['reason']
        assert result['band'] is None
        assert assess(item | {'properties': {prop: 2}}, tables)['verdict'] == 'vendor'
        tables['rules']['socket_caps'][name] = [1, 1, 1]
        assert assess(item, tables)['verdict'] == 'vendor'
