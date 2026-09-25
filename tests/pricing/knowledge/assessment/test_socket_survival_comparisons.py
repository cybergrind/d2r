from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import decode_stats, metadata
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.comparables import reject_reasons
from pricing.knowledge.assessment.handlers import HANDLERS
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def socketed_item(base, rarity, name, fillers, bonuses):
    definition = catalog().named.get((rarity, name), {})
    values = {(s['stat_id'], s.get('layer', 0)): s['min'] for s in definition.get('roll_ranges', {}).values()}
    values[31, 0] = 150
    if rarity == 'superior' and any(
        b['name'] == base and b['category'] == 'armor' for b in metadata()['bases'].values()
    ):
        values[16, 0] = 15
    for stat, amount in bonuses.items():
        values[stat, 0] = values.get((stat, 0), 0) + amount
    native = [
        {'id': stat, 'layer': layer, 'raw': value * (1 << metadata()['stats'][str(stat)]['shift'])}
        for (stat, layer), value in values.items()
    ]
    decoded, affixes, unresolved = decode_stats(native)
    assert not unresolved
    bases = {b['name']: b for b in metadata()['bases'].values()}
    item = replace(
        facts(base, rarity, name),
        sockets=len(fillers),
        socket_contents='filled',
        socket_items=[
            {'base_code': bases[n]['code'], 'name': n, 'unit_id': i + 1, 'position': i} for i, n in enumerate(fillers)
        ],
    ).to_dict()
    item['affixes'] = affixes
    return normalize({'item': item, 'decoded_stats': decoded, 'source': {'stat_capture_complete': True}})


@pytest.mark.parametrize(
    ('base', 'name', 'fillers', 'bonuses', 'family'),
    [
        ('Sallet', 'Rockstopper', ['Perfect Ruby'], {7: 38}, 'helm'),
        ('Sallet', 'Rockstopper', ['Ral Rune'], {39: 30}, 'helm'),
        (
            'Round Shield',
            "Moser's Blessed Circle",
            ['Perfect Diamond', 'Ort Rune'],
            {39: 19, 41: 54, 43: 19, 45: 19},
            'shield',
        ),
    ],
)
def test_named_survival_fillers_compare_total_effects_and_exact_payload(base, name, fillers, bonuses, family):
    item = socketed_item(base, 'unique', name, fillers, bonuses)
    contract, gaps = HANDLERS['named'].contract(item, family)
    assert contract is not None, gaps
    assert contract.socket_payload == tuple(fillers)
    row = {
        **contract.to_dict(),
        'properties': {**contract.properties, '934': ', '.join(fillers)},
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'one',
        'ask_ist': 1,
    }
    assert not reject_reasons(contract.to_dict(), row)
    for stat in bonuses:
        key = f'{stat}:0'
        prop = item.stats[key]['market_property']
        assert contract.properties[prop] == item.stats[key]['value']
        assert prop not in contract.intrinsic_properties
        assert reject_reasons(contract.to_dict(), {**row, 'properties': {**row['properties'], prop: 999}})
        invalid = replace(
            item,
            stats={**item.stats, key: {**item.stats[key], 'value': 0, 'raw': 0}},
            properties={**item.properties, prop: 0},
        )
        assert HANDLERS['named'].contract(invalid, family)[0] is None
    assert HANDLERS['named'].contract(replace(item, socket_items=[]), family)[0] is None


@pytest.mark.parametrize(('rarity', 'handler'), [('normal', 'base'), ('magic', 'affixed'), ('rare', 'affixed')])
def test_three_resistance_rune_helm_and_diamond_shield_can_compare(rarity, handler):
    for base, family, fillers, bonuses in [
        ('Mask', 'helm', ['Ral Rune', 'Ort Rune', 'Thul Rune'], {39: 30, 41: 30, 43: 30}),
        ('Large Shield', 'shield', ['Perfect Diamond'] * 3, {39: 57, 41: 57, 43: 57, 45: 57}),
    ]:
        if rarity == 'rare':
            fillers = fillers[:2]
            bonuses = {39: 30, 41: 30} if family == 'helm' else dict.fromkeys((39, 41, 43, 45), 38)
        item = socketed_item(base, rarity, None, fillers, bonuses)
        contract, gaps = HANDLERS[handler].contract(item, family)
        assert contract is not None, gaps
        assert contract.socket_payload == tuple(fillers)


def test_mixed_life_and_magic_find_preserves_both_bonuses():
    item = socketed_item('Cap', 'magic', None, ['Perfect Ruby', 'Ist Rune'], {7: 38, 80: 25})
    contract, gaps = HANDLERS['affixed'].contract(item, 'helm')
    assert contract is not None, gaps
    for stat in (7, 80):
        key = f'{stat}:0'
        changed = replace(item, stats={**item.stats, key: {**item.stats[key], 'raw': 1}})
        assert HANDLERS['affixed'].contract(changed, 'helm')[0] is None
    assert HANDLERS['affixed'].contract(item, 'shield')[0] is None
    assert HANDLERS['affixed'].contract(replace(item, runeword='unverified'), 'helm')[0] is None


