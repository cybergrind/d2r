from copy import deepcopy
from dataclasses import asdict

import pytest

from pricing.knowledge.assessment.maintenance import trade_crown
from tests.pricing.knowledge.assessment.maintenance.test_fixed_armor_trade_reviews import inputs


def source_inputs():
    policy, definitions, specs = inputs(('unique', 'Crown of Ages'))
    return trade_crown.bind_policy(policy), definitions, specs


def bank():
    from tests.pricing.knowledge.assessment.item_bank.cases.crown_trade import CASES

    return [
        (
            asdict(c.item),
            c.trade_checks,
            tuple(getattr(c.item, k) for k in ('identified', 'ethereal', 'sockets', 'socket_contents')),
        )
        for c in CASES
    ]


def test_bound_rule_and_native_report_boundaries_are_required():
    assert trade_crown.specification(*inputs(('unique', 'Crown of Ages'))) is None
    policy, definitions, specs = source_inputs()
    spec = trade_crown.specification(policy, definitions, specs)
    assert spec is not None
    assert trade_crown.case_gap(bank(), policy, spec) is None


@pytest.mark.parametrize('change', ['native', 'operation', 'binding', 'range'])
def test_changed_evidence_cannot_certify_crown(change):
    policy, definitions, specs = source_inputs()
    if change == 'native':
        definitions[0]['game_definition']['max6'] = 20
    elif change == 'operation':
        specs['36']['shift'] = 8
    elif change == 'binding':
        policy.pop('crown_trade_validated_at')
    else:
        definitions[0]['base_definition']['maxac'] = 160
    assert trade_crown.specification(policy, definitions, specs) is None


@pytest.mark.parametrize('change', ['missing-stat', 'incomplete', 'wrong-color'])
def test_incomplete_report_evidence_does_not_close_review(change):
    policy, definitions, specs = source_inputs()
    cases = deepcopy(bank())
    if change == 'missing-stat':
        cases = [c for c in cases if any(s == 36 for s, _, _ in c[0]['raw_stats'])]
    elif change == 'incomplete':
        cases = [c for c in cases if c[0]['complete']]
    else:
        next(c for c in cases if c[1]['lines'])[1]['lines'][0]['tone'] = 'tier_trash'
    assert trade_crown.case_gap(cases, policy, trade_crown.specification(policy, definitions, specs))


@pytest.mark.parametrize('stale', [False, True])
def test_review_requires_an_executed_current_generation(stale):
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions
    from tests.pricing.knowledge.assessment.item_bank.cases.crown_trade import CASES
    from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import data

    identity = ('unique', 'Crown of Ages')
    document, context = data(identity, CASES)
    policy = trade_crown.bind_policy(context['policies'][identity])
    context['policies'][identity] = policy
    document['rows'][0].update(scope='native_unique_crown_shell', policy_fingerprint=fingerprint(policy))
    if stale:
        next(iter(context['receipts'].values()))['generation'] = 'old-generation'
    states, accepted = review_dimensions(document, **context)
    assert states[identity]['state'] == ('pending' if stale else 'reviewed')
    assert bool(accepted) is not stale
