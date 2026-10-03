"""Dracul review requires native rolls, fixed combat effects and executed boundaries."""

from copy import deepcopy
from dataclasses import asdict

import pytest

from pricing.knowledge.assessment.maintenance import trade_draculs
from tests.pricing.knowledge.assessment.item_bank.cases.draculs_trade import CASES
from tests.pricing.knowledge.assessment.maintenance.test_fixed_armor_trade_reviews import inputs


def bank():
    return [
        (
            asdict(c.item),
            c.trade_checks,
            tuple(getattr(c.item, k) for k in ('identified', 'ethereal', 'sockets', 'socket_contents')),
        )
        for c in CASES
    ]


def test_current_native_definition_and_report_boundaries():
    policy, definitions, stats = inputs(('unique', "Dracul's Grasp"))
    spec = trade_draculs.specification(policy, definitions, stats)
    assert spec is not None
    assert trade_draculs.case_gap(bank(), policy, spec) is None


@pytest.mark.parametrize('mutation', ['threshold', 'native-proc', 'socketable', 'stat-operation'])
def test_changed_semantics_need_another_review(mutation):
    policy, definitions, stats = inputs(('unique', "Dracul's Grasp"))
    if mutation == 'threshold':
        policy['trade_qualification']['bands'][0]['when']['value'] = 9
    elif mutation == 'native-proc':
        definitions[0]['game_definition']['par4'] = 'Amplify Damage'
    elif mutation == 'socketable':
        definitions[0]['base_definition']['gemsockets'] = 1
    else:
        stats['60']['shift'] = 8
    assert trade_draculs.specification(policy, definitions, stats) is None


@pytest.mark.parametrize('mutation', ['corner', 'missing-roll', 'unknown-variant', 'proc', 'defense', 'color'])
def test_incomplete_or_incorrect_reports_cannot_close_review(mutation):
    policy, definitions, stats = inputs(('unique', "Dracul's Grasp"))
    spec = trade_draculs.specification(policy, definitions, stats)
    cases = deepcopy(bank())
    if mutation == 'corner':
        cases.pop(0)
    elif mutation == 'missing-roll':
        cases = [c for c in cases if any(s[0] == 60 for s in c[0]['raw_stats'])]
    elif mutation == 'unknown-variant':
        cases = [c for c in cases if c[2][1] is not None]
    elif mutation == 'proc':
        cases[0][0]['raw_stats'] = tuple(s for s in cases[0][0]['raw_stats'] if s[0] != 198)
    elif mutation == 'defense':
        cases[0][0]['raw_stats'] = tuple((31, 0, 999) if s[0] == 31 else s for s in cases[0][0]['raw_stats'])
    else:
        next(c for c in cases if c[1]['lines'])[1]['lines'][0]['tone'] = 'tier_high'
    assert trade_draculs.case_gap(cases, policy, spec)


IDENTITY = ('unique', "Dracul's Grasp")


def review_inputs():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_draculs_evidence import audit
    from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import data

    document, context = data(IDENTITY, CASES)
    row = document['rows'][0]
    row['scope'] = 'native_unique_lifetap_gloves'
    evidence = audit(map(json.loads, Path('pricing/data/appraisal-market.jsonl').read_text().splitlines()))
    evidence['market_snapshot'] = deepcopy(context['policies'][IDENTITY]['trade_qualification']['market_snapshot'])
    row['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    context['partial_evidence'] = {IDENTITY: evidence}
    return document, context


def test_current_cohorts_and_executed_reports_can_close_the_review():
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    document, context = review_inputs()
    dimensions, accepted = review_dimensions(document, **context)
    assert dimensions[IDENTITY]['state'] == 'reviewed'
    assert accepted


@pytest.mark.parametrize('mutation', ['census', 'lower-cohort', 'failed-case', 'generation'])
def test_stale_evidence_or_failed_execution_cannot_close_review(mutation):
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    document, context = review_inputs()
    receipt = next(iter(context['receipts'].values()))
    evidence = context['partial_evidence'][IDENTITY]
    if mutation == 'census':
        evidence['cohorts']['perfect_leech']['rows'].pop()
    elif mutation == 'lower-cohort':
        evidence['cohorts']['lower_leech'] = {'rows': ['a', 'b', 'c'], 'sellers': ['a', 'b', 'c'], 'barter_rows': []}
        document['rows'][0]['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    elif mutation == 'failed-case':
        next(iter(receipt['cases'].values()))['phases']['call'] = 'failed'
    else:
        receipt['generation'] = 'old'
    dimensions, accepted = review_dimensions(document, **context)
    assert dimensions[IDENTITY]['state'] == 'pending'
    assert not accepted
