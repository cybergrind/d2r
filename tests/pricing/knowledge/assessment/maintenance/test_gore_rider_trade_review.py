"""Executed variant boundaries, not a policy's existence, close Gore Rider review."""

from copy import deepcopy
from dataclasses import asdict

import pytest

from pricing.knowledge.assessment.maintenance import trade_gore_rider
from tests.pricing.knowledge.assessment.maintenance.test_fixed_armor_trade_reviews import inputs


IDENTITY = ('unique', 'Gore Rider')


def bank():
    from tests.pricing.knowledge.assessment.item_bank.cases.gore_rider_trade import CASES as ORIGINAL
    from tests.pricing.knowledge.assessment.item_bank.cases.gore_rider_upgraded_trade import CASES as UPGRADED

    return [
        (
            asdict(c.item),
            c.trade_checks,
            tuple(getattr(c.item, k) for k in ('identified', 'ethereal', 'sockets', 'socket_contents')),
        )
        for c in (*ORIGINAL, *UPGRADED)
    ]


def test_native_definition_and_executed_bank_cover_both_variants():
    policy, definitions, specs = inputs(IDENTITY)
    spec = trade_gore_rider.specification(policy, definitions, specs)
    assert spec is not None
    assert trade_gore_rider.case_gap(bank(), policy, spec) is None


@pytest.mark.parametrize('mutation', ['threshold', 'socketable', 'variable-fixed-bonus', 'stat-operation'])
def test_changed_native_or_trade_semantics_require_review(mutation):
    policy, definitions, specs = inputs(IDENTITY)
    if mutation == 'threshold':
        policy['trade_qualification']['bands'][1]['when']['all'][1]['value'] = 199
    elif mutation == 'socketable':
        definitions[0]['base_definition']['gemsockets'] = 1
    elif mutation == 'variable-fixed-bonus':
        definitions[0]['game_definition']['max4'] = 20
    else:
        specs['16']['shift'] = 8
    assert trade_gore_rider.specification(policy, definitions, specs) is None


@pytest.mark.parametrize('mutation', ['minimum-base', 'missing-roll', 'unknown-variant', 'fixed-bonus', 'color'])
def test_case_presence_cannot_hide_missing_or_wrong_boundary_reports(mutation):
    policy, definitions, specs = inputs(IDENTITY)
    spec = trade_gore_rider.specification(policy, definitions, specs)
    cases = deepcopy(bank())
    if mutation == 'minimum-base':
        cases = [c for c in cases if not (c[0]['base'] == 'Myrmidon Greaves' and (31, 0, 186) in c[0]['raw_stats'])]
    elif mutation == 'missing-roll':
        cases = [c for c in cases if any(s[0] == 16 for s in c[0]['raw_stats'])]
    elif mutation == 'unknown-variant':
        cases = [c for c in cases if c[2][1] is not None]
    elif mutation == 'fixed-bonus':
        cases[0][0]['raw_stats'] = tuple(r for r in cases[0][0]['raw_stats'] if r[0] != 136)
    else:
        next(c for c in cases if c[1]['lines'])[1]['lines'][0]['tone'] = 'tier_high'
    assert trade_gore_rider.case_gap(cases, policy, spec)


def review_inputs():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_gore_rider_evidence import audit
    from tests.pricing.knowledge.assessment.item_bank.cases.gore_rider_trade import CASES as ORIGINAL
    from tests.pricing.knowledge.assessment.item_bank.cases.gore_rider_upgraded_trade import CASES as UPGRADED
    from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import data

    document, context = data(IDENTITY, (*ORIGINAL, *UPGRADED))
    row = document['rows'][0]
    row['scope'] = 'native_unique_combat_boots'
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
        evidence['cohorts']['original']['rows'].pop()
    elif mutation == 'lower-cohort':
        evidence['cohorts']['upgraded_lower'] = {'rows': ['a', 'b', 'c'], 'sellers': ['a', 'b', 'c'], 'barter_rows': []}
        document['rows'][0]['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    elif mutation == 'failed-case':
        next(iter(receipt['cases'].values()))['phases']['call'] = 'failed'
    else:
        receipt['generation'] = 'old'
    dimensions, accepted = review_dimensions(document, **context)
    assert dimensions[IDENTITY]['state'] == 'pending'
    assert not accepted
