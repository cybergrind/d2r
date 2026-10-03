"""A published roll rule is not a complete review without native boundary reports."""

from copy import deepcopy
from dataclasses import asdict

import pytest

from pricing.knowledge.assessment.maintenance import trade_war_traveler
from tests.pricing.knowledge.assessment.maintenance.test_fixed_armor_trade_reviews import inputs


IDENTITY = ('unique', 'War Traveler')


def test_native_review_accepts_only_the_reviewed_magic_find_rule():
    spec = trade_war_traveler.specification(*inputs(IDENTITY))
    assert spec is not None
    assert spec['upgraded_base'] == 'Mirrored Boots'


@pytest.mark.parametrize('mutation', ['threshold', 'ethereal', 'base', 'range', 'stat-operation', 'extra-property'])
def test_native_review_rejects_changed_semantics(mutation):
    policy, definitions, specs = inputs(IDENTITY)
    if mutation == 'threshold':
        policy['trade_qualification']['bands'][0]['when']['value'] = 49
    elif mutation == 'ethereal':
        policy['trade_qualification']['valid_if']['all'][0]['value'] = True
    elif mutation == 'base':
        definitions[0]['base_definition']['gemsockets'] = 1
    elif mutation == 'range':
        definitions[0]['roll_ranges']['80']['max'] = 55
    elif mutation == 'stat-operation':
        specs['80']['shift'] = 8
    else:
        definitions[0]['game_definition']['prop10'] = 'ac'
    assert trade_war_traveler.specification(policy, definitions, specs) is None


def bank():
    from tests.pricing.knowledge.assessment.item_bank.cases.war_traveler_trade import CASES

    return [
        (
            asdict(c.item),
            c.trade_checks,
            tuple(getattr(c.item, k) for k in ('identified', 'ethereal', 'sockets', 'socket_contents')),
        )
        for c in CASES
    ]


def test_native_bank_covers_roll_and_variant_boundaries():
    policy, definitions, specs = inputs(IDENTITY)
    spec = trade_war_traveler.specification(policy, definitions, specs)
    assert trade_war_traveler.case_gap(bank(), policy, spec) is None


@pytest.mark.parametrize('mutation', ['minimum', 'unknown', 'color', 'native-stat'])
def test_presence_of_cases_does_not_approve_incomplete_or_wrong_reports(mutation):
    policy, definitions, specs = inputs(IDENTITY)
    spec = trade_war_traveler.specification(policy, definitions, specs)
    cases = deepcopy(bank())
    if mutation == 'minimum':
        cases = [c for c in cases if (80, 0, 30) not in c[0]['raw_stats']]
    elif mutation == 'unknown':
        cases = [c for c in cases if c[2][1] is not None]
    elif mutation == 'color':
        next(c for c in cases if c[1]['lines'])[1]['lines'][0]['tone'] = 'tier_high'
    else:
        cases[0][0]['raw_stats'] = tuple(r for r in cases[0][0]['raw_stats'] if r[0] != 96)
    assert trade_war_traveler.case_gap(cases, policy, spec)


def review_inputs():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_war_traveler_evidence import audit
    from tests.pricing.knowledge.assessment.item_bank.cases.war_traveler_trade import CASES
    from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import data

    document, context = data(IDENTITY, CASES)
    row = document['rows'][0]
    row['scope'] = 'native_unique_mf_boots'
    evidence = audit(json.loads(line) for line in Path('pricing/data/appraisal-market.jsonl').read_text().splitlines())
    evidence['market_snapshot'] = deepcopy(context['policies'][IDENTITY]['trade_qualification']['market_snapshot'])
    row['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    context['partial_evidence'] = {IDENTITY: evidence}
    return document, context


def test_executed_native_reports_and_source_census_can_close_the_review():
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    document, context = review_inputs()
    dimensions, receipts = review_dimensions(document, **context)
    assert dimensions[IDENTITY]['state'] == 'reviewed'
    assert receipts


@pytest.mark.parametrize('mutation', ['census', 'lower-cohort', 'failed-case', 'generation'])
def test_claimed_coverage_requires_matching_evidence_and_execution(mutation):
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    document, context = review_inputs()
    receipt = next(iter(context['receipts'].values()))
    evidence = context['partial_evidence'][IDENTITY]
    if mutation == 'census':
        evidence['cohorts']['perfect']['rows'].pop()
    elif mutation == 'lower-cohort':
        evidence['cohorts']['lower'] = {'rows': ['a', 'b', 'c'], 'sellers': ['a', 'b', 'c'], 'barter_rows': []}
        document['rows'][0]['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    elif mutation == 'failed-case':
        next(iter(receipt['cases'].values()))['phases']['call'] = 'failed'
    else:
        receipt['generation'] = 'old'
    dimensions, accepted = review_dimensions(document, **context)
    assert dimensions[IDENTITY]['state'] == 'pending'
    assert not accepted
