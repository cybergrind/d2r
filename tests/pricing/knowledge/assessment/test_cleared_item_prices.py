from dataclasses import replace

import pytest

from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.handlers import HANDLERS
from pricing.knowledge.assessment.mechanics.prepared_comparisons import socket_outcome_requests
from tests.pricing.knowledge.assessment.test_filled_affixed import filled_armor
from tests.pricing.knowledge.assessment.test_filled_topaz import multi_topaz_item, topaz_shako


@pytest.mark.parametrize('rarity', ['magic', 'rare', 'crafted'])
def test_clearing_affixed_armor_preserves_innate_magic_find(rarity):
    facts = filled_armor(rarity, innate=15, base='Helm' if rarity == 'crafted' else 'Cap')
    contract, gaps = HANDLERS['affixed'].contract(facts, 'helm')
    assert contract is not None, gaps
    requests = socket_outcome_requests(facts, contract, [])
    assert len(requests) == 1
    outcome = requests[0].contract
    prop = facts.stats['80:0']['market_property']
    assert outcome['properties'][prop] == 15
    assert contract.properties[prop] == 63
    assert outcome['rarity'] == rarity
    assert outcome['name'] == facts.base_name
    assert outcome['socket_contents'] == 'empty'


@pytest.mark.parametrize('kind', ['unique', 'set'])
def test_clearing_named_item_retains_identity_and_restores_fixed_property_rules(kind):
    facts = topaz_shako() if kind == 'unique' else multi_topaz_item('Ornate Armor', "Griswold's Heart", 'set', 3)
    family = 'helm' if kind == 'unique' else 'armor'
    contract, gaps = HANDLERS['named'].contract(facts, family)
    assert contract is not None, gaps
    requests = socket_outcome_requests(facts, contract, [])
    assert len(requests) == 1
    outcome = requests[0].contract
    prop = facts.stats['80:0']['market_property']
    assert outcome['name'] == facts.name
    assert outcome['base_code'] == facts.base_code
    assert outcome['rarity'] == kind
    assert outcome['socket_payload'] == ()
    if kind == 'unique':
        assert outcome['properties'][prop] == 50
        assert outcome['intrinsic_properties'][prop] == 50
        assert prop not in contract.intrinsic_properties
    else:
        assert prop not in outcome['properties']
    assert not socket_outcome_requests(replace(facts, socket_items=[]), contract, [])


def test_saved_um_shako_prices_empty_outcome_without_changing_filled_price(tmp_path):
    from datetime import date

    from pricing.knowledge.assessment.engine import assess_result
    from pricing.knowledge.assessment.maintenance.replay import replay
    from pricing.knowledge.pipeline import retrieve_draft
    from tests.pricing.knowledge.assessment.test_pipeline_context import database

    extraction = replay('harlequin_crest')['extraction']
    result = assess_result(extraction)
    clear = next(r for r in result.comparison_requests if r.preparation)
    assert clear.preparation['destroyed_items'] == ('Um Rune',)
    for prop in ('427', '428', '426', '401'):
        assert result.contract.properties[prop] == 15
        assert prop not in clear.contract['properties']
    rows = [
        {
            **clear.to_dict()['contract'],
            'kind': 'market',
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'ask_ist': 1,
            'observed_at': '2026-09-25',
        }
        for i in range(3)
    ]
    report = retrieve_draft(extraction, database(tmp_path, rows), as_of=date(2026, 9, 25))
    assert report['price_estimate']['estimate_ist'] is None
    prepared = next(r for r in report['assessment']['comparison_results'] if r['state'] == 'prepared')
    assert prepared['outcome_ask_estimate']['estimate_ist'] == 1
    assert prepared['price_estimate']['estimate_ist'] is None
    assert report['assessment']['trade_tier'] == thaw(result.trade_tier)
