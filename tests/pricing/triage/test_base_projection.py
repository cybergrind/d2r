from pricing.triage.adapters import base_facets


def test_combined_and_elemental_resistance_have_identical_base_modifiers():
    combined = base_facets({'441': 45}, 'normal', 4, 'empty')
    elemental = base_facets(dict.fromkeys(('427', '428', '426', '401'), 45), 'normal', 4, 'empty')
    assert combined['base_modifiers'] == elemental['base_modifiers']
    different = base_facets({'441': 45, '427': 60}, 'normal', 4, 'empty')
    assert different['base_modifiers'] != combined['base_modifiers']


def test_empty_base_defense_and_inherent_undead_bonus_are_not_affixes():
    armor = {'category': 'armor'}
    mace = {'category': 'weapons', 'undead_damage_bonus': 50}
    assert base_facets({'399': 158}, 'normal', 3, 'empty', base=armor)['base_modifiers'] == {}
    assert base_facets({'1855': 158}, 'normal', 3, 'empty', base=armor)['base_modifiers'] == {}
    assert base_facets({'538': 50}, 'normal', 5, 'empty', base=mace)['base_modifiers'] == {}
    for props, rarity, contents, base in [
        ({'399': 158}, 'rare', 'empty', armor),
        ({'399': 158}, 'normal', 'filled', armor),
        ({'399': 158, '1855': 200}, 'normal', 'empty', armor),
        ({'538': 100}, 'normal', 'empty', mace),
        ({'538': 50}, 'normal', 'empty', {}),
    ]:
        assert base_facets(props, rarity, 3, contents, base=base)['base_modifiers']


def test_clean_shield_native_block_is_not_a_trade_modifier():
    from inventory_tracking.items.metadata import metadata

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Sacred Rondache')
    assert base['native_block'] == 28
    native = base_facets({'446': 28, '441': 45}, 'normal', 4, 'empty', base=base)
    listed = base_facets({'441': 45}, 'normal', 4, 'empty', base=base)
    assert native['base_modifiers'] == listed['base_modifiers']
    for value, rarity, contents in [(20, 'normal', 'empty'), (28, 'magic', 'empty'), (28, 'normal', 'filled')]:
        assert base_facets({'446': value}, rarity, 4, contents, base=base)['base_modifiers']['446'] == value


def test_paladin_shield_damage_is_not_superior_defense_and_remains_a_price_modifier():
    from inventory_tracking.items.metadata import metadata

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Sacred Targe')
    result = base_facets({'510': 65, '424': 121}, 'normal', 4, 'empty', base=base)
    assert result['base_ed'] == 0
    assert result['base_modifiers'] == {'510': 65, '424': 121}
    result = base_facets({'510': 65, '425': 15, '424': 121}, 'superior', 4, 'empty', base=base)
    assert result['base_ed'] == 15
    assert result['base_ed_grade'] == 'perfect'
    assert result['base_modifiers'] == {'510': 65, '424': 121}
    result = base_facets({'510': 65}, 'superior', 4, 'empty', base=base)
    assert result['base_ed'] is None


def test_default_base_policy_cannot_pool_inherent_damage_rolls():
    import json

    from inventory_tracking.items.metadata import metadata
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import build_bands
    from pricing.triage.engine import DATA, assess
    from pricing.triage.import_bases import compile_bucket
    from tests.pricing.triage.test_bands import listing

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Sacred Targe')
    rule = compile_bucket(base['name'], '4os/noneth/normal')
    policy = next(
        p
        for p in json.loads((DATA / 'rules.json').read_text())['policies']
        if p.get('category') == 'base' and 'name' not in p
    )
    rows = []
    for damage, price in [(30, 0.2), (65, 10)]:
        for i in range(3):
            row = listing(f'{damage}-{i}', price) | {
                'category': 'base',
                'name': base['name'],
                'base_code': base['code'],
                'rarity': 'normal',
                'ethereal': False,
                'sockets': 4,
                'socket_contents': 'empty',
            }
            row['properties'].update({'510': damage, '424': 121})
            rows.append(row)
    document = build_bands(rows, [], rules=[rule], policies=[policy])
    tables = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in document['bands']},
        'rules': {'keep_ist': 0.25, 'rows': [rule], 'policies': [policy]},
        'own': {'rows': []},
    }
    assert assess(from_listing(rows[0]), tables)['band']['q1_ist'] == 0.2
    assert assess(from_listing(rows[-1]), tables)['band']['q1_ist'] == 10


def test_verified_base_identity_selectors_are_not_item_modifiers():
    result = base_facets(
        {'1940': 'Grand Matron Bow', '930': 'Elite', '1216': False, '423': 3, '454': 3}, 'normal', 4, 'empty'
    )
    assert result['base_modifiers'] == {'423': 3, '454': 3}


def test_unreadable_enhancement_never_becomes_zero_or_a_known_modifier_signature():
    for category, prop, other in [('armor', '425', '510'), ('weapons', '510', '425')]:
        base = {'category': category}
        for rarity in ('normal', 'superior'):
            for unreadable in (None, 'unknown', False):
                result = base_facets({prop: unreadable}, rarity, 4, 'empty', base=base)
                assert result['base_ed'] is None
                assert result['base_ed_grade'] is None
            for unreadable in (None, 'unknown', False):
                result = base_facets({prop: 15, other: unreadable}, rarity, 4, 'empty', base=base)
                assert result['base_ed'] == 15
                assert result['base_modifiers'] is None
        assert base_facets({}, 'normal', 4, 'empty', base=base)['base_ed'] == 0
        assert base_facets({prop: 0}, 'normal', 4, 'empty', base=base)['base_ed'] == 0
    unknown_base = base_facets({'425': 15, '510': None}, 'normal', 4, 'empty')
    assert unknown_base['base_ed'] is None
