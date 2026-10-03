import json
from copy import deepcopy
from dataclasses import asdict

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.maintenance import trade_stormshield
from pricing.knowledge.assessment.policies.named_tiers import RULES
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.cases.stormshield_trade import CASES


@pytest.fixture(scope='module')
def inputs():
    policy = trade_stormshield.bind_policy(
        next(p for p in json.loads(RULES.read_bytes())['policies'] if p['name'] == 'Stormshield')
    )
    variants = thaw(catalog().named_variants['unique', 'Stormshield'])
    specs = deepcopy(metadata()['stats'])
    cases = [
        (
            asdict(c.item),
            deepcopy(c.trade_checks),
            (c.item.identified, c.item.ethereal, c.item.sockets, c.item.socket_contents),
        )
        for c in CASES
    ]
    return policy, variants, specs, cases


def test_native_oracle_and_explicit_report_boundaries(inputs):
    policy, variants, specs, cases = inputs
    spec = trade_stormshield.specification(policy, variants, specs)
    assert spec
    assert trade_stormshield.case_gap(cases, policy, spec) is None


@pytest.mark.parametrize('change', ['coefficient', 'denominator', 'defense', 'binding'])
def test_native_or_source_changes_require_review(inputs, change):
    policy, variants, specs, _ = deepcopy(inputs)
    if change == 'coefficient':
        variants[0]['game_definition']['par1'] = 31
    elif change == 'denominator':
        specs['214']['op_param'] = 2
    elif change == 'defense':
        variants[0]['base_definition']['maxac'] = 149
    else:
        policy.pop('underlying_trade_validated_at')
    assert trade_stormshield.specification(policy, variants, specs) is None


@pytest.mark.parametrize('change', ['corner', 'missing-stat', 'lower-stat', 'higher-stat', 'color', 'verdict'])
def test_incomplete_or_wrong_report_contracts_fail(inputs, change):
    policy, variants, specs, cases = deepcopy(inputs)
    spec = trade_stormshield.specification(policy, variants, specs)
    if change == 'corner':
        cases.pop(0)
    elif change == 'missing-stat':
        cases = [r for r in cases if any(s == 36 for s, p, v in r[0]['raw_stats'])]
    elif change in ('lower-stat', 'higher-stat'):
        amount = 34 if change == 'lower-stat' else 36
        cases = [r for r in cases if (36, 0, amount) not in r[0]['raw_stats']]
    else:
        checks = next(c for _, c, _ in cases if c['lines'])
        if change == 'color':
            checks['lines'][0]['tone'] = 'tier_high'
        else:
            checks['qualification']['status'] = 'premium'
    assert trade_stormshield.case_gap(cases, policy, spec)


def gate_data():
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import data

    identity = ('unique', 'Stormshield')
    document, context = data(identity, CASES)
    policy = trade_stormshield.bind_policy(context['policies'][identity])
    context['policies'][identity] = policy
    document['rows'][0].update(scope='native_unique_underlying_stormshield', policy_fingerprint=fingerprint(policy))
    return document, context


def test_trade_registry_accepts_current_independent_contracts():
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    document, context = gate_data()
    dimensions, accepted = review_dimensions(document, **context)
    assert dimensions['unique', 'Stormshield']['state'] == 'reviewed'
    assert accepted


@pytest.mark.parametrize('change', ['case', 'execution', 'generation', 'policy'])
def test_registry_does_not_accept_missing_execution_or_stale_bindings(change):
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    document, context = gate_data()
    receipt = next(iter(context['receipts'].values()))
    if change == 'case':
        document['rows'][0]['cases'].pop(next(iter(document['rows'][0]['cases'])))
    elif change == 'execution':
        next(iter(receipt['cases'].values()))['phases']['call'] = 'failed'
    elif change == 'generation':
        receipt['generation'] = 'old'
    else:
        context['policies']['unique', 'Stormshield']['underlying_trade']['reviewed_at'] = '2025-01-01'
    dimensions, accepted = review_dimensions(document, **context)
    assert dimensions['unique', 'Stormshield']['state'] == 'pending'
    assert not accepted
