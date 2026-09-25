from datetime import date

from inventory_tracking.appraisal.sections import price_lines
from inventory_tracking.items.metadata import decode_stats, metadata
from pricing.knowledge.assessment.engine import assess_result
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.test_pipeline_context import database
from tests.pricing.knowledge.assessment.test_prepared_base_prices import armor


def filled_base():
    item = armor()
    gem = next(b for b in metadata()['bases'].values() if b['name'] == 'Perfect Topaz')
    item['item'].update(
        sockets=3,
        socket_contents='filled',
        filled_sockets=2,
        empty_sockets=1,
        socket_items=[
            {'base_code': gem['code'], 'name': gem['name'], 'unit_id': i + 1, 'position': i} for i in range(2)
        ],
    )
    decoded, affixes, unresolved = decode_stats(
        [
            {'id': 31, 'layer': 0, 'raw': 250},
            {'id': 80, 'layer': 0, 'raw': 48},
        ]
    )
    assert not unresolved
    item['decoded_stats'] = decoded
    item['item']['affixes'] = affixes
    return item


def test_cleared_base_quote_removes_socket_effects_and_retains_current_item(tmp_path):
    item = filled_base()
    assessment = assess_result(item, profiles=[])
    clear = next(
        (r for r in assessment.comparison_requests if r.preparation and r.preparation['action'] == 'clear_sockets'),
        None,
    )
    assert clear is not None
    prop = assessment.facts.stats['80:0']['market_property']
    assert prop not in clear.contract['properties']
    assert clear.contract['properties']['1855'] == 250
    assert clear.contract['socket_contents'] == 'empty'
    assert clear.contract['socket_payload'] == ()
    assert clear.contract['sockets'] == 3
    assert clear.preparation['destroys_contents'] is True
    assert clear.preparation['destroyed_items'] == ('Perfect Topaz', 'Perfect Topaz')
    assert assessment.contract.properties[prop] == 48
    assert assessment.facts.socket_contents == 'filled'
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
    result = retrieve_draft(item, database(tmp_path, rows), as_of=date(2026, 9, 25))
    assert result['price_estimate']['estimate_ist'] is None
    quote = next(r for r in result['assessment']['comparison_results'] if r['state'] == 'prepared')
    assert quote['outcome_ask_estimate']['estimate_ist'] == 1
    text = '\n'.join(price_lines(result))
    assert 'After clearing: 3 empty sockets' in text
    assert 'Hel' in text
    assert 'Scroll of Town Portal' in text
    assert 'Destroys: 2 x Perfect Topaz' in text


def test_unknown_or_unexplained_socket_effects_do_not_create_empty_base_quotes():
    for mutate in (
        lambda item: item['item'].update(socket_items=[]),
        lambda item: item['item']['socket_items'][0].update(base_code='unknown'),
        lambda item: item['item'].update(filled_sockets=3),
        lambda item: item['source'].clear(),
    ):
        item = filled_base()
        mutate(item)
        assert not any(r.preparation for r in assess_result(item, profiles=[]).comparison_requests)


def test_clearing_shield_preserves_inherent_resistances():
    from pricing.knowledge.assessment.handlers.exact import BaseHandler
    from pricing.knowledge.assessment.mechanics.prepared_comparisons import socket_outcome_requests
    from tests.pricing.knowledge.assessment.test_socket_survival_comparisons import socketed_item

    facts = socketed_item('Sacred Targe', 'normal', None, ['Perfect Diamond'] * 4, dict.fromkeys((39, 41, 43, 45), 121))
    contract, gaps = BaseHandler().contract(facts, 'shield')
    assert contract is not None, gaps
    (clear,) = socket_outcome_requests(facts, contract, [])
    for stat in (39, 41, 43, 45):
        prop = facts.stats[f'{stat}:0']['market_property']
        assert clear.contract['properties'][prop] == 45
        assert contract.properties[prop] == 121
