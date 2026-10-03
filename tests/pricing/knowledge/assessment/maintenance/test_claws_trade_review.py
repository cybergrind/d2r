from copy import deepcopy

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.maintenance import trade_fixed_armor
from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies
from pricing.knowledge.definition_store import catalog


IDENTITY = ('set', "Trang-Oul's Claws")


def inputs():
    return (
        deepcopy(_policies(RULES.read_bytes())[IDENTITY]),
        thaw(catalog().named_variants[IDENTITY]),
        thaw(metadata()['stats']),
    )


def test_claws_fixed_armor_proof_has_original_defense_and_native_skill_layer():
    spec = trade_fixed_armor.specification(*inputs())
    assert spec is not None
    assert spec['defense_cases'] == {67, 74}
    assert spec['upgraded_base'] == 'Vambraces'
    assert spec['fixed_native_stats'] == {(105, 0): 20, (43, 0): 30, (188, 16): 2, (332, 0): 25}


@pytest.mark.parametrize(
    'corruption',
    [
        'parameter',
        'layer',
        'poison',
        'conditional',
        'boolean-mode',
        'shift',
        'parameter-bits',
        'variable',
        'base',
        'premium',
        'inference',
        'base-guard',
    ],
)
def test_claws_proof_rejects_incompatible_native_or_trade_semantics(corruption):
    policy, definitions, specs = inputs()
    row = definitions[0]
    if corruption == 'parameter':
        row['game_definition']['par4'] = 7
    elif corruption == 'layer':
        row['roll_ranges']['188:16']['layer'] = 17
    elif corruption == 'poison':
        del row['roll_ranges']['332']
    elif corruption == 'conditional':
        row['game_definition']['add func'] = 2
    elif corruption == 'boolean-mode':
        row['game_definition']['add func'] = False
    elif corruption == 'shift':
        specs['332']['shift'] = 8
    elif corruption == 'parameter-bits':
        specs['188']['parameter_bits'] = 0
    elif corruption == 'variable':
        row['game_definition']['amin3a'] = 24
    elif corruption == 'base':
        row['base_definition']['maxac'] = 45
    elif corruption == 'premium':
        policy['trade_qualification']['default_status'] = 'premium'
    elif corruption == 'inference':
        policy['trade_qualification']['base_inference'] = 'anything'
    else:
        policy['trade_qualification']['valid_if']['all'].pop()
    assert trade_fixed_armor.specification(policy, definitions, specs) is None


def review_inputs():
    from tests.pricing.knowledge.assessment.item_bank.cases.claws_trade import CASES
    from tests.pricing.knowledge.assessment.maintenance.test_fixed_armor_trade_reviews import (
        review_inputs as armor_inputs,
    )

    return armor_inputs(IDENTITY, CASES)


def test_claws_executed_boundary_cases_establish_original_trade_review():
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, context = review_inputs()
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'reviewed'
    assert accepted


@pytest.mark.parametrize(
    'missing',
    [
        'defense-67',
        'defense-74',
        'upgraded',
        'ethereal',
        'unknown-ethereal',
        'socketed',
        'unknown-sockets',
        'unknown-contents',
        'unidentified',
    ],
)
def test_claws_review_requires_native_and_variant_boundaries(missing):
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, context = review_inputs()
    del doc['rows'][0]['cases']['claws-trade/' + missing]
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


def test_claws_review_cannot_use_native_cases_without_its_poison_bonus():
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, context = review_inputs()
    case = next(iter(context['receipts'].values()))['cases']['claws-trade/defense-67']['trade_case']
    case['item']['raw_stats'] = [r for r in case['item']['raw_stats'] if r[0] != 332]
    doc['rows'][0]['cases']['claws-trade/defense-67'] = fingerprint(case)
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


def test_claws_skill_parameter_must_belong_to_the_skill_property_slot():
    policy, definitions, specs = inputs()
    game = definitions[0]['game_definition']
    for field in ('prop', 'min', 'max'):
        game[field + '3'], game[field + '4'] = game[field + '4'], game[field + '3']
    assert trade_fixed_armor.specification(policy, definitions, specs) is None
