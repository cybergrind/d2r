import copy
import json
from pathlib import Path

import pytest

from inventory_tracking.items.decode import decode_rings


@pytest.fixture
def capture():
    return json.loads((Path(__file__).parents[1] / 'fixtures/appraisal_ring.json').read_text())


def test_captured_ring_decodes_scaled_stamina_and_fcr(capture):
    rows = decode_rings(capture['snapshot'], capture['report'])
    assert len(rows) == 1
    item = rows[0]['item']
    assert item['name'] == 'Ring'
    assert item['rarity'] == 'magic'
    assert {a['property_id']: a['value'] for a in item['affixes']} == {'452': 11, '520': 10}
    assert item['requirements'] == {}
    assert rows[0]['appraisal_ready'] is False
    assert rows[0]['source']['unit_id'] == 438836750
    assert rows[0]['source']['snapshot_only'] is True


@pytest.mark.parametrize('failure', ['build', 'unstable', 'arrays', 'owner'])
def test_untrusted_capture_cannot_produce_item_facts(capture, failure):
    if failure == 'build':
        capture['report']['game']['executable_fingerprint']['sha256'] = 'different'
    elif failure == 'unstable':
        capture['snapshot']['status'] = 'stale'
    elif failure == 'arrays':
        capture['snapshot']['resources']['items'][0]['resource_stats']['complete'] = False
    else:
        capture['snapshot']['resources']['items'][0]['details']['owner_id'] = -1
    with pytest.raises(ValueError, match=r'Unsupported|stale|missing|No owned'):
        decode_rings(capture['snapshot'], capture['report'])


def test_unknown_stats_remain_explicit_and_duplicate_stats_are_not_summed(capture):
    stats = capture['snapshot']['resources']['items'][0]['resource_stats']['arrays'][2]['stats']
    stats.append({'id': 999, 'layer': 3, 'raw': 25})
    stats.append(copy.deepcopy(stats[0]))
    result = decode_rings(capture['snapshot'], capture['report'])[0]
    assert [a['property_id'] for a in result['item']['affixes']] == ['520']
    assert len(result['unresolved_stats']) == 3
    assert result['appraisal_ready'] is False


def test_nonzero_layer_and_fractional_stamina_are_not_guessed(capture):
    stats = capture['snapshot']['resources']['items'][0]['resource_stats']['arrays'][2]['stats']
    stats[0]['raw'] += 1
    stats[1]['layer'] = 1
    assert decode_rings(capture['snapshot'], capture['report'])[0]['item']['affixes'] == []


@pytest.fixture
def crowbill():
    return json.loads((Path(__file__).parents[1] / 'fixtures/tancred_crowbill.json').read_text())


def test_captured_crowbill_name_and_missing_enhanced_damage_are_explicit(crowbill):
    from inventory_tracking.items.decode import decode_items

    result = decode_items(crowbill['snapshot'], crowbill['report'])[0]
    assert result['item']['name'] == "Tancred's Crowbill"
    assert result['item']['base_name'] == 'Military Pick'
    assert result['item']['set_name'] == "Tancred's Battlegear"
    assert result['source']['item_identity']['table_id'] == 30
    assert result['source']['item_identity']['offset'] == 0x34
    assert any('Enhanced Damage' in note and 'not captured' in note for note in result['review'])
    assert not any(a['property_id'] == '510' for a in result['item']['affixes'])


@pytest.mark.parametrize('damage', ['missing', 'short', 'invalid', 'quality', 'base', 'unidentified', 'unknown'])
def test_unverified_identity_keeps_base_name(crowbill, damage):
    import struct

    from inventory_tracking.items.decode import decode_items

    row = crowbill['snapshot']['resources']['items'][0]
    arrays = row['resource_stats']
    raw = bytearray.fromhex(arrays['item_data_hex'])
    if damage == 'missing':
        del arrays['item_data_hex']
    elif damage == 'short':
        arrays['item_data_hex'] = '00'
    elif damage == 'invalid':
        arrays['item_data_hex'] = 'not hex'
    else:
        offset, value = {'quality': (0, 7), 'base': (0x34, 69), 'unidentified': (0x18, 0), 'unknown': (0x34, 99999)}[
            damage
        ]
        struct.pack_into('<I', raw, offset, value)
        arrays['item_data_hex'] = raw.hex()
    result = decode_items(crowbill['snapshot'], crowbill['report'])[0]
    assert result['item']['name'] == 'Military Pick'
    assert 'item_identity' not in result['source']