def test_named_socket_resistance_is_checked_after_subtraction():
    # Rockstopper fire range is 20-50; Ral adds 30, so total 81 is invalid.
    item = socketed_item('Sallet', 'unique', 'Rockstopper', ['Ral Rune'], {39: 61})
    assert HANDLERS['named'].contract(item, 'helm')[0] is None
    # Shield Ort gives35, not the30 armor bonus.
    item = socketed_item('Round Shield', 'unique', "Moser's Blessed Circle", ['Ort Rune', 'Ort Rune'], {41: 60})
    assert HANDLERS['named'].contract(item, 'shield')[0] is None


def test_resistance_filler_stat_ids_match_pinned_properties():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.handlers.socket_fillers import filler_effects

    root = Path(__file__).resolve().parents[4] / 'third-parties/d2data/json'
    gems = {r['name']: r for r in json.loads((root / 'gems.json').read_text()).values()}
    properties = {r['code']: r for r in json.loads((root / 'properties.json').read_text()).values()}
    stats = {r['Stat']: r['*ID'] for r in json.loads((root / 'itemstatcost.json').read_text()).values()}
    for family, prefix in [('helm', 'helm'), ('armor', 'helm'), ('shield', 'shield'), ('weapon', 'weapon')]:
        for name, effects in filler_effects(family).items():
            gem = gems[name]
            prop = properties[gem[f'{prefix}Mod1Code']]
            ids = {stats[prop[f'stat{i}']] for i in range(1, 8) if prop.get(f'stat{i}')}
            if gem[f'{prefix}Mod1Code'] == 'indestruct':
                assert prop['func1'] == 20
                source = (root.parents[1] / 'D2MOO/source/D2Common/src/Items/ItemMods.cpp').read_text()
                function = source.split('int __fastcall ITEMMODS_PropertyFunc20(', 1)[1].split('\n}', 1)[0]
                assert 'STATLIST_AddStat(pStatList, STAT_ITEM_INDESCTRUCTIBLE, 1, 0)' in function
                ids = {stats['item_indesctructible']}
            assert set(effects) == ids
            assert set(effects.values()) == {gem[f'{prefix}Mod1Min']} == {gem[f'{prefix}Mod1Max']}


@pytest.mark.parametrize('rarity', ['normal', 'superior'])
def test_paladin_base_resistance_and_fillers_are_distinct_contributions(rarity):
    item = socketed_item(
        'Sacred Targe', rarity, None, ['Perfect Diamond'] * 4, dict.fromkeys((39, 41, 43, 45), 45 + 76)
    )
    contract, gaps = HANDLERS['base'].contract(item, 'shield')
    assert contract is not None, gaps
    for stat in (39, 41, 43, 45):
        assert contract.properties[item.stats[f'{stat}:0']['market_property']] == 121
    for innate in (1, 46):
        invalid = socketed_item(
            'Sacred Targe', rarity, None, ['Perfect Diamond'] * 4, dict.fromkeys((39, 41, 43, 45), innate + 76)
        )
        assert HANDLERS['base'].contract(invalid, 'shield')[0] is None
    unequal = socketed_item('Sacred Targe', rarity, None, ['Perfect Diamond'] * 4, {39: 120, 41: 121, 43: 121, 45: 121})
    assert HANDLERS['base'].contract(unequal, 'shield')[0] is None


def test_base_rune_resistance_requires_shared_automod_after_subtraction():
    item = socketed_item('Sacred Targe', 'normal', None, ['Ral Rune'], {39: 80, 41: 45, 43: 45, 45: 45})
    contract, gaps = HANDLERS['base'].contract(item, 'shield')
    assert contract is not None, gaps
    missing = replace(item, stats={k: v for k, v in item.stats.items() if k != '45:0'})
    assert HANDLERS['base'].contract(missing, 'shield')[0] is None
    # Ordinary shields cannot borrow the Paladin automod.
    ordinary = socketed_item(
        'Monarch', 'normal', None, ['Perfect Diamond'] * 4, dict.fromkeys((39, 41, 43, 45), 45 + 76)
    )
    assert HANDLERS['base'].contract(ordinary, 'shield')[0] is None


