from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.market_projection import market_properties
from pricing.knowledge.assessment.handlers.definitions import named_definitions
from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.test_family_contracts import facts, scalar_properties


def ormus(skill=None, bonus=3):
    definition = named_definitions()['unique', "Ormus' Robes"]
    stats = {f'{s["stat_id"]}:0': {'status': 'decoded', 'value': s['min']} for s in definition['roll_ranges'].values()}
    properties = scalar_properties(stats)
    if skill is not None:
        key = f'107:{skill}'
        stats[key] = {'status': 'decoded', 'value': bonus}
        properties[market_properties().get(key, 'unmapped')] = bonus
    return replace(facts('Dusk Shroud', 'unique', "Ormus' Robes"), stats=stats, properties=properties)


def test_ormus_without_selected_skill_cannot_make_comparison_contract():
    contract, gaps = NamedHandler().contract(ormus(), 'armor')
    assert contract is None
    assert any('random skill' in gap.lower() for gap in gaps)


@pytest.mark.parametrize('skill', [36, 47, 59, 60])
def test_ormus_native_skill_bounds_are_ids_not_bonus_range(skill):
    candidate = ormus(skill)
    assert NamedHandler().contract(candidate, 'armor')[0] is not None
    for other in (
        ormus(skill, 2),
        ormus(skill, 4),
        replace(candidate, properties={}),
        replace(candidate, capture_complete=False),
    ):
        assert NamedHandler().contract(other, 'armor')[0] is None


def test_ormus_rejects_outside_skill_ids_and_multiple_random_choices():
    assert NamedHandler().contract(ormus(61), 'armor')[0] is None
    candidate = ormus(47)
    candidate = replace(candidate, stats=dict(candidate.stats) | {'107:59': {'status': 'decoded', 'value': 3}})
    assert NamedHandler().contract(candidate, 'armor')[0] is None