def test_unique_identity_uses_unique_table_not_set_table(crowbill):
    import struct

    from inventory_tracking.items.decode import decode_items

    row = crowbill['snapshot']['resources']['items'][0]
    row['txt_id'] = 0  # Verified local table: The Gnasher / Hand Axe.
    row['details']['quality'] = 7
    raw = bytearray.fromhex(row['resource_stats']['item_data_hex'])
    struct.pack_into('<I', raw, 0, 7)
    struct.pack_into('<I', raw, 0x34, 0)
    row['resource_stats']['item_data_hex'] = raw.hex()
    result = decode_items(crowbill['snapshot'], crowbill['report'])[0]
    assert result['item']['name'] == 'The Gnasher'
    assert result['item']['base_name'] == 'Hand Axe'
    assert 'set_name' not in result['item']


@pytest.fixture
def spirit():
    return json.loads((Path(__file__).parents[1] / 'fixtures/spirit_monarch.json').read_text())


def test_captured_spirit_identity_and_roll_ranges(spirit):
    from inventory_tracking.items.decode import decode_items

    result = decode_items(
        spirit['snapshot'],
        spirit['report'],
        inventory_page=spirit['snapshot']['resources']['items'][0]['details']['inventory_page'],
    )[0]
    assert result['item']['name'] == 'Spirit'
    assert result['item']['runeword'] == 'Spirit'
    assert result['item']['base_name'] == 'Monarch'
    assert result['source']['item_identity']['offset'] == 0x48
    stats = {r['memory_stat']['id']: r for r in result['decoded_stats']}
    assert stats[105]['text'] == '+27% (25-35%) Faster Cast Rate'
    assert stats[9]['text'] == '+105 (89-112) to Mana'
    assert stats[147]['text'] == '+5 (3-8) Magic Absorb'
    assert stats[3]['text'] == '+22 to Vitality'
    assert stats[194]['text'] == 'Sockets: 4 — Tal Rune, Thul Rune, Ort Rune, Amn Rune (runeword recipe)'
    assert {a['property_id']: a['value'] for a in result['item']['affixes']}['520'] == 27


@pytest.mark.parametrize('failure', ['flag', 'id', 'base', 'sockets'])
def test_runeword_requires_flag_id_base_and_socket_agreement(spirit, failure):
    import struct

    from inventory_tracking.items.decode import decode_items

    row = spirit['snapshot']['resources']['items'][0]
    data = bytearray.fromhex(row['resource_stats']['item_data_hex'])
    if failure == 'flag':
        struct.pack_into('<I', data, 0x18, 0x10)
    elif failure == 'id':
        struct.pack_into('<H', data, 0x48, 65535)
    elif failure == 'base':
        row['txt_id'] = 537
    else:
        for array in row['resource_stats']['arrays']:
            for stat in array['stats']:
                if stat['id'] == 194:
                    stat['raw'] = 3
    row['resource_stats']['item_data_hex'] = data.hex()
    result = decode_items(
        spirit['snapshot'],
        spirit['report'],
        inventory_page=spirit['snapshot']['resources']['items'][0]['details']['inventory_page'],
    )[0]
    assert 'runeword' not in result['item']
    assert not any('roll_range' in stat for stat in result['decoded_stats'])


def test_captured_authority_combines_damage_components_and_shows_range():
    from inventory_tracking.items.decode import decode_items

    capture = json.loads((Path(__file__).parents[1] / 'fixtures/authority_mage_plate.json').read_text())
    page = capture['snapshot']['resources']['items'][0]['details']['inventory_page']
    result = decode_items(capture['snapshot'], capture['report'], inventory_page=page)[0]
    assert result['item']['name'] == 'Authority'
    damage = [s for s in result['decoded_stats'] if 'Enhanced' in s['text']]
    assert len(damage) == 1
    assert damage[0]['text'] == '+41% (40-60%) Enhanced Damage'
    assert [s['id'] for s in damage[0]['memory_stats']] == [17, 18]
    assert damage[0]['value'] == 41
    assert damage[0]['roll_quality'] == 'low'
    assert result['item']['socket_recipe'] == ['Hel Rune', 'Shael Rune', 'Ral Rune']
    assert sum(a['property_id'] == '510' for a in result['item']['affixes']) == 1
