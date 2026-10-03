import json
from dataclasses import asdict

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.maintenance import trade_torch
from pricing.knowledge.assessment.policies.named_tiers import RULES
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.cases.torch_trade import CASES


def inputs():
    policy = next(p for p in json.loads(RULES.read_bytes())['policies'] if p['name'] == 'Hellfire Torch')
    variants = thaw(catalog().named_variants['unique', 'Hellfire Torch'])
    spec = trade_torch.specification(policy, variants, metadata()['stats'])
    assert spec is not None
    cases = [
        (asdict(c.item), c.trade_checks, (c.item.identified, c.item.ethereal, c.item.sockets, c.item.socket_contents))
        for c in CASES
    ]
    return policy, spec, cases


def test_all_torch_cases_assert_class_roll_and_rendering_boundaries():
    policy, spec, cases = inputs()
    assert trade_torch.case_gap(cases, policy, spec) is None


def test_each_torch_case_is_required_for_this_native_review():
    policy, spec, cases = inputs()
    for index, case in enumerate(CASES):
        assert trade_torch.case_gap(cases[:index] + cases[index + 1 :], policy, spec), case.id


@pytest.mark.parametrize('field', ['qualification', 'lines'])
def test_unknown_class_cannot_inherit_positive_report_assertions(field):
    policy, spec, cases = inputs()
    index = next(i for i, row in enumerate(cases) if row[0]['raw_stats'][0][:2] == (83, 1))
    item, checks, variant = cases[index]
    checks = {
        **checks,
        field: {'status': 'candidate'}
        if field == 'qualification'
        else [{'text': 'Trade: candidate', 'tone': 'tier_high'}],
    }
    cases[index] = item, checks, variant
    assert trade_torch.case_gap(cases, policy, spec)
