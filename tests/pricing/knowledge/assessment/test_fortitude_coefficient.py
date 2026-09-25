from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import decode_stats
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.comparables import reject_reasons
from pricing.knowledge.assessment.domain.contracts import ComparableContract
from pricing.knowledge.assessment.handlers.runeword import RunewordHandler, definitions
from pricing.knowledge.assessment.mechanics.per_level import variable_per_level_properties
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def fortitude(raw=2560, level=91):
    stats = [
        {'id': 216, 'layer': 0, 'raw': raw},
        {'id': 201, 'layer': 60 * 64 + 15, 'raw': 20},
        {'id': 31, 'layer': 0, 'raw': 1500},
        *[{'id': stat, 'layer': 0, 'raw': 30} for stat in (39, 41, 43, 45)],
    ]
    decoded, _, unresolved = decode_stats(stats, viewer_level=level)
    assert not unresolved
    item = replace(facts('Archon Plate'), name='Fortitude', runeword='Fortitude', sockets=4, socket_contents='filled')
    return normalize({'item': item.to_dict(), 'decoded_stats': decoded, 'source': {'stat_capture_complete': True}})


@pytest.mark.parametrize('level', [62, 91, 99])
@pytest.mark.parametrize('raw', [2048, 2304, 2560, 2816, 3072])
def test_fortitude_prices_native_coefficient_independently_of_viewer_level(raw, level):
    item = fortitude(raw, level)
    properties, consumed, gaps = variable_per_level_properties(item, definitions()['Fortitude'])
    assert not gaps
    assert consumed == {'216:0'}
    assert properties == {'438': raw / 2048}
    # Exercise exact matching for this modifier independently of other Fortitude gaps.
    contract = ComparableContract(
        1,
        'runeword',
        'armor',
        'Fortitude',
        'runeword',
        False,
        4,
        'filled',
        properties,
        base_code=item.base_code,
        base_rarity=item.rarity,
    )
    serialized = contract.to_dict()
    listing = {
        **{
            key: serialized[key]
            for key in ('name', 'rarity', 'base_code', 'ethereal', 'sockets', 'socket_contents', 'base_rarity')
        },
        'properties': dict(contract.properties),
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'coefficient-test',
        'ask_ist': 1,
    }
    assert not reject_reasons(serialized, listing)
    for value in (raw * level // 2048, 1.35, 0.125, 2):
        assert reject_reasons(serialized, {**listing, 'properties': {**listing['properties'], '438': value}})
    assert reject_reasons(
        serialized, {**listing, 'properties': {k: v for k, v in listing['properties'].items() if k != '438'}}
    )


def test_fortitude_rejects_conflicting_projection_and_invalid_native_roll():
    item = fortitude()
    contract, gaps = RunewordHandler().contract(replace(item, properties={**item.properties, '438': 113}), 'armor')
    assert contract is None
    assert any('conflict' in gap for gap in gaps)
    contract, gaps = RunewordHandler().contract(fortitude(raw=2561), 'armor')
    assert contract is None
    assert any('invalid' in gap for gap in gaps)


def test_fortitude_handler_clears_coefficient_gap_without_hiding_other_unmapped_stats():
    contract, gaps = RunewordHandler().contract(fortitude(), 'armor')
    assert contract is None
    assert 'No verified market mapping for native stat 39:0.' in gaps
    assert 'No verified market mapping for native stat 201:3855.' not in gaps
    assert not any('216:0' in gap or 'per-level' in gap for gap in gaps)


def test_fortitude_verified_fixed_proc_allows_exact_roll_cohort():
    import json
    from datetime import date
    from pathlib import Path

    from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables

    item = fortitude()
    decoded, _, _ = decode_stats(
        [{'id': r['id'], 'layer': r['parameter'], 'raw': r['raw']} for r in item.stats.values()], viewer_level=91
    )
    catalog = json.loads((Path(__file__).resolve().parents[4] / 'pricing/data/appraisal-properties.json').read_text())[
        'properties'
    ]
    captured = item.to_dict()
    captured['affixes'] = [
        {
            'property_id': next(k for k, v in catalog.items() if row['label'] in v['labels']),
            'value': row['value'],
            'memory_stat': row['memory_stat'],
        }
        for row in decoded
        if row.get('label')
    ]
    item = normalize({'item': captured, 'decoded_stats': decoded, 'source': {'stat_capture_complete': True}})
    contract, gaps = RunewordHandler().contract(item, 'armor')
    assert contract is not None, gaps
    serialized = contract.to_dict()
    rows = [
        {
            **{
                key: serialized[key]
                for key in ('name', 'rarity', 'base_code', 'ethereal', 'sockets', 'socket_contents', 'base_rarity')
            },
            'properties': dict(contract.properties),
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'observed_at': '2026-09-24',
            'ask_ist': i,
        }
        for i in (1, 2, 3)
    ]
    assert price_from_comparables(evaluate(serialized, rows), today=date(2026, 9, 24))['estimate_ist'] == 2
    assert reject_reasons(serialized, {**rows[0], 'properties': {**rows[0]['properties'], '999999': 20}})
    for key in ('201:3855', '216:0'):
        changed = replace(item, stats={k: v for k, v in item.stats.items() if k != key}, projection_gaps=[])
        contract, gaps = RunewordHandler().contract(changed, 'armor')
        assert contract is None
        assert gaps
