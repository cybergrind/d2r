import pytest

from pricing.knowledge.assessment.maintenance import trade_arachnid
from tests.pricing.knowledge.assessment.maintenance.test_fixed_armor_trade_reviews import inputs


IDENTITY = ('unique', 'Arachnid Mesh')


def test_arachnid_native_proof_has_one_armor_roll_and_specific_variant_boundaries():
    spec = trade_arachnid.specification(*inputs(IDENTITY))
    assert spec is not None
    assert spec['bounds'] == {'16:0': (90, 120)}
    assert (True, False, 0, 'filled') in spec['variants']


@pytest.mark.parametrize(
    'mutation',
    [
        'base',
        'charges',
        'extra-property',
        'range',
        'operation',
        'mana-operation',
        'threshold',
        'ethereal',
        'inference',
        'material',
    ],
)
def test_arachnid_proof_rejects_changed_native_semantics(mutation):
    policy, definitions, specs = inputs(IDENTITY)
    d = definitions[0]
    if mutation == 'base':
        d['base_definition']['maxac'] = 63
    elif mutation == 'charges':
        d['game_definition']['max3'] = 4
    elif mutation == 'extra-property':
        d['game_definition']['prop7'] = 'ac'
    elif mutation == 'range':
        d['roll_ranges']['16']['min'] = 80
    elif mutation == 'operation':
        specs['16']['op'] = 0
    elif mutation == 'mana-operation':
        specs['77']['op'] = 0
    elif mutation == 'threshold':
        policy['trade_qualification']['bands'][0]['when']['value'] = 119
    elif mutation == 'ethereal':
        policy['trade_qualification']['valid_if']['all'][0]['value'] = True
    elif mutation == 'inference':
        policy['trade_qualification'].pop('ethereal_inference')
    else:
        policy['trade_qualification']['material_stats'] = []
    assert trade_arachnid.specification(policy, definitions, specs) is None


def review_inputs():
    import json
    from copy import deepcopy
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_arachnid_evidence import MARKET, audit_arachnid
    from tests.pricing.knowledge.assessment.item_bank.cases.arachnid_trade import CASES
    from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import data

    doc, ctx = data(IDENTITY, CASES)
    row = doc['rows'][0]
    row['scope'] = 'native_unique_caster_belt'
    evidence = audit_arachnid(
        (json.loads(s) for s in Path(MARKET).read_text().splitlines()), definition=ctx['definitions'][IDENTITY][0]
    )
    evidence['market_snapshot'] = deepcopy(ctx['policies'][IDENTITY]['trade_qualification']['market_snapshot'])
    row['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    ctx['partial_evidence'] = {IDENTITY: evidence}
    return doc, ctx


def test_source_bound_arachnid_native_reports_establish_only_the_reviewed_segment():
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, ctx = review_inputs()
    rows, accepted = review_dimensions(doc, **ctx)
    assert rows[IDENTITY]['state'] == 'reviewed', rows
    assert accepted


@pytest.mark.parametrize(
    'missing',
    [
        'ed-90',
        'ed-109',
        'ed-110',
        'ed-119',
        'ed-120',
        'invalid-None',
        'invalid-89',
        'invalid-121',
        'ethereal',
        'unknown-ethereal',
        'unidentified',
        'socketed',
        'unknown-sockets',
        'unknown-contents',
        'filled',
    ],
)
def test_missing_native_arachnid_boundaries_keep_the_review_open(missing):
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, ctx = review_inputs()
    del doc['rows'][0]['cases']['arachnid-trade/' + missing]
    rows, accepted = review_dimensions(doc, **ctx)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize(
    'mutation',
    [
        'evidence',
        'snapshot',
        'lower-sellers',
        'thin-perfect',
        'verdict',
        'color',
        'fixed',
        'duplicate',
        'complete',
        'definition',
    ],
)
def test_rebound_wrong_reports_or_changed_censuses_do_not_establish_coverage(mutation):
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, ctx = review_inputs()
    review = doc['rows'][0]
    evidence = ctx['partial_evidence'][IDENTITY]
    if mutation == 'evidence':
        ctx['partial_evidence'] = {}
    elif mutation == 'snapshot':
        evidence['market_snapshot']['sha256'] = 'stale'
    elif mutation == 'lower-sellers':
        evidence['cohorts']['lower'] = {'priced_rows': ['a', 'b', 'c'], 'priced_sellers': ['a', 'b', 'c']}
    elif mutation == 'thin-perfect':
        evidence['cohorts']['perfect']['priced_sellers'] = ['a']
    elif mutation == 'definition':
        ctx['definitions'][IDENTITY][0]['game_definition']['max3'] = 4
        review['definition_fingerprint'] = fingerprint(ctx['definitions'][IDENTITY])
    else:
        key = 'arachnid-trade/ed-120'
        case = ctx['receipts'][review['receipt']]['cases'][key]['trade_case']
        if mutation == 'verdict':
            case['checks']['qualification']['status'] = 'candidate'
        elif mutation == 'color':
            case['checks']['lines'][0]['tone'] = 'tier_low'
        elif mutation == 'fixed':
            case['item']['raw_stats'] = [r for r in case['item']['raw_stats'] if r[0] != 105]
        elif mutation == 'duplicate':
            case['item']['raw_stats'] = (*case['item']['raw_stats'], (16, 0, 120))
        else:
            case['item']['complete'] = True
        review['cases'][key] = fingerprint(case)
    if mutation != 'evidence':
        review['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    rows, accepted = review_dimensions(doc, **ctx)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted
