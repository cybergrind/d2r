import json
import struct
from copy import deepcopy
from pathlib import Path

import pytest

from inventory_tracking.items.identity import IDENTIFIED_FLAG, RUNEWORD_FLAG, SOCKETED_FLAG, resolve_identity
from inventory_tracking.items.metadata import metadata


ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def recipes():
    rows = json.loads((ROOT / 'pricing/data/appraisal-definitions.json').read_text())['rows']
    return {r['name']: r for r in rows if r.get('rarity') == 'runeword'}


def capture(recipe, base_name, prefix=65535):
    bases = metadata()['bases']
    base = next(b for b in bases.values() if b['name'] == base_name)
    raw = bytearray(0x60)
    struct.pack_into('<I', raw, 0, 2)
    struct.pack_into('<I', raw, 0x18, IDENTIFIED_FLAG | RUNEWORD_FLAG | SOCKETED_FLAG)
    struct.pack_into('<H', raw, 0x48, prefix)
    children = []
    for position, code in enumerate(recipe['runes']):
        class_id = next(k for k, b in bases.items() if b['code'] == code)
        child_data = bytearray(0x60)
        struct.pack_into('<I', child_data, 0, 2)
        struct.pack_into('<I', child_data, 0x18, IDENTIFIED_FLAG)
        children.append(
            {
                'position': position,
                'item_data_hex': child_data.hex(),
                'unit': {
                    'type': 4,
                    'txt_id': int(class_id),
                    'unit_id': position + 1000,
                    'identity_stable': True,
                    'details': {'quality': 2},
                },
            }
        )
    arrays = {
        'item_data_hex': raw.hex(),
        'arrays': [{'header_offset': 0xE8, 'stats': [{'id': 194, 'layer': 0, 'raw': len(children)}]}],
        'socket_items': {'complete': True, 'children': children},
    }
    return {'quality': 2}, arrays, base


@pytest.mark.parametrize(('name', 'base'), [('Hustle (armor)', 'Mage Plate'), ('Hustle (weapon)', 'Phase Blade')])
@pytest.mark.parametrize('prefix', [27360, 65535])
def test_hustle_variant_comes_from_base_and_captured_recipe_not_a_guessed_prefix_id(recipes, name, base, prefix):
    # 27360 is the local d2go Hustle mapping; 65535 is deliberately unknown.
    details, arrays, item_base = capture(recipes[name], base, prefix)
    identity = resolve_identity(details, arrays, item_base)
    assert identity is not None
    assert identity['name'] == name
    assert identity['method'] == 'captured_recipe'
    assert identity['observed_table_id'] == prefix
    assert identity['table_id'] is None  # No new numerical mapping is asserted.
    if name.endswith('(weapon)'):
        assert identity['roll_ranges']['17']['min'] == 180
        assert identity['roll_ranges']['17']['max'] == 200
    else:
        assert '17' not in identity['roll_ranges']
        assert identity['roll_ranges']['93']['min'] == 40


def test_every_unmapped_recipe_is_retained_and_can_use_verified_children(recipes):
    pending = [r for r in recipes.values() if r['table_id'] is None]
    assert {r['name'] for r in metadata().get('unmapped_runewords', [])} == {r['name'] for r in pending}
    raw_bases = {}
    for table in ('weapons', 'armor'):
        raw_bases.update(json.loads((ROOT / f'pricing/raw/d2data/{table}.json').read_text()))
    for recipe in pending:
        base = next(
            b
            for b in metadata()['bases'].values()
            if b['code'] in recipe['base_codes']
            and raw_bases.get(b['code'], {}).get('gemsockets', 0) >= len(recipe['runes'])
        )
        details, arrays, base = capture(recipe, base['name'])
        assert resolve_identity(details, arrays, base)['name'] == recipe['name']


@pytest.mark.parametrize(
    'failure',
    [
        'partial',
        'order',
        'missing',
        'duplicate_unit',
        'wrong_type',
        'unstable_child',
        'non_rune',
        'count',
        'flag',
        'unidentified',
    ],
)
def test_recipe_recognition_requires_complete_ordered_runes_and_runeword_flags(recipes, failure):
    details, arrays, base = capture(recipes['Hustle (weapon)'], 'Phase Blade')
    children = arrays['socket_items']['children']
    if failure == 'partial':
        arrays['socket_items']['complete'] = False
    elif failure == 'order':
        children[0]['unit'], children[1]['unit'] = children[1]['unit'], children[0]['unit']
    elif failure == 'missing':
        children.pop()
    elif failure == 'duplicate_unit':
        children[1]['unit']['unit_id'] = children[0]['unit']['unit_id']
    elif failure == 'wrong_type':
        children[0]['unit']['type'] = 1
    elif failure == 'unstable_child':
        children[0]['unit']['identity_stable'] = False
    elif failure == 'non_rune':
        children[0]['unit']['txt_id'] = int(next(k for k, b in metadata()['bases'].items() if b['name'] == 'Jewel'))
    elif failure == 'count':
        arrays['arrays'][0]['stats'][0]['raw'] = 2
    else:
        raw = bytearray.fromhex(arrays['item_data_hex'])
        flags = IDENTIFIED_FLAG if failure == 'flag' else RUNEWORD_FLAG
        struct.pack_into('<I', raw, 0x18, flags)
        arrays['item_data_hex'] = raw.hex()
    assert resolve_identity(details, arrays, base) is None


