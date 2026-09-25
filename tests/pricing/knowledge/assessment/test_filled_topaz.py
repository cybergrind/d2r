from dataclasses import replace

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.comparables import reject_reasons
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.maintenance.replay import replay


def topaz_shako():
    item = normalize(replay('harlequin_crest')['extraction'])
    gem = next(b for b in metadata()['bases'].values() if b['name'] == 'Perfect Topaz')
    return replace(
        item,
        sockets=1,
        socket_contents='filled',
        filled_sockets=1,
        empty_sockets=0,
        socket_items=[{'base_code': gem['code'], 'name': gem['name'], 'unit_id': 1, 'position': 0}],
        stats={**item.stats, '80:0': {**item.stats['80:0'], 'value': 74, 'raw': 74}},
        properties={**item.properties, item.stats['80:0']['market_property']: 74},
    )


def test_single_topaz_named_comparison_requires_explicit_same_filler():
    item = topaz_shako()
    contract, gaps = NamedHandler().contract(item, 'helm')
    assert contract is not None, gaps
    assert contract.socket_payload == ('Perfect Topaz',)
    row = {
        **contract.to_dict(),
        'properties': {**contract.properties, '934': 'Perfect Topaz'},
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'one',
        'ask_ist': 1,
    }
    assert not reject_reasons(contract.to_dict(), row)
    for contents in (None, 'Jewel', 'Flawed Topaz', 'Perfect Topaz, Perfect Topaz'):
        assert reject_reasons(contract.to_dict(), {**row, 'properties': {**row['properties'], '934': contents}})
    assert NamedHandler().contract(replace(item, socket_items=[]), 'helm')[0] is None


def test_topaz_comparison_rejects_wrong_total_or_inconsistent_occupancy():
    item = topaz_shako()
    for changed in (
        replace(item, stats={**item.stats, '80:0': {**item.stats['80:0'], 'value': 75}}),
        replace(item, empty_sockets=1),
        replace(item, socket_items=[{**item.socket_items[0], 'base_code': 'unverified'}]),
    ):
        assert NamedHandler().contract(changed, 'helm')[0] is None


def multi_topaz_item(base, name, quality, count):
    from inventory_tracking.items.metadata import decode_stats
    from pricing.knowledge.definition_store import catalog
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    definition = catalog().named[quality, name]
    native = [
        {'id': s['stat_id'], 'layer': s.get('layer', 0), 'raw': count if s['stat_id'] == 194 else s['min']}
        for s in definition['roll_ranges'].values()
    ]
    native.append({'id': 80, 'layer': 0, 'raw': 24 * count})
    decoded, affixes, unresolved = decode_stats(native)
    assert not unresolved
    gem = next(b for b in metadata()['bases'].values() if b['name'] == 'Perfect Topaz')
    item = replace(
        facts(base, quality, name),
        sockets=count,
        socket_contents='filled',
        socket_items=[
            {'name': gem['name'], 'base_code': gem['code'], 'unit_id': i + 1, 'position': i} for i in range(count)
        ],
    ).to_dict()
    item['affixes'] = affixes
    return normalize({'item': item, 'decoded_stats': decoded, 'source': {'stat_capture_complete': True}})


def test_multiple_topazes_preserve_payload_multiplicity_and_total_magic_find():
    for base, name, quality, count, family in [
        ('Corona', 'Crown of Ages', 'unique', 2, 'helm'),
        ('Ornate Armor', "Griswold's Heart", 'set', 3, 'armor'),
    ]:
        item = multi_topaz_item(base, name, quality, count)
        contract, gaps = NamedHandler().contract(item, family)
        assert contract is not None, gaps
        assert contract.socket_payload == ('Perfect Topaz',) * count
        prop = item.stats['80:0']['market_property']
        assert contract.properties[prop] == 24 * count
        row = {
            **contract.to_dict(),
            'properties': {**contract.properties, '934': ', '.join(contract.socket_payload)},
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': 'one',
            'ask_ist': 1,
        }
        assert not reject_reasons(contract.to_dict(), row)
        assert reject_reasons(contract.to_dict(), {**row, 'properties': {**row['properties'], '934': 'Perfect Topaz'}})
        duplicate = replace(item, socket_items=[{**c, 'unit_id': 1} for c in item.socket_items])
        assert NamedHandler().contract(duplicate, family)[0] is None


