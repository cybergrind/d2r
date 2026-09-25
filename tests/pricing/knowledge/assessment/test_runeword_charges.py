from dataclasses import replace
from datetime import date

import pytest

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables, reject_reasons
from pricing.knowledge.assessment.handlers.runeword import RunewordHandler
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def harmony():
    key = '204:6100'
    stats = {f'{stat}:0': {'status': 'decoded', 'value': 240, 'raw': 240} for stat in (17, 18)}
    stats['97:32'] = {'status': 'decoded', 'value': 4, 'raw': 4}
    stats[key] = {
        'status': 'decoded',
        'value': 15,
        'raw': 25 * 256 + 15,
        'unit': 'charges_remaining',
        'charges': {'remaining': 15, 'maximum': 25},
    }
    return replace(
        facts('Long Bow'),
        runeword='Harmony',
        sockets=4,
        socket_contents='filled',
        stats=stats,
        properties={'510': 240},
        projection_gaps=[f'No verified market mapping for native stat {key}.'],
    )


def test_harmony_fixed_revive_charges_are_comparable_by_skill_level():
    item = harmony()
    contract, gaps = RunewordHandler().contract(item, 'weapon')
    assert contract is not None, gaps
    assert contract.properties['741'] == 20
    assert contract.intrinsic_properties['741'] == 20
    payload = contract.to_dict()
    rows = [
        {
            **payload,
            'properties': {'510': 240},
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'ask_ist': 1,
            'observed_at': '2026-09-25',
        }
        for i in range(3)
    ]
    assert price_from_comparables(evaluate(payload, rows), today=date(2026, 9, 25))['estimate_ist'] == 1
    assert reject_reasons(payload, {**rows[0], 'properties': {'510': 240, '741': 15}})


@pytest.mark.parametrize('change', ['missing', 'capacity', 'level', 'projection'])
def test_harmony_unproven_charge_record_blocks_comparison(change):
    item = harmony()
    stats = {k: dict(v) for k, v in item.stats.items()}
    if change == 'missing':
        del stats['204:6100']
    elif change == 'capacity':
        stats['204:6100']['charges'] = {'remaining': 15, 'maximum': 24}
    elif change == 'level':
        stats['204:6099'] = stats.pop('204:6100')
    else:
        stats['204:6100']['market_property'] = 'wrong'
    contract, gaps = RunewordHandler().contract(replace(item, stats=stats, projection_gaps=[]), 'weapon')
    assert contract is None
    assert any('charge' in g.lower() for g in gaps)


def test_compiled_runeword_charge_coverage_matches_pinned_source():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.handlers.runeword import definitions

    root = Path(__file__).resolve().parents[4]
    source = json.loads((root / 'pricing/raw/d2data/runes.json').read_text())
    definitions_by_name = definitions()
    reviewed = 0
    for name, record in source.items():
        if record.get('complete') != 1:
            continue
        count = sum(record.get(f'T1Code{i}') == 'charged' for i in range(1, 8))
        assert len(definitions_by_name[name]['charged_skills']) == count, name
        reviewed += bool(count)
    assert reviewed == 21
    assert definitions_by_name['Harmony']['charged_skills'] == (
        {'skill_id': 95, 'level': 20, 'capacity_parameter': 25},
    )


def test_old_runeword_definition_cannot_silently_skip_charge_validation():
    from pricing.knowledge.assessment.mechanics.named_charges import fixed_charge_properties

    _, consumed, gaps = fixed_charge_properties(harmony(), {'rarity': 'runeword'})
    assert not consumed
    assert gaps == ['Runeword charged-skill definitions need an offline rebuild.']
