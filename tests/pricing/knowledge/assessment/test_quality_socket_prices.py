from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers import HANDLERS
from pricing.knowledge.assessment.mechanics.prepared_comparisons import socket_outcome_requests
from tests.pricing.knowledge.assessment.test_filled_affixed import filled_armor
from tests.pricing.knowledge.assessment.test_socket_survival_comparisons import socketed_item


@pytest.mark.parametrize(('quality', 'targets'), [('magic', [1, 2]), ('rare', [1]), ('crafted', [1])])
def test_quality_controls_quest_socket_outcome_contracts(quality, targets):
    facts = replace(filled_armor(quality, innate=15, count=0, base='Helm'), socket_contents='empty', gaps=())
    contract, gaps = HANDLERS['affixed'].contract(facts, 'helm')
    assert contract is not None, gaps
    requests = socket_outcome_requests(facts, contract, [])
    assert [r.contract['sockets'] for r in requests] == targets
    for request in requests:
        assert request.state == 'prepared'
        assert request.contract['properties'] == contract.properties
        assert request.contract['rarity'] == quality
        outcome = request.preparation['outcomes'][0]
        assert outcome['success_weight'] == 1
        assert outcome['denominator'] == (2 if quality == 'magic' else 1)
        assert 'item_level' not in request.preparation['preconditions']
    assert facts.sockets == 0


@pytest.mark.parametrize(
    ('base', 'quality', 'name', 'family'),
    [
        ('Sallet', 'unique', 'Rockstopper', 'helm'),
        ('Basinet', 'set', "Sazabi's Mental Sheath", 'helm'),
    ],
)
def test_named_quest_socket_keeps_identity_and_rolls(base, quality, name, family):
    facts = replace(socketed_item(base, quality, name, [], {}), socket_contents='empty', gaps=())
    contract, gaps = HANDLERS['named'].contract(facts, family)
    assert contract is not None, gaps
    (request,) = socket_outcome_requests(facts, contract, [])
    assert request.contract['sockets'] == 1
    assert request.contract['name'] == name
    assert request.contract['properties'] == contract.properties
    assert request.contract['intrinsic_properties'] == contract.intrinsic_properties


def test_magic_socket_quote_shows_random_chance_and_preserves_current_price():
    from datetime import date

    from inventory_tracking.appraisal.prepared_prices import prepared_price_lines
    from pricing.knowledge.assessment.comparison_requests import evaluate_requests
    from pricing.knowledge.names import normalize_name

    facts = replace(filled_armor('magic', innate=15, count=0, base='Helm'), socket_contents='empty', gaps=())
    contract, _ = HANDLERS['affixed'].contract(facts, 'helm')
    requests = socket_outcome_requests(facts, contract, [])
    rows = [
        {
            **request.to_dict()['contract'],
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': f'{request.request_id}-{i}',
            'ask_ist': 1,
            'observed_at': '2026-09-25',
        }
        for request in requests
        for i in range(3)
    ]
    results = evaluate_requests(requests, {normalize_name(contract.name): rows}, today=date(2026, 9, 25))
    assert all(r['price_estimate']['estimate_ist'] is None for r in results)
    assert all(r['outcome_ask_estimate']['estimate_ist'] == 1 for r in results)
    text = '\n'.join(prepared_price_lines({'assessment': {'comparison_results': results}}))
    assert 'If Larzuk gives 2 empty sockets' in text
    assert '50%' in text
    assert 'Item level is unknown' not in text
    assert 'Larzuk socket reward' in text