@pytest.mark.parametrize(
    ('base', 'name', 'fillers', 'bonuses', 'family'),
    [
        ('Sallet', 'Rockstopper', ['Um Rune'], dict.fromkeys((39, 41, 43, 45), 15), 'helm'),
        ('Sallet', 'Rockstopper', ['Shael Rune'], {99: 20}, 'helm'),
        ('Sallet', 'Rockstopper', ['Ber Rune'], {36: 8}, 'helm'),
        (
            'Round Shield',
            "Moser's Blessed Circle",
            ['Um Rune', 'Shael Rune'],
            {39: 22, 41: 22, 43: 22, 45: 22, 102: 20},
            'shield',
        ),
    ],
)
def test_defensive_runes_preserve_named_rolls_and_destination_effects(base, name, fillers, bonuses, family):
    item = socketed_item(base, 'unique', name, fillers, bonuses)
    contract, gaps = HANDLERS['named'].contract(item, family)
    assert contract is not None, gaps
    assert contract.socket_payload == tuple(fillers)
    for stat in bonuses:
        row = item.stats[f'{stat}:0']
        assert contract.properties[row['market_property']] == row['value']
        assert row['market_property'] not in contract.intrinsic_properties
    wrong = {**bonuses, next(iter(bonuses)): next(iter(bonuses.values())) + 100}
    invalid = socketed_item(base, 'unique', name, fillers, wrong)
    assert HANDLERS['named'].contract(invalid, family)[0] is None


def test_shael_shield_block_and_armor_recovery_are_not_interchangeable():
    item = socketed_item('Monarch', 'normal', None, ['Shael Rune'], {99: 20})
    assert HANDLERS['base'].contract(item, 'shield')[0] is None
    item = socketed_item('Cap', 'normal', None, ['Shael Rune'], {102: 20})
    assert HANDLERS['base'].contract(item, 'helm')[0] is None


def test_um_shield_total_allows_valid_automod_residual_but_not_ordinary_armor_bonus():
    for bonus in (22, 15):
        item = socketed_item('Sacred Targe', 'normal', None, ['Um Rune'], dict.fromkeys((39, 41, 43, 45), 45 + bonus))
        contract, gaps = HANDLERS['base'].contract(item, 'shield')
        # 60 total could be22 +38 rather than45 +15: the value is not enough to
        # prove an incorrect recipe. Only the exact total and Um are compared.
        assert contract is not None, gaps
        assert contract.properties[item.stats['39:0']['market_property']] == 45 + bonus
    wrong_ordinary = socketed_item('Monarch', 'normal', None, ['Um Rune'], dict.fromkeys((39, 41, 43, 45), 15))
    assert HANDLERS['base'].contract(wrong_ordinary, 'shield')[0] is None


def test_um_named_shield_listing_must_compare_total_resistance_and_exact_fillers():
    from pricing.knowledge.assessment.property_equivalence import ELEMENTAL_RESISTANCES

    item = socketed_item(
        'Round Shield',
        'unique',
        "Moser's Blessed Circle",
        ['Um Rune', 'Shael Rune'],
        {39: 22, 41: 22, 43: 22, 45: 22, 102: 20},
    )
    contract, gaps = HANDLERS['named'].contract(item, 'shield')
    assert contract is not None, gaps
    properties = {k: v for k, v in contract.properties.items() if k not in ELEMENTAL_RESISTANCES}
    properties.update({'441': 47, '934': 'Shael Rune, Um Rune'})
    row = {
        **contract.to_dict(),
        'properties': properties,
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'one',
        'ask_ist': 1,
    }
    assert not reject_reasons(contract.to_dict(), row)
    for changed in ({'441': 25}, {'934': 'Um Rune, Um Rune'}, {'934': None}):
        assert reject_reasons(contract.to_dict(), {**row, 'properties': {**properties, **changed}})


@pytest.mark.parametrize(
    ('base', 'quality', 'name', 'handler', 'family'),
    [
        ('Sallet', 'unique', 'Rockstopper', 'named', 'helm'),
        ('Cap', 'magic', None, 'affixed', 'helm'),
        ('Mage Plate', 'normal', None, 'base', 'armor'),
        ('Monarch', 'normal', None, 'base', 'shield'),
    ],
)
def test_single_cham_compares_cannot_be_frozen_with_verified_payload(base, quality, name, handler, family):
    item = socketed_item(base, quality, name, ['Cham Rune'], {153: 1})
    contract, gaps = HANDLERS[handler].contract(item, family)
    assert contract is not None, gaps
    assert contract.socket_payload == ('Cham Rune',)
    row = {
        **contract.to_dict(),
        'properties': {**contract.properties, '591': True, '934': 'Cham Rune'},
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'one',
        'ask_ist': 1,
    }
    assert not reject_reasons(contract.to_dict(), row)
    for changed in ({'591': False}, {'934': 'Jewel'}):
        assert reject_reasons(contract.to_dict(), {**row, 'properties': {**row['properties'], **changed}})


def test_stacked_or_unverified_cham_flag_is_not_assumed_boolean():
    item = socketed_item('Cap', 'magic', None, ['Cham Rune'], {153: 1})
    for value in (0, 2):
        changed = replace(
            item,
            stats={**item.stats, '153:0': {**item.stats['153:0'], 'raw': value, 'value': value}},
            properties={**item.properties, '591': value},
        )
        assert HANDLERS['affixed'].contract(changed, 'helm')[0] is None
    stacked = replace(
        item, sockets=2, socket_items=[*item.socket_items, {**item.socket_items[0], 'unit_id': 2, 'position': 1}]
    )
    assert HANDLERS['affixed'].contract(stacked, 'helm')[0] is None