def test_mixed_ist_topaz_armor_payload_matches_as_multiset_with_armor_bonus():
    item = multi_topaz_item('Corona', 'Crown of Ages', 'unique', 2)
    ist = next(b for b in metadata()['bases'].values() if b['name'] == 'Ist Rune')
    children = [dict(c) for c in item.socket_items]
    children[0].update(base_code=ist['code'], name=ist['name'])
    prop = item.stats['80:0']['market_property']
    item = replace(
        item,
        socket_items=children,
        stats={**item.stats, '80:0': {**item.stats['80:0'], 'raw': 49, 'value': 49}},
        properties={**item.properties, prop: 49},
    )
    contract, gaps = NamedHandler().contract(item, 'helm')
    assert contract is not None, gaps
    assert sorted(contract.socket_payload) == ['Ist Rune', 'Perfect Topaz']
    row = {
        **contract.to_dict(),
        'properties': {**contract.properties, '934': 'Perfect Topaz, Ist Rune'},
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'one',
        'ask_ist': 1,
    }
    assert not reject_reasons(contract.to_dict(), row)
    for payload in ['Ist Rune, Ist Rune', 'Perfect Topaz', 'Perfect Topaz, Jewel']:
        assert reject_reasons(contract.to_dict(), {**row, 'properties': {**row['properties'], '934': payload}})
    wrong_weapon_bonus = replace(
        item,
        stats={**item.stats, '80:0': {**item.stats['80:0'], 'raw': 54, 'value': 54}},
        properties={**item.properties, prop: 54},
    )
    assert NamedHandler().contract(wrong_weapon_bonus, 'helm')[0] is None


def test_magic_find_filler_amounts_match_pinned_armor_effects():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.handlers.socket_fillers import filler_effects

    rows = json.loads((Path(__file__).resolve().parents[4] / 'third-parties/d2data/json/gems.json').read_text())
    by_name = {r['name']: r for r in rows.values()}
    for name in ('Perfect Topaz', 'Ist Rune'):
        value = filler_effects('armor')[name][80]
        assert by_name[name]['helmMod1Code'] == 'mag%'
        assert by_name[name]['helmMod1Min'] == by_name[name]['helmMod1Max'] == value


def test_verified_partial_socket_fill_is_distinct_from_full_and_unknown():
    item = multi_topaz_item('Corona', 'Crown of Ages', 'unique', 2)
    prop = item.stats['80:0']['market_property']
    partial = replace(
        item,
        socket_items=item.socket_items[:1],
        filled_sockets=1,
        empty_sockets=1,
        stats={**item.stats, '80:0': {**item.stats['80:0'], 'raw': 24, 'value': 24}},
        properties={**item.properties, prop: 24},
    )
    contract, gaps = NamedHandler().contract(partial, 'helm')
    assert contract is not None, gaps
    assert contract.sockets == 2
    assert contract.socket_payload == ('Perfect Topaz',)
    row = {
        **contract.to_dict(),
        'properties': {**contract.properties, '934': 'Perfect Topaz'},
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'one',
        'ask_ist': 1,
    }
    assert not reject_reasons(contract.to_dict(), row)
    assert reject_reasons(
        contract.to_dict(), {**row, 'properties': {**row['properties'], '934': 'Perfect Topaz, Perfect Topaz'}}
    )
    assert reject_reasons(contract.to_dict(), {**row, 'sockets': 1})
    unknown = replace(partial, filled_sockets=None, empty_sockets=None)
    assert NamedHandler().contract(unknown, 'helm')[0] is None
