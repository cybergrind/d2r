"""Underlying-item coverage must bind the separate published Shako rule."""

from copy import deepcopy
from dataclasses import asdict

import pytest

from pricing.knowledge.assessment.maintenance import trade_shako
from tests.pricing.knowledge.assessment.maintenance.test_fixed_armor_trade_reviews import inputs


IDENTITY = ('unique', 'Harlequin Crest')


def source_inputs():
    policy, definitions, specs = inputs(IDENTITY)
    return trade_shako.bind_policy(policy), definitions, specs


def test_baseline_tier_alone_is_not_underlying_trade_coverage():
    assert trade_shako.specification(*inputs(IDENTITY)) is None
    assert trade_shako.specification(*source_inputs()) is not None


@pytest.mark.parametrize('change', ['range', 'socket', 'operation', 'fixed', 'separate-policy'])
def test_changed_native_or_separate_rule_invalidates_proof(change):
    policy, definitions, specs = source_inputs()
    if change == 'range':
        definitions[0]['base_definition']['minac'] = 97
    elif change == 'socket':
        definitions[0]['base_definition']['gemsockets'] = 3
    elif change == 'operation':
        specs['31']['shift'] = 8
    elif change == 'fixed':
        definitions[0]['game_definition']['min1'] = 1
    else:
        policy['underlying_trade']['id'] = 'other'
    assert trade_shako.specification(policy, definitions, specs) is None


def bank():
    from tests.pricing.knowledge.assessment.item_bank.cases.shako_trade import CASES

    return [
        (
            asdict(c.item),
            c.trade_checks,
            tuple(getattr(c.item, k) for k in ('identified', 'ethereal', 'sockets', 'socket_contents')),
        )
        for c in CASES
    ]


def test_native_defense_socket_and_unknown_boundaries_have_report_contracts():
    policy, definitions, specs = source_inputs()
    assert trade_shako.case_gap(bank(), policy, trade_shako.specification(policy, definitions, specs)) is None


@pytest.mark.parametrize('change', ['maximum', 'missing-defense', 'incomplete', 'wrong-color'])
def test_missing_or_wrong_reports_cannot_close_shako_review(change):
    policy, definitions, specs = source_inputs()
    cases = deepcopy(bank())
    if change == 'maximum':
        cases = [c for c in cases if (31, 0, 141) not in c[0]['raw_stats']]
    elif change == 'missing-defense':
        cases = [c for c in cases if any(s == 31 for s, _, _ in c[0]['raw_stats'])]
    elif change == 'incomplete':
        cases = [c for c in cases if c[0]['complete']]
    else:
        next(c for c in cases if c[1]['lines'])[1]['lines'][0]['tone'] = 'tier_high'
    assert trade_shako.case_gap(cases, policy, trade_shako.specification(policy, definitions, specs))


def review_inputs():
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from tests.pricing.knowledge.assessment.item_bank.cases.shako_trade import CASES
    from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import data

    document, context = data(IDENTITY, CASES)
    row = document['rows'][0]
    row['scope'] = 'native_unique_underlying_shako'
    policy = trade_shako.bind_policy(context['policies'][IDENTITY])
    context['policies'] = {**context['policies'], IDENTITY: policy}
    row['policy_fingerprint'] = fingerprint(policy)
    return document, context


def test_source_bound_underlying_rule_and_executed_reports_close_the_review():
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    document, context = review_inputs()
    rows, accepted = review_dimensions(document, **context)
    assert rows[IDENTITY]['state'] == 'reviewed'
    assert accepted


@pytest.mark.parametrize('change', ['binding', 'rule', 'receipt', 'generation', 'inputs'])
def test_stale_or_missing_implementation_binding_keeps_review_open(change):
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions

    document, context = review_inputs()
    receipt = next(iter(context['receipts'].values()))
    if change == 'binding':
        context['policies'][IDENTITY].pop('underlying_trade_validated_at')
        document['rows'][0]['policy_fingerprint'] = fingerprint(context['policies'][IDENTITY])
    elif change == 'rule':
        context['policies'][IDENTITY]['underlying_trade']['evidence_ids'] = []
    elif change == 'receipt':
        next(iter(receipt['cases'].values()))['phases']['call'] = 'failed'
    elif change == 'generation':
        receipt['generation'] = 'previous'
    else:
        receipt['finished_inputs'] = {'changed.py': 'new'}
    rows, accepted = review_dimensions(document, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted
