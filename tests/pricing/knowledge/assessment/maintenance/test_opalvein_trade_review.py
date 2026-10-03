from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance import trade_opalvein
from tests.pricing.knowledge.assessment.maintenance.test_fixed_armor_trade_reviews import inputs


IDENTITY = ('unique', 'Opalvein')


def test_native_choice_spec_preserves_all_six_alternatives():
    spec = trade_opalvein.specification(*inputs(IDENTITY))
    assert spec is not None
    assert len(spec['choices']) == 6
    assert spec['supported'] == {'329:0', '331:0'}


@pytest.mark.parametrize(
    'mutation', ['mode', 'count', 'range', 'pair', 'shift', 'proc', 'extra', 'premium', 'choice', 'market-mapping']
)
def test_changed_native_or_trade_semantics_cannot_reuse_choice_proof(mutation):
    policy, definitions, specs = inputs(IDENTITY)
    d = definitions[0]
    if mutation == 'mode':
        d['property_groups'][0]['game_definition']['PickMode'] = 2
    elif mutation == 'count':
        d['game_definition']['max2'] = 2
    elif mutation == 'range':
        d['roll_ranges']['86']['min'] = 0
    elif mutation == 'pair':
        d['property_groups'][0]['choices'][1]['roll_ranges']['18']['max'] = 41
    elif mutation == 'shift':
        specs['329']['shift'] = 8
    elif mutation == 'proc':
        d['game_definition']['max1'] = 16
    elif mutation == 'extra':
        d['game_definition']['prop7'] = 'str'
    elif mutation == 'premium':
        policy['trade_qualification']['default_status'] = 'premium'
    elif mutation == 'market-mapping':
        specs['329']['property_id'] = '743'
    else:
        policy['trade_qualification']['choice_keys'].append('330:0')
    assert trade_opalvein.specification(policy, definitions, specs) is None


def review_inputs():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_choice_evidence import MARKET, audit_choices
    from tests.pricing.knowledge.assessment.item_bank.cases.opal_trade import CASES
    from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import data

    doc, ctx = data(IDENTITY, CASES)
    doc['rows'][0]['scope'] = 'choice_named_jewelry'
    evidence = audit_choices(json.loads(line) for line in Path(MARKET).read_text().splitlines())
    evidence['market_snapshot'] = deepcopy(ctx['policies'][IDENTITY]['trade_qualification']['market_snapshot'])
    doc['rows'][0]['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    ctx['partial_evidence'] = {IDENTITY: evidence}
    return doc, ctx


def test_choice_review_requires_executed_reports_and_full_native_choice_coverage():
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, ctx = review_inputs()
    rows, accepted = review_dimensions(doc, **ctx)
    assert rows[IDENTITY]['state'] == 'reviewed', rows
    assert accepted


@pytest.mark.parametrize(
    'missing',
    [
        '329-3-6-1-1',
        'other-357-5-8-3-3',
        'other-17-40-8-3-3',
        'cold-component-86-None',
        'cold-unknown-ethereal',
        'choice-pair-330-332',
    ],
)
def test_missing_choice_boundary_keeps_review_open(missing):
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, ctx = review_inputs()
    del doc['rows'][0]['cases']['opal-trade/' + missing]
    rows, accepted = review_dimensions(doc, **ctx)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize(
    'mutation',
    [
        'absent',
        'fingerprint',
        'snapshot',
        'enough-sellers',
        'thin-supported',
        'wrong-verdict',
        'wrong-color',
        'fixed-proc',
        'duplicate',
    ],
)
def test_choice_review_rejects_stale_census_and_rebound_incorrect_reports(mutation):
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    doc, ctx = review_inputs()
    review = doc['rows'][0]
    evidence = ctx['partial_evidence'][IDENTITY]
    if mutation == 'absent':
        ctx['partial_evidence'] = {}
    elif mutation == 'fingerprint':
        review['unresolved_evidence_fingerprint'] = 'stale'
    elif mutation == 'snapshot':
        evidence['market_snapshot']['sha256'] = 'stale'
    elif mutation == 'enough-sellers':
        evidence['choices']['lightning']['priced_sellers'] = ['a', 'b', 'c']
        evidence['choices']['lightning']['priced_rows'] = ['a', 'b', 'c']
    elif mutation == 'thin-supported':
        evidence['choices']['fire']['priced_sellers'] = ['a']
    else:
        key = 'opal-trade/329-3-6-1-1'
        case = ctx['receipts'][review['receipt']]['cases'][key]['trade_case']
        if mutation == 'wrong-verdict':
            case['checks']['qualification']['status'] = 'premium'
        elif mutation == 'wrong-color':
            case['checks']['lines'][0]['tone'] = 'tier_high'
        elif mutation == 'fixed-proc':
            case['item']['raw_stats'] = [r for r in case['item']['raw_stats'] if r[0] != 195]
        else:
            case['item']['raw_stats'] = (*case['item']['raw_stats'], (329, 0, 3))
        review['cases'][key] = fingerprint(case)
    if mutation not in ('absent', 'fingerprint'):
        review['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    rows, accepted = review_dimensions(doc, **ctx)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted
