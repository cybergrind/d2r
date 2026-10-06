import pytest

from pricing.triage.adapters import from_listing
from pricing.triage.bands import build_bands
from pricing.triage.engine import assess
from tests.pricing.triage.test_bands import listing


@pytest.mark.parametrize(
    ('category', 'name', 'sockets'), [('uniques', 'Harlequin Crest', 0), ('sets', "Griswold's Heart", 3)]
)
def test_unmarked_named_listing_arrives_like_nonethereal_drop(category, name, sockets):
    row = listing('seller', 1)
    row.update(category=category, name=name, ethereal=None, sockets=None, socket_contents='unknown')
    item = from_listing(row)
    assert item['ethereal'] is False
    assert item['sockets'] == sockets
    assert item['socket_contents'] == 'empty'


def test_unmarked_equipment_listings_price_explicit_nonethereal_drop():
    rows = [listing(str(i), 1) for i in range(3)]
    for row in rows:
        row.update(category='uniques', name='Harlequin Crest', ethereal=None)
    document = build_bands(rows, [])
    tables = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in document['bands']},
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': {'rows': []},
    }
    item = {**from_listing(rows[0]), 'ethereal': False}
    assert assess(item, tables)['verdict'] == 'slow'
    assert assess({**item, 'ethereal': None}, tables)['verdict'] == 'check'


def test_explicit_equipment_facets_and_variable_native_sockets_are_preserved():
    row = listing('seller', 1)
    row.update(category='uniques', name='Harlequin Crest', ethereal=True, sockets=1, socket_contents='filled')
    item = from_listing(row)
    assert (item['ethereal'], item['sockets'], item['socket_contents']) == (True, 1, 'filled')
    row.update(name='Tomb Reaver', sockets=None, socket_contents='unknown')
    assert from_listing(row)['sockets'] is None


def test_named_listing_uses_verified_base_code_for_drop_family():
    row = listing('seller', 1)
    row.update(category='uniques', name='Harlequin Crest', base_code='uap')
    item = from_listing(row)
    assert item['base_name'] == 'Shako'
    assert item['family'] == 'helm'


def test_clean_base_listing_socket_count_is_usable_without_optional_contents_field():
    row = listing('seller', 1)
    row.update(category='base', name='Monarch', rarity='superior', sockets=4, socket_contents='unknown')
    row['properties']['425'] = 15
    item = from_listing(row)
    assert item['empty_sockets'] is True
    assert item['base_ed'] == 15
    for change in ({'rarity': None}, {'sockets': None}, {'rarity': 'magic'}):
        assert from_listing(row | change)['empty_sockets'] is None
    row['properties']['934'] = 'Jewel'
    row['socket_contents'] = 'filled'
    assert from_listing(row)['empty_sockets'] is False


@pytest.mark.parametrize(
    ('market_name', 'game_name', 'code'), [('Kris', 'Kriss', 'kri'), ('Stiletto', 'Stilleto', '9bl')]
)
def test_verified_catalog_spelling_alias_matches_the_captured_base(market_name, game_name, code):
    row = listing('seller', 1) | {'category': 'base', 'name': market_name, 'rarity': 'normal', 'sockets': 3}
    item = from_listing(row)
    assert (item['name'], item['base_code'], item['family']) == (game_name, code, 'knif')
    assert row['name'] == market_name
    rule = {'category': 'base', 'name': game_name, 'bucket': 'three', 'conditions': {'sockets': 3}}
    document = build_bands([row | {'seller_id': str(i), 'listing_id': str(i)} for i in range(3)], [], rules=[rule])
    tables = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in document['bands']},
        'rules': {'keep_ist': 0.25, 'rows': [rule]},
        'own': {'rows': []},
    }
    assert assess(item, tables)['verdict'] == 'slow'


def test_named_base_can_be_resolved_when_required_level_excludes_every_upgrade():
    row = listing('seller', 1) | {'category': 'sets', 'name': "Whitstan's Guard", 'base_code': None}
    row['properties']['796'] = 29
    item = from_listing(row)
    assert item['base_name'] == 'Round Shield'
    assert row['base_code'] is None
    row['properties']['796'] = 99
    assert from_listing(row)['base_code'] is None
    row['properties']['796'] = 1
    assert from_listing(row)['base_code'] is None
    row['properties'].update({'796': 29, '930': 'Elite'})
    assert from_listing(row)['base_code'] is None
    row['properties'].pop('930')
    row['properties']['1216'] = True
    assert from_listing(row)['base_code'] is None


@pytest.mark.parametrize('count', [None, 0])
def test_named_jewel_payload_prevents_zero_socket_default(count):
    row = listing('seller', 1) | {
        'category': 'uniques',
        'name': "Arreat's Face",
        'sockets': count,
        'socket_contents': 'filled',
        'properties': {'934': 'Jewel'},
    }
    item = from_listing(row)
    assert item['sockets'] == 1
    assert item['socket_contents'] == 'filled'
    assert row['sockets'] == count
    row['properties']['402'] = 2
    row['sockets'] = 2
    assert from_listing(row)['sockets'] == 2


