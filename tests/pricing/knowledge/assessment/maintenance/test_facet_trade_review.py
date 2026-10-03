import json
from dataclasses import asdict

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.maintenance import trade_facets
from pricing.knowledge.assessment.policies.named_tiers import RULES
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.cases.facet_trade import CASES


def inputs():
    policy = next(p for p in json.loads(RULES.read_bytes())['policies'] if p['name'] == 'Rainbow Facet')
    variants = thaw(catalog().named_variants[('unique', 'Rainbow Facet')])
    spec = trade_facets.specification(policy, variants, metadata()['stats'])
    assert spec is not None
    cases = [
        (asdict(c.item), c.trade_checks, (c.item.identified, c.item.ethereal, c.item.sockets, c.item.socket_contents))
        for c in CASES
    ]
    return policy, spec, cases


def test_all_native_facet_boundaries_are_explicitly_asserted():
    policy, spec, cases = inputs()
    assert trade_facets.case_gap(cases, policy, spec) is None


@pytest.mark.parametrize(
    'missing',
    [
        '3-3',
        '4-5',
        '5-4',
        '5-5',
        'trigger-None',
        'trigger-99',
        'other-native-trigger',
        'unknown-sockets',
        'stat-330-None',
    ],
)
def test_missing_native_boundary_cannot_pass_review(missing):
    policy, spec, cases = inputs()
    cases = [row for row, case in zip(cases, CASES, strict=True) if not case.id.endswith('/' + missing)]
    assert trade_facets.case_gap(cases, policy, spec)
