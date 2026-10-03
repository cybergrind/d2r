"""Native IK component reviews reject changed mechanics and incomplete reports."""

from copy import deepcopy
from dataclasses import asdict

import pytest

from pricing.knowledge.assessment.maintenance import trade_ik_components
from tests.pricing.knowledge.assessment.item_bank.cases.ik_detail_trade import CASES as DETAIL
from tests.pricing.knowledge.assessment.item_bank.cases.ik_forge_trade import CASES as FORGE
from tests.pricing.knowledge.assessment.maintenance.test_fixed_armor_trade_reviews import inputs


@pytest.mark.parametrize(('name', 'bank'), [("Immortal King's Forge", FORGE), ("Immortal King's Detail", DETAIL)])
def test_native_component_and_report_boundaries(name, bank):
    policy, definitions, stats = inputs(('set', name))
    spec = trade_ik_components.specification(policy, definitions, stats)
    assert spec is not None
    cases = [
        (
            asdict(c.item),
            c.trade_checks,
            tuple(getattr(c.item, k) for k in ('identified', 'ethereal', 'sockets', 'socket_contents')),
        )
        for c in bank
    ]
    assert trade_ik_components.case_gap(cases, policy, spec) is None
    changed = deepcopy(cases)
    changed[0][0]['raw_stats'] = tuple(s for s in changed[0][0]['raw_stats'] if s[0] != 0)
    assert trade_ik_components.case_gap(changed, policy, spec)
    changed = deepcopy(cases)
    changed[0][0]['raw_stats'] = tuple((31, 0, 999) if s[0] == 31 else s for s in changed[0][0]['raw_stats'])
    assert trade_ik_components.case_gap(changed, policy, spec)
    assert trade_ik_components.case_gap([c for c in cases if c[2][1] is not None], policy, spec)
    definitions[0]['game_definition']['amin3a'] += 1
    assert trade_ik_components.specification(policy, definitions, stats) is None


@pytest.mark.parametrize(('name', 'bank'), [("Immortal King's Forge", FORGE), ("Immortal King's Detail", DETAIL)])
def test_executed_receipt_closes_only_current_component(name, bank):
    from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions
    from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import data

    identity = ('set', name)
    document, context = data(identity, bank)
    document['rows'][0]['scope'] = 'native_fixed_ik_component'
    states, accepted = review_dimensions(document, **context)
    assert states[identity]['state'] == 'reviewed', states[identity]
    assert accepted
    next(iter(context['receipts'].values()))['generation'] = 'old'
    assert review_dimensions(document, **context)[0][identity]['state'] == 'pending'
