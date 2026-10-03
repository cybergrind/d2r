from copy import deepcopy

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.maintenance import trade_fixed_armor
from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies
from pricing.knowledge.definition_store import catalog


IDENTITY = ('set', "Immortal King's Pillar")


def inputs(identity=IDENTITY):
    return (
        deepcopy(_policies(RULES.read_bytes())[identity]),
        thaw(catalog().named_variants[identity]),
        thaw(metadata()['stats']),
    )


def test_fixed_armor_proof_includes_original_defense_and_conditional_set_defense():
    spec = trade_fixed_armor.specification(*inputs())
    assert spec is not None
    assert spec['defense_cases'] == {118, 128, 278, 288}
    assert spec['upgraded_base'] == 'Myrmidon Greaves'


@pytest.mark.parametrize(
    'corruption',
    ['identity', 'base', 'variable', 'extra-property', 'set-roll', 'shift', 'premium', 'material', 'variant'],
)
def test_fixed_armor_proof_rejects_unreviewed_semantics(corruption):
    policy, definitions, specs = inputs()
    definition = definitions[0]
    if corruption == 'identity':
        definition['name'] = "Immortal King's Forge"
    elif corruption == 'base':
        definition['base_definition']['minac'] = 44
    elif corruption == 'variable':
        definition['roll_ranges']['19']['min'] = 109
    elif corruption == 'extra-property':
        definition['game_definition']['prop5'] = 'ac%'
    elif corruption == 'set-roll':
        definition['game_definition']['amin3a'] = 159
    elif corruption == 'shift':
        specs['31']['shift'] = 8
    elif corruption == 'premium':
        policy['trade_qualification']['default_status'] = 'premium'
    elif corruption == 'material':
        policy['trade_qualification']['material_stats'] = ['31:0']
    else:
        policy['trade_qualification']['valid_if']['all'][-1]['value'] = 'unknown'
    assert trade_fixed_armor.specification(policy, definitions, specs) is None


def review_inputs(identity=IDENTITY, cases=None):
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from tests.pricing.knowledge.assessment.item_bank.cases.ik_pillar_trade import CASES
    from tests.pricing.knowledge.assessment.item_bank.trade_checks import trade_case

    cases = CASES if cases is None else cases
    policy, definitions, specs = inputs(identity)
    path = 'pricing/data/report-receipts/armor.json'
    review = {
        'quality': 'set',
        'name': identity[1],
        'scope': 'fixed_set_armor',
        'policy_fingerprint': fingerprint(policy),
        'definition_fingerprint': fingerprint(definitions),
        'receipt': path,
        'review_date': '2026-10-01',
        'reason': 'Reviewed original fixed-affix armor.',
        'cases': {c.id: fingerprint(trade_case(c)) for c in cases},
    }
    receipt = {
        'schema_version': 1,
        'generation': 'selected',
        'exitstatus': 0,
        'sources_unchanged': True,
        'inputs': {'source': 'hash'},
        'finished_inputs': {'source': 'hash'},
        'cases': {
            c.id: {
                'trade_case': trade_case(c),
                'covers': list(c.covers),
                'phases': dict.fromkeys(('setup', 'call', 'teardown'), 'passed'),
            }
            for c in cases
        },
    }
    return {'schema_version': 1, 'rows': [review]}, {
        'policies': {identity: policy},
        'definitions': {identity: definitions},
        'receipts': {path: receipt},
        'generation': 'selected',
        'inputs': {'source': 'hash'},
        'stat_specs': specs,
    }


def test_fixed_armor_execution_can_establish_only_its_explicit_review():
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, context = review_inputs()
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'reviewed'
    assert accepted == {'pricing/data/report-receipts/armor.json'}


@pytest.mark.parametrize(
    'missing',
    [
        'defense-118',
        'defense-128',
        'defense-278',
        'defense-288',
        'upgraded',
        'ethereal',
        'unknown-ethereal',
        'socketed',
        'unknown-sockets',
        'unknown-contents',
        'unidentified',
    ],
)
def test_fixed_armor_review_requires_every_native_and_variant_boundary(missing):
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, context = review_inputs()
    del doc['rows'][0]['cases']['ik-pillar-trade/' + missing]
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


def test_fixed_armor_cannot_borrow_a_foreign_base_even_with_rebound_case_hash():
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, context = review_inputs()
    key = 'ik-pillar-trade/upgraded'
    receipt = next(iter(context['receipts'].values()))
    case = receipt['cases'][key]['trade_case']
    case['item']['base'] = 'Mirrored Boots'
    doc['rows'][0]['cases'][key] = fingerprint(case)
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize('corruption', ['roll-mapping', 'missing-base-guard', 'boolean-set-bonus'])
def test_fixed_armor_definition_proof_rejects_rebound_incomplete_guards(corruption):
    policy, definitions, specs = inputs()
    if corruption == 'roll-mapping':
        definitions[0]['roll_ranges']['19']['stat_id'] = 31
    elif corruption == 'missing-base-guard':
        policy['trade_qualification']['valid_if']['all'].pop()
    else:
        definitions[0]['game_definition']['amin4a'] = True
        definitions[0]['game_definition']['amax4a'] = True
    assert trade_fixed_armor.specification(policy, definitions, specs) is None


@pytest.mark.parametrize('mode', [None, 0, 1, True, 2.0])
def test_conditional_defense_proof_requires_count_based_set_activation(mode):
    policy, definitions, specs = inputs()
    if mode is None:
        definitions[0]['game_definition'].pop('add func')
    else:
        definitions[0]['game_definition']['add func'] = mode
    assert trade_fixed_armor.specification(policy, definitions, specs) is None
