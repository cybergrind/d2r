import pytest

from pricing.knowledge.assessment.maintenance import trade_titan
from tests.pricing.knowledge.assessment.maintenance.test_fixed_armor_trade_reviews import inputs


IDENTITY = ('unique', "Titan's Revenge")


def test_titan_proof_preserves_both_verified_native_base_codes():
    spec = trade_titan.specification(*inputs(IDENTITY))
    assert spec is not None
    assert spec['base_codes'] == {'Ceremonial Javelin': 'ama', 'Matriarchal Javelin': 'amf'}
    assert spec['thresholds'] == {'ama': 190, 'amf': 200}


@pytest.mark.parametrize(
    'mutation',
    [
        'upgrade',
        'pair',
        'operation',
        'skill-layer',
        'replenish',
        'flat-damage',
        'threshold',
        'band-base',
        'leech-bounds',
        'material',
    ],
)
def test_titan_proof_rejects_changed_native_and_trade_semantics(mutation):
    policy, definitions, specs = inputs(IDENTITY)
    d = definitions[0]
    if mutation == 'upgrade':
        d['base_definition']['ultracode'] = d['base_code']
    elif mutation == 'pair':
        d['roll_ranges']['18']['min'] = 149
    elif mutation == 'operation':
        specs['17']['op'] = 0
    elif mutation == 'skill-layer':
        d['roll_ranges']['188:2']['layer'] = 3
    elif mutation == 'replenish':
        d['game_definition']['par5'] = 29
    elif mutation == 'flat-damage':
        d['game_definition']['min9'] = 24
    elif mutation == 'threshold':
        policy['trade_qualification']['bands'][1]['when']['all'][1]['value'] = 190
    elif mutation == 'band-base':
        policy['trade_qualification']['bands'][1]['when']['all'][0]['value'] = d['base_code']
    elif mutation == 'leech-bounds':
        d['roll_ranges']['60']['max'] = 10
    else:
        policy['trade_qualification']['material_stats'].remove('60:0')
    assert trade_titan.specification(policy, definitions, specs) is None


def review_inputs():
    import json
    from copy import deepcopy
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_titan_evidence import MARKET, audit_titan
    from tests.pricing.knowledge.assessment.item_bank.cases.titan_trade import CASES
    from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import data

    doc, ctx = data(IDENTITY, CASES)
    review = doc['rows'][0]
    review['scope'] = 'ethereal_unique_javelin'
    evidence = audit_titan(json.loads(line) for line in Path(MARKET).read_text().splitlines())
    evidence['market_snapshot'] = deepcopy(ctx['policies'][IDENTITY]['trade_qualification']['market_snapshot'])
    review['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    ctx['partial_evidence'] = {IDENTITY: evidence}
    return doc, ctx


def test_native_and_upgraded_titan_reports_establish_only_source_bound_dispositions():
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, ctx = review_inputs()
    rows, accepted = review_dimensions(doc, **ctx)
    assert rows[IDENTITY]['state'] == 'reviewed', rows
    assert accepted


@pytest.mark.parametrize(
    'missing',
    [
        'Ceremonial Javelin/ed-189-leech-9',
        'Ceremonial Javelin/ed-190-leech-5',
        'Matriarchal Javelin/ed-199-leech-9',
        'Matriarchal Javelin/ed-200-leech-5',
        'Matriarchal Javelin/unidentified',
        'Ceremonial Javelin/unknown-ethereal',
        'Matriarchal Javelin/component-60-None',
        'Ceremonial Javelin/reverse-mismatched-ed',
        'Matriarchal Javelin/shared-invalid-201',
    ],
)
def test_missing_titan_boundary_cannot_be_hidden_by_other_base_coverage(missing):
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, ctx = review_inputs()
    del doc['rows'][0]['cases']['titan-trade/' + missing]
    rows, accepted = review_dimensions(doc, **ctx)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize(
    'mutation',
    [
        'evidence',
        'snapshot',
        'lower-sellers',
        'noneth-sellers',
        'thin-upgrade',
        'wrong-verdict',
        'wrong-color',
        'fixed-replenish',
        'duplicate',
        'wrong-base',
    ],
)
def test_titan_review_rejects_changed_evidence_and_rebound_wrong_reports(mutation):
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, ctx = review_inputs()
    review = doc['rows'][0]
    evidence = ctx['partial_evidence'][IDENTITY]
    if mutation == 'evidence':
        ctx['partial_evidence'] = {}
    elif mutation == 'snapshot':
        evidence['market_snapshot']['sha256'] = 'stale'
    elif mutation in ('lower-sellers', 'noneth-sellers'):
        key = 'amf/lower' if mutation == 'lower-sellers' else 'ama/nonethereal'
        evidence['cohorts'][key].update(priced_rows=['a', 'b', 'c'], priced_sellers=['a', 'b', 'c'])
    elif mutation == 'thin-upgrade':
        evidence['cohorts']['amf/premium']['priced_sellers'] = ['a']
    else:
        key = (
            'titan-trade/Matriarchal Javelin/ed-199-leech-9'
            if mutation in ('wrong-verdict', 'wrong-base')
            else 'titan-trade/Matriarchal Javelin/ed-200-leech-9'
        )
        case = ctx['receipts'][review['receipt']]['cases'][key]['trade_case']
        if mutation == 'wrong-verdict':
            case['checks']['qualification']['status'] = 'premium'
        elif mutation == 'wrong-color':
            case['checks']['lines'][0]['tone'] = 'tier_low'
        elif mutation == 'fixed-replenish':
            case['item']['raw_stats'] = [r for r in case['item']['raw_stats'] if r[0] != 253]
        elif mutation == 'wrong-base':
            case['item']['base'] = 'Ceremonial Javelin'
        else:
            case['item']['raw_stats'] = (*case['item']['raw_stats'], (17, 0, 200))
        review['cases'][key] = fingerprint(case)
    if mutation != 'evidence':
        review['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    rows, accepted = review_dimensions(doc, **ctx)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


def test_original_base_evaluation_cannot_certify_upgraded_reports(monkeypatch):
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    original = trade_titan._outcome
    monkeypatch.setattr(trade_titan, '_outcome', lambda *args, **kwargs: original(*args))
    doc, ctx = review_inputs()
    rows, accepted = review_dimensions(doc, **ctx)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted
