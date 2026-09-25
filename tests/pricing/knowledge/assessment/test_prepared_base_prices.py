from datetime import date

from inventory_tracking.appraisal.sections import price_lines
from pricing.knowledge.assessment.engine import assess_result
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.test_base_use import capture
from tests.pricing.knowledge.assessment.test_pipeline_context import database


def armor():
    item = capture('Mage Plate', sockets=0, ethereal=False, quality='normal', ed=0, ar=0)
    item['decoded_stats'] = [{'status': 'decoded', 'value': 250, 'memory_stat': {'id': 31, 'layer': 0, 'raw': 250}}]
    return item


def test_larzuk_outcome_asks_are_separate_from_current_base_price(tmp_path):
    item = armor()
    outcome = assess_result(item, profiles=[])
    prepared = [r for r in outcome.comparison_requests if r.preparation and r.preparation['action'] == 'larzuk']
    assert len(prepared) == 1
    request = prepared[0]
    assert request.contract['sockets'] == 3
    assert outcome.facts.sockets == 0
    assert outcome.contract.sockets == 0
    assert request.preparation['action'] == 'larzuk'
    assert request.preparation['resources']
    rows = [
        {
            **request.to_dict()['contract'],
            'kind': 'market',
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'ask_ist': value,
            'observed_at': '2026-09-25',
        }
        for i, value in enumerate((1, 2, 3))
    ]
    result = retrieve_draft(item, database(tmp_path, rows), as_of=date(2026, 9, 25))
    assert result['price_estimate']['estimate_ist'] is None
    prepared_result = next(r for r in result['assessment']['comparison_results'] if r['state'] == 'prepared')
    assert prepared_result['price_estimate']['estimate_ist'] is None
    assert prepared_result['outcome_ask_estimate']['estimate_ist'] == 2
    text = '\n'.join(price_lines(result))
    assert 'After Larzuk: 3 empty sockets' in text
    assert '1-3 Ist' in text
    assert 'quest reward' in text
    assert '2026-09-25' in text
    stale = retrieve_draft(item, database(tmp_path, rows), as_of=date(2026, 11, 1))
    assert 'After Larzuk' not in '\n'.join(price_lines(stale))


def test_incomplete_or_impossible_outcomes_are_not_quoted():
    incomplete = armor()
    incomplete['source'] = {}
    for item in (incomplete, capture('Phase Blade', sockets=0, ethereal=False)):
        assert all(r.state == 'observed' for r in assess_result(item, profiles=[]).comparison_requests)


def test_cube_outcome_quote_retains_probability_and_consumed_ingredients(tmp_path):
    item = armor()
    requests = assess_result(item, profiles=[]).comparison_requests
    cube = next((r for r in requests if r.preparation and r.preparation['action'] == 'cube_socket'), None)
    assert cube is not None
    assert cube.contract['sockets'] == 3
    assert cube.preparation['outcomes'] == ({'maximum': 3, 'success_weight': 4, 'denominator': 6},)
    rows = [
        {
            **cube.to_dict()['contract'],
            'kind': 'market',
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'ask_ist': 2,
            'observed_at': '2026-09-25',
        }
        for i in range(3)
    ]
    result = retrieve_draft(item, database(tmp_path, rows), as_of=date(2026, 9, 25))
    assert result['price_estimate']['estimate_ist'] is None
    text = '\n'.join(price_lines(result))
    assert 'If cube gives 3 empty sockets' in text
    assert '66.7%' in text
    for cost in ('Tal', 'Thul', 'Perfect Topaz'):
        assert cost in text
    assert 'expected value' not in text
    assert all(r['price_estimate']['estimate_ist'] is None for r in result['assessment']['comparison_results'])


def test_cube_outcome_keeps_unknown_level_caps_and_excludes_superior():
    item = capture(sockets=0, quality='normal', ed=0, ar=0)
    item['decoded_stats'] = []
    requests = assess_result(item, profiles=[]).comparison_requests
    cube = next(
        (
            r
            for r in requests
            if r.preparation and r.preparation['action'] == 'cube_socket' and r.contract['sockets'] == 4
        ),
        None,
    )
    assert cube is not None
    assert cube.preparation['action'] == 'cube_socket'
    assert 'item_level' in cube.preparation['preconditions']
    chances = cube.preparation['outcomes']
    assert any(r['success_weight'] == 0 for r in chances)
    assert any(r['success_weight'] > 0 for r in chances)
    superior = assess_result(capture(sockets=0), profiles=[]).comparison_requests
    assert all(r.preparation['action'] == 'larzuk' for r in superior if r.preparation)


def test_unknown_level_larzuk_quote_is_conditional_and_does_not_price_current_item(tmp_path):
    from inventory_tracking.items.metadata import decode_stats

    item = capture(sockets=0, quality='superior')
    decoded, affixes, unresolved = decode_stats([r['memory_stat'] for r in item['decoded_stats']])
    assert not unresolved
    item['decoded_stats'] = decoded
    item['item']['affixes'] = affixes
    result = assess_result(item, profiles=[])
    request = next(
        (
            r
            for r in result.comparison_requests
            if r.preparation and r.preparation['action'] == 'larzuk' and r.contract['sockets'] == 4
        ),
        None,
    )
    assert request is not None
    assert request.preparation['feasibility'] == 'conditional'
    rows = [
        {
            **request.to_dict()['contract'],
            'kind': 'market',
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'ask_ist': 2,
            'observed_at': '2026-09-25',
        }
        for i in range(3)
    ]
    report = retrieve_draft(item, database(tmp_path, rows), as_of=date(2026, 9, 25))
    assert report['price_estimate']['estimate_ist'] is None
    text = '\n'.join(price_lines(report))
    assert 'If Larzuk gives 4 empty sockets' in text
    assert 'Possible counts: 3, 4, 6' in text
    assert 'Item level is unknown' in text
    assert 'After Larzuk: 4' not in text
