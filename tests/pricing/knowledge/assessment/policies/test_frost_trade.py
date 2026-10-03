"""Cold-socket trade demand is separate from an unproven perfect-roll premium."""

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.cases.elemental_colossal_recipients import jewel


@pytest.mark.parametrize('perfect', [(), (331,), (335,), (85, 80, 79), (331, 335, 85, 80, 79)])
def test_frost_ordinary_demand_does_not_invent_a_perfect_premium(perfect):
    result = assess_trade_qualification(normalize(jewel('cold', perfect).capture()))
    assert result.get('status') == 'candidate'


def test_frost_ordinary_floor_uses_pinned_colossal_demand_evidence():
    import hashlib
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.policies.named_tiers import RULES

    policy = next(r for r in json.loads(RULES.read_bytes())['policies'] if r['name'] == "Protector's Frost")
    evidence = policy['trade_qualification']['demand_source']
    assert evidence['path'] == 'pricing/raw/mr/items__new-items-in-reign-of-the-warlock.html'
    assert hashlib.sha256(Path(evidence['path']).read_bytes()).hexdigest() == evidence['sha256']
    assert evidence['source_date'] == '2026-02-19'
    assert 'limited to 1 per character' in evidence['excerpt']
