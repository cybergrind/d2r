import json
import struct
from pathlib import Path

import pytest

from inventory_tracking.items.decode import decode_items
from pricing.knowledge.assessment.engine import assess_result


ROOT = Path(__file__).resolve().parents[4]


def superior(index, attack=2):
    saved = json.loads((ROOT / 'tests/inventory_tracking/fixtures/superior_phase_blade.json').read_text())
    row = saved['snapshot']['resources']['items'][0]
    arrays = row['resource_stats']
    arrays.pop('damage_modifiers')
    arrays.pop('stat_diagnostics')
    raw = bytearray.fromhex(arrays['item_data_hex'])
    struct.pack_into('<I', raw, 0x34, index)
    arrays['item_data_hex'] = raw.hex()
    from pricing.knowledge.market_base_catalog import equipment_base

    base_damage = equipment_base('Phase Blade')[0]['details']['one_hand_damage']
    for array in arrays['arrays']:
        for stat in array['stats']:
            if index == 0 and stat['id'] in (21, 22):
                stat['raw'] = base_damage[stat['id'] - 21]
            if stat['id'] == 19:
                stat['raw'] = attack
    return decode_items(
        saved['snapshot'],
        saved['report'],
        inventory_page=row['details']['inventory_page'],
        inventory_owner_id=row['details']['owner_id'],
    )[0]


def test_ar_only_superior_quality_row_proves_absence_of_ed_without_inventing_stats():
    extraction = superior(0)
    assert extraction['source']['superior_quality']['table_id'] == 0
    result = assess_result(extraction, profiles=[])
    assert result.contract is not None, result.price_gaps
    assert result.contract.properties['423'] == 2
    assert '17:0' not in result.facts.stats
    assert result.contract.properties['510'] == 0


@pytest.mark.parametrize(('index', 'attack'), [(3, 2), (0, 4), (999, 2)])
def test_ed_row_invalid_roll_or_unknown_quality_row_does_not_prove_zero(index, attack):
    result = assess_result(superior(index, attack), profiles=[])
    assert result.contract is None
    assert 'Weapon damage-modifier coverage is unproven.' in result.price_gaps


def test_zero_ed_base_price_requires_explicit_zero_in_comparable_listings():
    from datetime import date

    from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables, reject_reasons

    contract = assess_result(superior(0), profiles=[]).contract.to_dict()
    rows = [
        {
            **contract,
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'observed_at': '2026-09-25',
            'ask_ist': 1,
        }
        for i in range(3)
    ]
    assert price_from_comparables(evaluate(contract, rows), today=date(2026, 9, 25))['estimate_ist'] == 1
    missing = {k: v for k, v in rows[0]['properties'].items() if k != '510'}
    assert reject_reasons(contract, {**rows[0], 'properties': missing})
    assert reject_reasons(contract, {**rows[0], 'properties': {**missing, '510': 14}})


@pytest.mark.parametrize(('index', 'attack'), [(4, None), (5, 2)])
def test_durability_superior_patterns_keep_durability_roll_in_contract(index, attack):
    from inventory_tracking.items.metadata import decode_stats
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    raw = [{'id': 75, 'layer': 0, 'raw': 12}]
    if attack is not None:
        raw.append({'id': 19, 'layer': 0, 'raw': attack})
    decoded, affixes, unresolved = decode_stats(raw)
    item = facts('Crystal Sword', 'superior').to_dict()
    item['affixes'] = affixes
    extraction = {
        'item': item,
        'decoded_stats': decoded,
        'unresolved_stats': unresolved,
        'source': {
            'stat_capture_complete': True,
            'superior_quality': {'table_id': index, 'offset': 0x34, 'category': 'weapons'},
        },
    }
    result = assess_result(extraction, profiles=[])
    assert result.contract is not None, result.price_gaps
    assert result.contract.properties['937'] == 12
    assert result.contract.properties['510'] == 0
    decoded[0]['value'] = 16
    decoded[0]['memory_stat']['raw'] = 16
    assert assess_result(extraction, profiles=[]).contract is None


def test_superior_damage_pair_must_represent_one_roll():
    from dataclasses import replace

    from pricing.knowledge.assessment.handlers import HANDLERS
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    item = replace(
        facts('Crystal Sword', 'superior'),
        stats={
            f'{stat}:0': {'status': 'decoded', 'raw': value, 'value': value} for stat, value in ((17, 14), (18, 15))
        },
        properties={'510': 14},
        provenance={'capture': {'superior_quality': {'table_id': 1, 'offset': 0x34, 'category': 'weapons'}}},
    )
    contract, gaps = HANDLERS['base'].contract(item, 'weapon')
    assert contract is None
    assert any('same roll' in gap for gap in gaps)
    matched = replace(item, stats={**item.stats, '18:0': {'status': 'decoded', 'raw': 14, 'value': 14}})
    contract, gaps = HANDLERS['base'].contract(matched, 'weapon')
    assert contract is not None, gaps
