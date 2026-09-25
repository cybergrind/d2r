from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.domain.facts import ItemFacts
from pricing.knowledge.assessment.handlers import HANDLERS


def facts(base_name, rarity='normal', name=None):
    base = next(b for b in metadata()['bases'].values() if b['name'] == base_name)
    return ItemFacts(
        name or base_name, base_name, base['code'], base['type'], rarity, None, True, False, 0, 'empty', [], True
    )


def scalar_properties(stats):
    """Build fixture facets for ordinary layer-zero modifiers as the decoder does."""
    return {
        prop: row['value']
        for key, row in stats.items()
        if key not in {'31:0', '194:0'}
        and key.endswith(':0')
        and (prop := metadata()['stats'][key.split(':')[0]].get('property_id'))
    }


@pytest.mark.parametrize(('base', 'family'), [('Mage Plate', 'armor'), ('Monarch', 'shield'), ('Diadem', 'helm')])
def test_armor_base_comparisons_require_actual_defense(base, family):
    item = facts(base)
    contract, gaps = HANDLERS['base'].contract(item, family)
    assert contract is None
    assert any('defense' in gap.lower() for gap in gaps)
    item = replace(item, stats={'31:0': {'id': 31, 'value': 100, 'status': 'decoded'}})
    contract, gaps = HANDLERS['base'].contract(item, family)
    assert not gaps
    assert contract.properties['1855'] == 100


@pytest.mark.parametrize(('base', 'family'), [('Small Charm', 'charm'), ('Jewel', 'jewel'), ('Ring', 'jewelry')])
def test_complete_affixed_nonarmor_family_can_make_exact_contract(base, family):
    item = replace(facts(base, 'magic'), properties={'427': 10})
    contract, gaps = HANDLERS['affixed'].contract(item, family)
    assert not gaps
    assert contract.name == base


def test_named_set_contract_preserves_identity_rolls_and_defense():
    item = replace(
        facts('Basinet', 'set', "Sazabi's Mental Sheath"),
        stats={
            str(k) + ':0': {'id': k, 'value': v, 'status': 'decoded'}
            for k, v in [(31, 177), (127, 1), (39, 19), (41, 20)]
        },
        properties={'427': 19, '428': 20, '587': 1},
    )
    contract, gaps = HANDLERS['named'].contract(item, 'helm')
    assert not gaps
    assert contract.name == "Sazabi's Mental Sheath"
    assert contract.rarity == 'set'
    assert contract.base_code == item.base_code
    assert contract.properties['1855'] == 177
    missing = replace(item, stats={k: v for k, v in item.stats.items() if k != '41:0'})
    assert HANDLERS['named'].contract(missing, 'helm')[0] is None
    assert HANDLERS['named'].contract(replace(item, ethereal=True), 'helm')[0] is None
    assert HANDLERS['named'].contract(replace(item, name='Unverified name'), 'helm')[0] is None


def test_named_unique_does_not_mix_original_and_unverified_upgraded_base():
    item = replace(
        facts('Templar Coat', 'unique', 'Guardian Angel'),
        stats={
            str(k) + ':0': {'id': k, 'value': v, 'status': 'decoded'}
            for k, v in [(31, 789), (89, 4), (16, 187), (102, 30), (40, 15), (42, 15), (44, 15), (46, 15), (20, 20)]
        },
        properties={'425': 187},
    )
    item = replace(
        item,
        stats={
            **item.stats,
            '245:0': {
                'status': 'decoded',
                'raw': 5,
                'value': 227,
                'viewer_level': 91,
                'per_level': {'numerator': 5, 'denominator': 2},
            },
        },
    )
    contract, gaps = HANDLERS['named'].contract(item, 'armor')
    assert not gaps
    assert contract.name == 'Guardian Angel'
    wrong = facts('Mage Plate', 'unique', 'Guardian Angel')
    assert HANDLERS['named'].contract(replace(item, base_code=wrong.base_code), 'armor')[0] is None


def test_set_price_reaches_report_and_excludes_wrong_defense_and_base(tmp_path):
    import json
    from datetime import UTC, datetime

    from inventory_tracking.appraisal.text import format_appraisal
    from pricing.knowledge.index import build_index
    from pricing.knowledge.pipeline import retrieve_draft

    item = facts('Basinet', 'set', "Sazabi's Mental Sheath")
    stats = [(31, 177, None), (127, 1, '587'), (39, 19, '427'), (41, 20, '428')]
    decoded, affixes = [], []
    for stat, value, market in stats:
        raw = {'id': stat, 'layer': 0, 'raw': value}
        decoded.append({'status': 'decoded', 'value': value, 'memory_stat': raw, 'text': str(stat)})
        if market:
            affixes.append({'property_id': market, 'value': value, 'memory_stat': raw})
    extraction = {
        'item': {**item.to_dict(), 'affixes': affixes},
        'decoded_stats': decoded,
        'source': {'stat_capture_complete': True},
    }
    properties = {'1855': 177, '587': 1, '427': 19, '428': 20}
    rows = [
        {
            'kind': 'market',
            'name': item.name,
            'rarity': 'set',
            'base_code': item.base_code,
            'ethereal': False,
            'sockets': 0,
            'socket_contents': 'empty',
            'properties': properties,
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'seller_id': str(i),
            'listing_id': str(i),
            'ask_ist': i,
            'unit_policy': 'single_item',
            'observed_at': datetime.now(UTC).date().isoformat(),
        }
        for i in (1, 2, 3)
    ]
    rows.extend(
        [
            {**rows[0], 'seller_id': 'defense', 'listing_id': 'defense', 'properties': {**properties, '1855': 180}},
            {**rows[0], 'seller_id': 'base', 'listing_id': 'base', 'base_code': facts('Diadem').base_code},
        ]
    )
    path = tmp_path / 'rows.json'
    path.write_text(json.dumps({'schema_version': 1, 'rows': rows}))
    db = tmp_path / 'market.sqlite3'
    build_index([path], db)
    result = retrieve_draft(extraction, db)
    assert result['price_estimate']['estimate_ist'] == 2
    assert len(result['assessment']['comparisons']['rejected']) == 2
    report = format_appraisal({'state': 'complete', 'request_id': 1, 'result': result})
    assert 'Price: ~2 Ist' in report
    assert 'not implemented' not in report


def test_named_skill_tree_roll_requires_exact_native_parameter():
    from pricing.knowledge.assessment.handlers.definitions import named_definitions

    definition = named_definitions()['set', "Aldur's Deception"]
    item = facts(definition['base_name'], 'set', definition['name'])
    stats = {
        f'{spec["stat_id"]}:{spec.get("layer", 0)}': {'id': spec['stat_id'], 'value': spec['min'], 'status': 'decoded'}
        for spec in definition['roll_ranges'].values()
    }
    stats['31:0'] = {'id': 31, 'value': 800, 'status': 'decoded'}
    properties = scalar_properties(stats)
    item = replace(item, stats=stats, properties=properties)
    assert HANDLERS['named'].contract(item, 'armor')[0] is not None
    wrong = dict(stats)
    wrong['188:0'] = wrong.pop('188:41')
    contract, gaps = HANDLERS['named'].contract(replace(item, stats=wrong), 'armor')
    assert contract is None
    assert any('188:41' in gap for gap in gaps)
