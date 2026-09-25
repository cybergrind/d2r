from datetime import date

import pytest

from pricing.knowledge.assessment.maintenance.replay import replay
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.test_pipeline_context import database


def cohort(stem, prices):
    saved = replay(stem)
    contract = saved['assessment']['contract']
    rows = [
        {
            **{k: contract[k] for k in ('name', 'rarity', 'ethereal', 'sockets', 'socket_contents', 'base_code')},
            'kind': 'market',
            'properties': dict(contract['properties']),
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'ask_ist': price,
            'observed_at': '2026-09-25',
        }
        for i, price in enumerate(prices)
    ]
    return saved['extraction'], rows


@pytest.mark.parametrize(
    ('stem', 'prices', 'tier'),
    [
        ('sazabi_mental_sheath', [0.1, 0.1, 0.15], 'trash'),
        ('atma_scarab', [0.2, 0.4, 0.7], 'low'),
        ('atma_scarab', [0.8, 1, 2.4], 'med'),
        ('sazabi_mental_sheath', [2.5, 3, 4], 'high'),
    ],
)
def test_exact_named_ask_cohorts_can_supply_missing_trade_tier(tmp_path, stem, prices, tier):
    extraction, rows = cohort(stem, prices)
    result = retrieve_draft(extraction, database(tmp_path, rows), as_of=date(2026, 9, 25))
    assert result['price_estimate']['estimate_ist'] is not None
    outcome = result['assessment']['trade_tier']
    assert outcome['status'] == 'market_supported'
    assert outcome['tier'] == tier
    assert outcome['source']['request_id'] == 'current'
    assert outcome['source']['date'] == '2026-09-25'
    from inventory_tracking.appraisal.sections import tier_lines

    assert tier_lines(result) == [f'Trade tier: {tier} (cached asks, 2026-09-25)']


def test_band_crossing_tier_boundary_does_not_claim_a_single_tier(tmp_path):
    extraction, rows = cohort('atma_scarab', [0.7, 0.8, 1])
    result = retrieve_draft(extraction, database(tmp_path, rows), as_of=date(2026, 9, 25))
    tier = result['assessment']['trade_tier']
    assert tier['status'] == 'conditional'
    assert tier['tier'] is None
    assert tier['possible_tiers'] == ['low', 'med']


def test_thin_stale_or_wrong_variant_asks_do_not_fill_tier_gap(tmp_path):
    extraction, rows = cohort('atma_scarab', [1, 1, 1])
    db = database(tmp_path, rows)
    fresh = retrieve_draft(extraction, db, as_of=date(2026, 9, 25))
    assert fresh['assessment']['trade_tier']['status'] == 'market_supported'
    stale = retrieve_draft(extraction, db, as_of=date(2026, 11, 1))
    assert stale['price_estimate']['excluded_observations'] == {'stale': 3}
    assert stale['assessment']['trade_tier']['status'] == 'pending_review'

    rows[-1]['ethereal'] = True
    thin = retrieve_draft(extraction, database(tmp_path, rows), as_of=date(2026, 9, 25))
    assert thin['price_estimate']['estimate_ist'] is None
    assert thin['assessment']['trade_tier']['status'] == 'pending_review'


def test_existing_tier_and_noncurrent_results_are_not_reclassified(tmp_path):
    from copy import deepcopy

    from pricing.knowledge.assessment.adapters.capture import normalize
    from pricing.knowledge.assessment.policies.market_tiers import resolve_market_tier

    extraction, rows = cohort('atma_scarab', [1, 1, 1])
    result = retrieve_draft(extraction, database(tmp_path, rows), as_of=date(2026, 9, 25))
    current = result['assessment']['comparison_results'][0]
    facts = normalize(extraction)
    reviewed = {'status': 'reviewed', 'tier': 'high'}
    conditional = {'status': 'conditional', 'tier': None, 'possible_tiers': ['low', 'high']}
    for tier in (reviewed, conditional):
        assert resolve_market_tier(facts, tier, current) is tier
    pending = {'status': 'pending_review', 'tier': None, 'possible_tiers': []}
    for key, value in (('state', 'prepared'), ('segment_id', 'another_role'), ('request_ids', ['another_item'])):
        assert resolve_market_tier(facts, pending, {**current, key: value}) is pending
    wrong = deepcopy(current)
    wrong['price_estimate']['scope'] = 'Ladder'
    assert resolve_market_tier(facts, pending, wrong) is pending
    wrong = deepcopy(current)
    wrong['contract']['name'] = 'Another item'
    assert resolve_market_tier(facts, pending, wrong) is pending
