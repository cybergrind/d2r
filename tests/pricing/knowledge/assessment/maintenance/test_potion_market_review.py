"""Ordinary potion pricing is reviewed separately from stacks and quest objects."""

from copy import deepcopy
from datetime import date

import pytest

from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.assessment.maintenance.potion_market_review import (
    apply_potion_market_reviews,
    audit_potions,
    build_review,
)
from tests.pricing.knowledge.test_market_consumables import imported


DAY = date(2026, 9, 28)


def test_potion_audit_uses_actual_import_and_single_unit_comparisons():
    observations = [imported('Super Healing Potion', str(i)) for i in range(3)]
    observations += [imported('Super Healing Potion', 'bulk', amount=40)]
    rows = audit_potions(observations, DAY)
    assert len(rows) == 15
    healing = next(r for r in rows if r['name'] == 'Super Healing Potion')
    assert healing['price']['estimate_ist'] == 1  # Synthetic fixture, not real prices.
    assert len(healing['accepted_observations']) == 3
    assert healing['cached_observations'] == 4
    assert healing['rejection_counts']
    assert all(r['price']['unavailable_reason'] == 'no_matches' for r in rows if r != healing)


def test_missing_potion_rule_is_not_reviewed_evidence_absence(monkeypatch):
    from pricing.knowledge.assessment.handlers.consumable import ConsumableHandler

    monkeypatch.setattr(ConsumableHandler, 'contract', lambda *a: (None, ['missing rule']))
    with pytest.raises(ValueError, match='comparison implementation'):
        audit_potions([], DAY)


@pytest.fixture(scope='module')
def reviewed():
    return build_review(ROOT, DAY)


def test_matrix_closes_only_exact_potion_identity_market(reviewed):
    from pricing.knowledge.assessment.maintenance.coverage_matrix import build_matrix
    from tests.pricing.knowledge.assessment.maintenance.test_coverage_matrix import inputs

    args = inputs()
    args[0]['identities'][0].update(name='Super Healing Potion', category='misc', catalog_ids=['hp5'])
    result = build_matrix(*args, potion_market_reviews=reviewed)
    row = next(r for r in result['rows'] if r['id'] == 'identity:u')
    assert row['dimensions']['market']['state'] == 'reviewed'
    assert row['dimensions']['market']['unit_quantity'] == 1
    assert row['dimensions']['desirability']['state'] == 'pending'
    assert row['dimensions']['report']['state'] == 'pending'


@pytest.mark.parametrize('change', ['omit_identity', 'forge_price', 'stale_input'])
def test_potion_review_rejects_omissions_tampering_and_stale_inputs(reviewed, change):
    review = deepcopy(reviewed)
    if change == 'omit_identity':
        review['rows'].pop()
    elif change == 'forge_price':
        review['rows'][0]['price']['estimate_ist'] = 999
    else:
        review['inputs']['pricing/knowledge/market_consumables.py'] = '0' * 64
    with pytest.raises(ValueError, match=r'[Pp]otion pricing review'):
        apply_potion_market_reviews([], review, ROOT)
