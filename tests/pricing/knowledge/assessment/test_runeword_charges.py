from dataclasses import replace

import pytest

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


def test_harmony_revive_charges_decode_but_partial_item_cannot_be_priced():
    from pricing.knowledge.assessment.handlers.runeword import definitions
    from pricing.knowledge.assessment.mechanics.named_charges import fixed_charge_properties

    item = harmony()
    properties, consumed, gaps = fixed_charge_properties(item, definitions()['Harmony'])
    assert properties == {'741': 20}
    assert consumed == {'204:6100'}
    assert gaps == []
    # This legacy fixture omits elemental damage and cannot establish a full
    # Harmony price. Skill level20 remains distinct from15 remaining charges.
    contract, gaps = RunewordHandler().contract(item, 'weapon')
    assert contract is None
    assert any('elemental' in gap.lower() for gap in gaps)


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