def test_recipe_cannot_exceed_native_socket_capacity(recipes):
    for base_name in ('Dagger', 'Quilted Armor'):
        details, arrays, base = capture(recipes['Hustle (weapon)'], base_name)
        assert resolve_identity(details, arrays, base) is None


def test_known_prefix_cannot_override_contradictory_complete_children(recipes):
    details, arrays, base = capture(recipes['Spirit'], 'Monarch', recipes['Spirit']['table_id'])
    assert resolve_identity(details, arrays, base)['name'] == 'Spirit'
    arrays['socket_items']['children'][0]['unit']['txt_id'] = int(
        next(k for k, b in metadata()['bases'].items() if b['name'] == 'El Rune')
    )
    assert resolve_identity(details, arrays, base) is None


def test_ambiguous_recipes_remain_unresolved(recipes, monkeypatch):
    import inventory_tracking.items.identity as identity_module

    document = deepcopy(metadata())
    duplicate = {**recipes['Hustle (weapon)'], 'name': 'Ambiguous fixture'}
    document.setdefault('unmapped_runewords', []).append(duplicate)
    monkeypatch.setattr(identity_module, 'metadata', lambda: document)
    details, arrays, base = capture(recipes['Hustle (weapon)'], 'Phase Blade')
    assert resolve_identity(details, arrays, base) is None


def test_unreadable_flagged_runeword_is_reported_as_an_issue():
    from inventory_tracking.items.decode import decode_items
    from pricing.knowledge.assessment.adapters.capture import normalize

    data = json.loads((ROOT / 'tests/inventory_tracking/fixtures/spirit_monarch.json').read_text())
    row = data['snapshot']['resources']['items'][0]
    raw = bytearray.fromhex(row['resource_stats']['item_data_hex'])
    struct.pack_into('<H', raw, 0x48, 65535)
    row['resource_stats']['item_data_hex'] = raw.hex()
    row['resource_stats'].pop('socket_items', None)
    result = decode_items(data['snapshot'], data['report'], inventory_page=row['details']['inventory_page'])[0]
    assert 'Runeword identity could not be read.' in result['issues']
    assert result['source']['runeword_identity_unresolved'] is True
    assert 'Runeword identity is unresolved.' in normalize(result).gaps


@pytest.mark.parametrize(
    ('name', 'base_name', 'stat'),
    [
        ('Hustle (armor)', 'Mage Plate', {'id': 93, 'layer': 0, 'raw': 40}),
        ('Hustle (weapon)', 'Phase Blade', {'id': 17, 'layer': 0, 'raw': 190}),
    ],
)
def test_recipe_identity_reaches_report_ranges_and_preserves_its_evidence(recipes, name, base_name, stat):
    from inventory_tracking.items.decode import decode_items
    from pricing.knowledge.assessment.adapters.capture import normalize

    data = json.loads((ROOT / 'tests/inventory_tracking/fixtures/spirit_monarch.json').read_text())
    row = data['snapshot']['resources']['items'][0]
    _, arrays, base = capture(recipes[name], base_name)
    row['txt_id'] = int(next(k for k, b in metadata()['bases'].items() if b['code'] == base['code']))
    row['details']['quality'] = 2
    row['resource_stats'].update(arrays)
    row['resource_stats']['arrays'][0]['stats'].append(stat)
    if name.endswith('(weapon)'):
        row['resource_stats']['arrays'][0]['stats'].append({'id': 18, 'layer': 0, 'raw': 190})
    result = decode_items(data['snapshot'], data['report'], inventory_page=row['details']['inventory_page'])[0]
    assert result['item']['runeword'] == name
    assert result['source']['item_identity'] == {
        'table': 'runeword',
        'table_id': None,
        'offset': 0x48,
        'method': 'captured_recipe',
        'observed_table_id': 65535,
    }
    assert result['item']['filled_sockets'] == 3
    assert result['item']['empty_sockets'] == 0
    assert normalize(result).runeword == name
    if name.endswith('(weapon)'):
        assert any('+190% (180-200%) Enhanced Damage' in r['text'] for r in result['decoded_stats'])
    assert 'Runeword identity could not be read.' not in result['issues']


@pytest.mark.parametrize('quality', [1, 2, 3])
def test_verified_recipe_identity_supports_all_nonmagical_native_qualities(recipes, quality):
    # D2MOO ITEMS_GetRunesTxtRecordFromItem rejects MAGIC..TEMPERED, not INFERIOR.
    # Require the actual runeword flag and verified recipe; quality alone is no
    # evidence that a low-quality unsocketed base can become this runeword.
    details, arrays, base = capture(recipes['Spirit'], 'Monarch')
    data = bytearray.fromhex(arrays['item_data_hex'])
    struct.pack_into('<I', data, 0, quality)
    arrays['item_data_hex'] = data.hex()
    details['quality'] = quality
    result = resolve_identity(details, arrays, base)
    assert result is not None
    assert result['name'] == 'Spirit'
    assert result['method'] == 'captured_recipe'
    arrays['socket_items']['children'].reverse()
    assert resolve_identity(details, arrays, base) is None
