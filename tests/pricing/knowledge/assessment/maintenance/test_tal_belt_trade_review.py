import pytest

from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions
from tests.pricing.knowledge.assessment.item_bank.cases.tal_belt_trade import CASES
from tests.pricing.knowledge.assessment.maintenance.test_fixed_armor_trade_reviews import (
    inputs as armor_inputs,
    review_inputs as armor_review_inputs,
)


IDENTITY = ('set', "Tal Rasha's Fine-Spun Cloth")


def review_inputs():
    document, context = armor_review_inputs(IDENTITY, CASES)
    document['rows'][0]['scope'] = 'original_set_mf'
    return document, context


def test_every_tal_belt_roll_and_variant_can_establish_the_original_base_review():
    document, context = review_inputs()
    rows, accepted = review_dimensions(document, **context)
    assert rows[IDENTITY]['state'] == 'reviewed'
    assert accepted


@pytest.mark.parametrize(
    'missing',
    [
        *(
            f'mf-{mf}-defense-{defense}-fcr-{fcr}'
            for mf in range(10, 16)
            for defense, fcr in ((35, 0), (40, 0), (95, 0), (100, 0), (95, 10), (100, 10))
        ),
        'mf-None',
        'mf-9',
        'mf-16',
        'upgraded',
        'ethereal',
        'unknown-ethereal',
        'socketed',
        'unknown-sockets',
        'unknown-contents',
        'unidentified',
    ],
)
def test_tal_belt_review_requires_all_intrinsic_rolls_and_variant_boundaries(missing):
    document, context = review_inputs()
    del document['rows'][0]['cases']['tal-belt-trade/' + missing]
    rows, accepted = review_dimensions(document, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize(
    'corruption',
    [
        'mf-min',
        'mf-mapping',
        'mf-shift',
        'mana-shift',
        'mode',
        'boolean-mode',
        'set-defense',
        'set-cast',
        'extra-property',
        'parameter',
        'base',
        'upgrade',
        'threshold',
        'default',
        'base-guard',
        'inference',
    ],
)
def test_tal_belt_proof_rejects_changed_native_or_trade_semantics(corruption):
    from pricing.knowledge.assessment.maintenance.trade_tal_belt import specification

    policy, definitions, specs = armor_inputs(IDENTITY)
    row = definitions[0]
    game = row['game_definition']
    trade = policy['trade_qualification']
    if corruption == 'mf-min':
        game['min5'] = 9
    elif corruption == 'mf-mapping':
        row['roll_ranges']['80']['stat_id'] = 79
    elif corruption == 'mf-shift':
        specs['80']['shift'] = 8
    elif corruption == 'mana-shift':
        specs['9']['shift'] = 0
    elif corruption == 'mode':
        game['add func'] = 0
    elif corruption == 'boolean-mode':
        game['add func'] = True
    elif corruption == 'set-defense':
        game['amin1a'] = 59
    elif corruption == 'set-cast':
        game['amax2a'] = 11
    elif corruption == 'extra-property':
        game['prop6'] = 'ac%'
    elif corruption == 'parameter':
        game['par5'] = 1
    elif corruption == 'base':
        row['base_definition']['minac'] = 34
    elif corruption == 'upgrade':
        row['base_definition']['ultracode'] = row['base_code']
    elif corruption == 'threshold':
        trade['bands'][0]['when']['value'] = 14
    elif corruption == 'default':
        trade['default_status'] = 'use_only'
    elif corruption == 'base-guard':
        trade['valid_if']['all'].pop(3)
    else:
        trade['base_inference'] = 'anything'
    assert specification(policy, definitions, specs) is None


@pytest.mark.parametrize(
    'corruption', ['lower-roll-sale', 'wrong-color', 'missing-fixed-stat', 'duplicate-mf', 'foreign-base']
)
def test_tal_belt_receipt_cannot_certify_rebound_wrong_evidence(corruption):
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint

    document, context = review_inputs()
    key = 'tal-belt-trade/mf-14-defense-35-fcr-0'
    if corruption == 'wrong-color':
        key = 'tal-belt-trade/mf-15-defense-35-fcr-0'
    if corruption == 'foreign-base':
        key = 'tal-belt-trade/upgraded'
    case = next(iter(context['receipts'].values()))['cases'][key]['trade_case']
    if corruption == 'lower-roll-sale':
        case['checks']['qualification']['status'] = 'candidate'
    elif corruption == 'wrong-color':
        case['checks']['lines'][0]['tone'] = 'tier_high'
    elif corruption == 'missing-fixed-stat':
        case['item']['raw_stats'] = [s for s in case['item']['raw_stats'] if s[0] != 9]
    elif corruption == 'duplicate-mf':
        case['item']['raw_stats'] = (*case['item']['raw_stats'], (80, 0, 15))
    else:
        case['item']['base'] = 'Troll Belt'
    document['rows'][0]['cases'][key] = fingerprint(case)
    rows, accepted = review_dimensions(document, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


def test_tal_belt_partial_set_stages_cannot_swap_defense_and_cast_rate():
    from pricing.knowledge.assessment.maintenance.trade_tal_belt import specification

    policy, definitions, specs = armor_inputs(IDENTITY)
    game = definitions[0]['game_definition']
    for field in ('aprop', 'amin', 'amax'):
        game[field + '1a'], game[field + '2a'] = game[field + '2a'], game[field + '1a']
    assert specification(policy, definitions, specs) is None
