import json
from copy import deepcopy
from dataclasses import asdict

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.maintenance import trade_waterwalk
from pricing.knowledge.assessment.policies.named_tiers import RULES
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.cases.waterwalk_defense import CASES


@pytest.fixture
def inputs():
    policy = next(p for p in json.loads(read_artifact(RULES))['policies'] if p['name'] == 'Waterwalk')
    definitions = thaw(catalog().named_variants['unique', 'Waterwalk'])
    specs = deepcopy(metadata()['stats'])
    cases = [
        (
            asdict(c.item),
            deepcopy(c.trade_checks),
            (c.item.identified, c.item.ethereal, c.item.sockets, c.item.socket_contents),
        )
        for c in CASES
        if c.id.startswith('waterwalk-boundaries/')
    ]
    return policy, definitions, specs, cases


def test_native_boundaries_and_explicit_report_contracts_pass(inputs):
    policy, definitions, specs, cases = inputs
    spec = trade_waterwalk.specification(policy, definitions, specs)
    assert spec is not None
    assert trade_waterwalk.case_gap(cases, policy, spec) is None


@pytest.mark.parametrize('mutation', ['life-shift', 'extra-native-property', 'mapping', 'premium'])
def test_changed_native_or_policy_contract_is_rejected(inputs, mutation):
    policy, definitions, specs, _ = deepcopy(inputs)
    if mutation == 'life-shift':
        specs['7']['shift'] = 0
    elif mutation == 'extra-native-property':
        definitions[0]['game_definition']['prop9'] = 'ac'
    elif mutation == 'mapping':
        policy['trade_qualification']['market_stat_properties']['31:0'] = '399'
    else:
        policy['trade_qualification']['bands'][0]['status'] = 'premium'
    assert trade_waterwalk.specification(policy, definitions, specs) is None


@pytest.mark.parametrize(
    'mutation', ['missing-corner', 'missing-unknown', 'missing-per-level', 'wrong-fixed-stat', 'wrong-report']
)
def test_case_presence_alone_cannot_satisfy_review(inputs, mutation):
    policy, definitions, specs, cases = deepcopy(inputs)
    spec = trade_waterwalk.specification(policy, definitions, specs)
    if mutation == 'missing-corner':
        cases.pop(0)
    elif mutation == 'missing-unknown':
        cases = [r for r in cases if r[0]['ethereal'] is not None]
    elif mutation == 'missing-per-level':
        cases = [r for r in cases if not any(s == 214 for s, p, v in r[0]['raw_stats'])]
    elif mutation == 'wrong-fixed-stat':
        cases[0][0]['raw_stats'] = tuple((s, p, 99 if s == 32 else v) for s, p, v in cases[0][0]['raw_stats'])
    else:
        next(checks for item, checks, sig in cases if checks['lines'])['lines'][0]['tone'] = 'tier_high'
    assert trade_waterwalk.case_gap(cases, policy, spec)


def review_inputs():
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_waterwalk_evidence import audit
    from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import data

    identity = ('unique', 'Waterwalk')
    document, context = data(identity, [c for c in CASES if c.trade_checks])
    review = document['rows'][0]
    review['scope'] = 'native_unique_waterwalk'
    evidence = audit(map(json.loads, Path('pricing/data/appraisal-market.jsonl').read_text().splitlines()))
    evidence['market_snapshot'] = deepcopy(context['policies'][identity]['trade_qualification']['market_snapshot'])
    review['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    context['partial_evidence'] = {identity: evidence}
    return document, context


def test_current_source_bound_reports_can_satisfy_the_trade_review_gate():
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    document, context = review_inputs()
    dimensions, accepted = review_dimensions(document, **context)
    assert dimensions['unique', 'Waterwalk']['state'] == 'reviewed'
    assert accepted


@pytest.mark.parametrize('mutation', ['census', 'dense-cohort', 'failed-case', 'generation', 'missing-case'])
def test_invalid_integration_evidence_stays_pending(mutation):
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    document, context = review_inputs()
    receipt = next(iter(context['receipts'].values()))
    evidence = context['partial_evidence']['unique', 'Waterwalk']
    if mutation == 'census':
        evidence['original']['rows'].pop()
    elif mutation == 'dense-cohort':
        cohort = evidence['unresolved_cohorts'][0]
        cohort['rows'].extend(['new-a', 'new-b'])
        cohort['sellers'].extend(['new-seller-a', 'new-seller-b'])
        evidence['observations'] += 2
        document['rows'][0]['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    elif mutation == 'failed-case':
        next(iter(receipt['cases'].values()))['phases']['call'] = 'failed'
    elif mutation == 'missing-case':
        document['rows'][0]['cases'].pop(next(iter(document['rows'][0]['cases'])))
    else:
        receipt['generation'] = 'old'
    dimensions, accepted = review_dimensions(document, **context)
    assert dimensions['unique', 'Waterwalk']['state'] == 'pending'
    assert not accepted
