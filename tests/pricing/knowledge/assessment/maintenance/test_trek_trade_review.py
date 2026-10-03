import pytest

from pricing.knowledge.assessment.maintenance import trade_trek
from tests.pricing.knowledge.assessment.maintenance.test_fixed_armor_trade_reviews import inputs


IDENTITY = ('unique', 'Sandstorm Trek')


def test_ethereal_boots_have_native_attribute_defense_and_poison_axes():
    spec = trade_trek.specification(*inputs(IDENTITY))
    assert spec is not None
    assert spec['bounds'] == {'0:0': (10, 15), '3:0': (10, 15), '16:0': (140, 170), '45:0': (40, 70)}
    assert (False, True, 0, 'empty') in spec['variants']


@pytest.mark.parametrize(
    'mutation',
    [
        'repair',
        'stamina',
        'defense-min',
        'vitality-op',
        'defense-op',
        'base',
        'socket',
        'ethereal',
        'threshold',
        'material',
    ],
)
def test_trek_proof_cannot_reuse_changed_native_or_trade_semantics(mutation):
    policy, definitions, specs = inputs(IDENTITY)
    d = definitions[0]
    if mutation == 'repair':
        d['game_definition']['par7'] = 4
    elif mutation == 'stamina':
        d['fixed_per_level_effects'][0]['coefficient_raw'] = 7
    elif mutation == 'defense-min':
        d['roll_ranges']['16']['min'] = 150
    elif mutation == 'vitality-op':
        specs['3']['op'] = 0
    elif mutation == 'defense-op':
        specs['16']['op'] = 0
    elif mutation == 'base':
        d['base_definition']['maxac'] = 66
    elif mutation == 'socket':
        d['base_definition']['gemsockets'] = 1
    elif mutation == 'ethereal':
        policy['trade_qualification']['valid_if']['all'][0]['value'] = False
    elif mutation == 'threshold':
        policy['trade_qualification']['bands'][0]['when']['all'][0]['value'] = 14
    else:
        policy['trade_qualification']['material_stats'].remove('45:0')
    assert trade_trek.specification(policy, definitions, specs) is None


def review_inputs():
    import json
    from copy import deepcopy
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_equipment_evidence import MARKET, audit_trek
    from tests.pricing.knowledge.assessment.item_bank.cases.trek_trade import CASES
    from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import data

    doc, ctx = data(IDENTITY, CASES)
    row = doc['rows'][0]
    row['scope'] = 'ethereal_unique_boots'
    evidence = audit_trek(json.loads(line) for line in Path(MARKET).read_text().splitlines())
    evidence['market_snapshot'] = deepcopy(ctx['policies'][IDENTITY]['trade_qualification']['market_snapshot'])
    row['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    ctx['partial_evidence'] = {IDENTITY: evidence}
    return doc, ctx


def test_trek_native_variants_can_establish_only_the_reviewed_ethereal_segments():
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, ctx = review_inputs()
    rows, accepted = review_dimensions(doc, **ctx)
    assert rows[IDENTITY]['state'] == 'reviewed', rows
    assert accepted


@pytest.mark.parametrize(
    'missing',
    [
        '10-10-140-40',
        '15-14-170-70',
        '14-15-170-70',
        '15-15-140-40',
        'component-16-139',
        'component-45-None',
        'nonethereal',
        'unidentified',
        'unknown-sockets',
    ],
)
def test_missing_trek_threshold_or_native_variant_boundary_keeps_review_open(missing):
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, ctx = review_inputs()
    del doc['rows'][0]['cases']['trek-trade/' + missing]
    rows, accepted = review_dimensions(doc, **ctx)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize(
    'mutation',
    [
        'evidence',
        'snapshot',
        'new-noneth',
        'thin-eth',
        'wrong-verdict',
        'wrong-color',
        'missing-repair',
        'missing-stamina',
        'duplicate',
    ],
)
def test_trek_review_rejects_changed_evidence_and_rebound_report_claims(mutation):
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, ctx = review_inputs()
    review = doc['rows'][0]
    evidence = ctx['partial_evidence'][IDENTITY]
    if mutation == 'evidence':
        ctx['partial_evidence'] = {}
    elif mutation == 'snapshot':
        evidence['market_snapshot']['sha256'] = 'stale'
    elif mutation == 'new-noneth':
        evidence['cohorts']['nonethereal'] = {'priced_rows': ['a', 'b', 'c'], 'priced_sellers': ['a', 'b', 'c']}
    elif mutation == 'thin-eth':
        evidence['cohorts']['ethereal_ordinary']['priced_sellers'] = ['a']
    else:
        key = 'trek-trade/15-14-170-70'
        case = ctx['receipts'][review['receipt']]['cases'][key]['trade_case']
        if mutation == 'wrong-verdict':
            case['checks']['qualification']['status'] = 'premium'
        elif mutation == 'wrong-color':
            case['checks']['lines'][0]['tone'] = 'tier_high'
        elif mutation.startswith('missing-'):
            stat = 252 if mutation == 'missing-repair' else 242
            case['item']['raw_stats'] = [r for r in case['item']['raw_stats'] if r[0] != stat]
        else:
            case['item']['raw_stats'] = (*case['item']['raw_stats'], (0, 0, 15))
        review['cases'][key] = fingerprint(case)
    if mutation != 'evidence':
        review['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    rows, accepted = review_dimensions(doc, **ctx)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted
