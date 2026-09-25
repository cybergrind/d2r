from dataclasses import replace

from pricing.knowledge.assessment.handlers.runeword import RunewordHandler
from pricing.knowledge.definitions import socket_bonus_ranges
from tests.pricing.knowledge.assessment.test_intrinsic_properties import spirit


def test_socket_compiler_keeps_equipment_effects_separate_and_adds_duplicate_runes():
    gems = {
        'fixture': {
            'shieldMod1Code': 'res-pois',
            'shieldMod1Min': 35,
            'shieldMod1Max': 35,
            'helmMod1Code': 'res-pois',
            'helmMod1Min': 30,
            'helmMod1Max': 30,
        }
    }
    properties = {'res-pois': {'func1': 1, 'stat1': 'poisonresist'}}
    result = socket_bonus_ranges(['fixture', 'fixture'], gems, properties, {'poisonresist': 45})
    assert result['shield']['45']['min'] == 70
    assert result['armor']['45']['min'] == 60
    assert result['weapon'] == {}


def test_spirit_shield_rune_bonuses_are_intrinsic_without_ignoring_added_base_resists():
    from pricing.knowledge.assessment.handlers.runeword import definitions
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    item = spirit()
    base = facts('Monarch')
    stats = {
        **item.stats,
        '45:0': {'id': 45, 'status': 'decoded', 'value': 35, 'market_property': '401'},
        '31:0': {'id': 31, 'status': 'decoded', 'value': 140},
    }
    item = replace(
        item,
        base_code=base.base_code,
        base_name=base.base_name,
        item_type=base.item_type,
        stats=stats,
        properties={**item.properties, '401': 35},
    )
    assert definitions()['Spirit']['socket_bonus_ranges']['shield']['45']['min'] == 35
    contract, gaps = RunewordHandler().contract(item, 'shield')
    assert not gaps
    assert contract.intrinsic_properties['401'] == 35
    augmented = replace(
        item, stats={**stats, '45:0': {**stats['45:0'], 'value': 80}}, properties={**item.properties, '401': 80}
    )
    assert RunewordHandler().contract(augmented, 'shield')[0] is None  # Monarch has no automod resistance.
    paladin_base = facts('Sacred Targe')
    augmented = replace(
        augmented, base_code=paladin_base.base_code, base_name=paladin_base.base_name, item_type=paladin_base.item_type
    )
    assert '401' not in RunewordHandler().contract(augmented, 'shield')[0].intrinsic_properties


def test_saved_spirit_compares_only_variable_rolls_after_proven_base_and_recipe_bonuses():
    import json
    from datetime import date
    from pathlib import Path

    from inventory_tracking.items.decode import decode_items
    from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
    from pricing.knowledge.assessment.engine import assess

    capture = json.loads((Path(__file__).parents[3] / 'inventory_tracking/fixtures/spirit_monarch.json').read_text())
    row = capture['snapshot']['resources']['items'][0]
    extraction = decode_items(
        capture['snapshot'],
        capture['report'],
        inventory_page=row['details']['inventory_page'],
        inventory_owner_id=row['details']['owner_id'],
    )[0]
    contract = assess(extraction, profiles=[])['contract']
    assert contract['intrinsic_properties']['446'] == 22
    rows = [
        {
            **{
                k: contract[k]
                for k in ('name', 'base_code', 'rarity', 'ethereal', 'sockets', 'socket_contents', 'base_rarity')
            },
            'listing_id': str(i),
            'seller_id': str(i),
            'observed_at': '2026-09-24',
            'properties': {'520': 27, '400': 105, '818': 5, '1855': 140},
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'ask_ist': i,
        }
        for i in (1, 2, 3)
    ]
    result = evaluate(contract, rows)
    assert not result['rejected']
    assert price_from_comparables(result, today=date(2026, 9, 24))['estimate_ist'] == 2
    changed = {**rows[0], 'properties': {**rows[0]['properties'], '446': 30}}
    assert not evaluate(contract, [changed])['accepted']


def test_cold_rune_duration_requires_matching_frames_and_decoded_seconds():
    item = spirit()
    stats = dict(item.stats)
    for stat, raw, value, unit in ((54, 3, 3, None), (55, 14, 14, None), (56, 75, 3, 'seconds')):
        stats[f'{stat}:0'] = {'status': 'decoded', 'raw': raw, 'value': value, 'unit': unit}
    item = replace(
        item,
        stats=stats,
        properties={**item.properties, '482': 3, '483': 14},
        projection_gaps=('No verified market mapping for native stat 56:0.',),
    )
    contract, gaps = RunewordHandler().contract(item, 'weapon')
    assert not gaps
    assert contract.intrinsic_properties['482'] == 3
    assert contract.intrinsic_properties['483'] == 14
    for row in (
        {'status': 'decoded', 'raw': 3, 'value': 3, 'unit': 'seconds'},
        {'status': 'decoded', 'raw': 75, 'value': 75, 'unit': 'frames'},
    ):
        changed = replace(item, stats={**stats, '56:0': row})
        assert RunewordHandler().contract(changed, 'weapon')[0] is None
