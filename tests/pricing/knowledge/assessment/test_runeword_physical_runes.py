from copy import deepcopy

from pricing.knowledge.assessment.engine import assess_result
from pricing.knowledge.assessment.maintenance.replay import replay


def test_saved_insight_fixed_sol_mirror_does_not_hide_missing_enhanced_damage():
    result = assess_result(replay('insight_bill')['extraction'], profiles=[])
    assert 'No verified market mapping for native stat 159:0.' not in result.price_gaps
    assert 'Runeword roll 17 was not captured.' in result.price_gaps
    assert 'Runeword roll 18 was not captured.' in result.price_gaps
    assert result.contract is None
    assert result.facts.stats['159:0']['raw'] == 9


def test_insight_with_explicit_ed_evidence_can_form_contract_but_wrong_mirror_cannot():
    extraction = deepcopy(replay('insight_bill')['extraction'])
    for stat in (17, 18):
        extraction['decoded_stats'].append(
            {'memory_stat': {'id': stat, 'layer': 0, 'raw': 230}, 'value': 230, 'status': 'decoded'}
        )
    extraction['item']['affixes'].append(
        {
            'property_id': '510',
            'value': 230,
            'memory_stats': [{'id': stat, 'layer': 0, 'raw': 230} for stat in (17, 18)],
        }
    )
    result = assess_result(extraction, profiles=[])
    assert result.contract is not None, result.price_gaps
    mirror = next(row for row in extraction['decoded_stats'] if row.get('memory_stat', {}).get('id') == 159)
    mirror['memory_stat']['raw'] = 10
    mirror['value'] = 10
    wrong = assess_result(extraction, profiles=[])
    assert wrong.contract is None
    assert 'No verified market mapping for native stat 159:0.' in wrong.price_gaps


def test_rune_mirror_does_not_explain_throwing_base_damage_or_incomplete_capture():
    from dataclasses import replace

    from pricing.knowledge.assessment.adapters.capture import normalize
    from pricing.knowledge.assessment.handlers.runeword import definitions
    from pricing.knowledge.assessment.mechanics.rune_physical import fixed_physical_rune_keys
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    item = normalize(replay('insight_bill')['extraction'])
    definition = definitions()['Insight']
    assert fixed_physical_rune_keys(item, definition, 'weapon') == {'159:0'}
    throwing = replace(facts('Throwing Knife'), stats=item.stats)
    assert not fixed_physical_rune_keys(throwing, definition, 'weapon')
    assert not fixed_physical_rune_keys(replace(item, capture_complete=False), definition, 'weapon')
    assert not fixed_physical_rune_keys(item, definition, 'armor')