def test_caster_amulet_recipe_overrides_legacy_rare_listing_selector_only():
    from inventory_tracking.items.metadata import metadata
    from pricing.triage.adapters import from_drop, from_listing
    from pricing.triage.listing_defaults import normalize

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Amulet')
    row = {
        'category': 'misc',
        'name': 'Amulet',
        'base_code': base['code'],
        'rarity': 'rare',
        'properties': {'797': 'rare', '520': 20, '400': 20, '569': 9, '514': 2},
    }
    result = normalize(row)
    assert result['rarity'] == 'crafted'
    assert result['facet_basis']['rarity']['kind'] == 'caster_amulet_recipe_signature'
    assert from_listing(row)['category'] == 'crafted'
    from pricing.triage.engine import assess
    from pricing.triage.import_affixed_rules import affixed_rules

    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    assert assess(from_listing(row), tables)['verdict'] == 'check'
    assert row['rarity'] == 'rare'
    for prop, value in [('520', 10), ('520', 14), ('520', 21), ('400', 9), ('569', 3), ('569', 11)]:
        assert normalize(row | {'properties': row['properties'] | {prop: value}})['rarity'] == 'rare'
    for prop in ('520', '400', '569'):
        assert (
            normalize(row | {'properties': {k: v for k, v in row['properties'].items() if k != prop}})['rarity']
            == 'rare'
        )
    assert normalize(row | {'name': 'Ring'})['rarity'] == 'rare'
    assert normalize(row | {'rarity': 'magic'})['rarity'] == 'magic'
    # A captured quality flag remains authoritative; this is a listing-only correction.
    assert from_drop({'item': {'name': 'Amulet', 'rarity': 'rare', 'base_code': base['code']}})['category'] == 'rare'


@pytest.mark.parametrize(
    ('market_name', 'game_name', 'code', 'family'),
    [
        ('Mithril Point', 'Mithral Point', '7di', 'knif'),
        ('Colossus Sword', 'Colossal Sword', '7fb', 'swor'),
        ('Large Siege Bow', 'Long Siege Bow', '8l8', 'bow'),
        ('Sabre', 'Saber', 'sbr', 'swor'),
        ('Griffon Headdress', 'Griffon Headress', 'dr7', 'pelt'),
        ('Hierophant Trophy', 'Heirophant Trophy', 'nea', 'head'),
        ('Ornate Plate', 'Ornate Armor', 'xar', 'tors'),
    ],
)
def test_localized_equipment_alias_reaches_rare_handler(market_name, game_name, code, family):
    row = listing('seller', 1) | {'category': 'base', 'name': market_name, 'rarity': 'rare'}
    item = from_listing(row)
    assert (item['name'], item['base_name'], item['base_code'], item['family']) == (game_name, game_name, code, family)
    conflicting = from_listing(row | {'base_code': 'rin'})
    assert conflicting['base_code'] == 'rin'
    assert conflicting['name'] == market_name


def test_verified_code_distinguishes_duplicate_native_base_names():
    from inventory_tracking.items.metadata import metadata

    bases = [b for b in metadata()['bases'].values() if b['name'] == 'Ancient Shield']
    assert len(bases) == 2
    for base in bases:
        row = listing('seller', 1) | {'category': 'base', 'name': base['name'], 'base_code': base['code']}
        assert from_listing(row)['family'] == base['type']


@pytest.mark.parametrize(('name', 'prop'), [('Archon Plate', '425'), ('Giant Thresher', '510')])
def test_plain_listing_with_superior_ed_is_not_priced_as_normal(name, prop):
    from inventory_tracking.items.metadata import metadata
    from pricing.triage.listing_defaults import normalize

    base = next(b for b in metadata()['bases'].values() if b['name'] == name)
    row = listing('seller', 1) | {
        'category': 'base',
        'name': name,
        'base_code': base['code'],
        'rarity': 'normal',
        'sockets': 4,
        'socket_contents': 'empty',
    }
    row['properties'][prop] = 13
    result = normalize(row)
    assert result['rarity'] == 'superior'
    assert result['facet_basis']['rarity']['reported'] == 'normal'
    assert row['rarity'] == 'normal'
    assert from_listing(row)['rarity'] == 'superior'
    assert normalize(row | {'properties': row['properties'] | {prop: 13.0}})['rarity'] == 'superior'
    for value in (0, 4, 13.5, 16, None, '13'):
        assert normalize(row | {'properties': row['properties'] | {prop: value}})['rarity'] == 'normal'
    for extra in ({'520': 10}, {'937': 30}, {'423': 100}, {'937': 10, '423': 3}):
        assert normalize(row | {'properties': row['properties'] | extra})['rarity'] == 'normal'
    for changes in ({'socket_contents': 'filled'}, {'rarity': 'rare'}, {'base_code': None}):
        assert normalize(row | changes)['rarity'] == changes.get('rarity', 'normal')


def test_inherent_paladin_damage_cannot_imply_superior_armor_quality():
    from inventory_tracking.items.metadata import metadata
    from pricing.triage.listing_defaults import normalize

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Sacred Targe')
    row = listing('seller', 1) | {
        'category': 'base',
        'name': base['name'],
        'base_code': base['code'],
        'rarity': 'normal',
        'sockets': 4,
        'socket_contents': 'empty',
    }
    row['properties']['510'] = 10
    assert normalize(row)['rarity'] == 'normal'


@pytest.mark.parametrize(
    ('name', 'properties'),
    [
        ('Kriss', {'510': 13, '1579': 3, '1574': 2, '937': 11}),
        ('Sacred Targe', {'425': 15, '441': 45}),
    ],
)
def test_superior_signature_preserves_legal_native_modifiers(name, properties):
    from inventory_tracking.items.metadata import metadata
    from pricing.triage.listing_defaults import normalize

    base = next(b for b in metadata()['bases'].values() if b['name'] == name)
    row = listing('seller', 1) | {
        'category': 'base',
        'name': name,
        'base_code': base['code'],
        'rarity': 'normal',
        'sockets': 3,
        'socket_contents': 'empty',
    }
    row['properties'].update(properties)
    assert normalize(row)['rarity'] == 'superior'
    assert normalize(row | {'properties': row['properties'] | {'520': 20}})['rarity'] == 'normal'
    assert normalize(row | {'rarity': None})['rarity'] is None
    assert normalize(row | {'socket_contents': 'filled'})['rarity'] == 'normal'
