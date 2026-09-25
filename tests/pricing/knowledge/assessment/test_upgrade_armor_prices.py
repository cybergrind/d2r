from datetime import date

from inventory_tracking.appraisal.sections import price_lines
from pricing.knowledge.assessment.engine import assess_result
from pricing.knowledge.assessment.maintenance.replay import replay
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.test_pipeline_context import database


def armor_requests(result):
    return [r for r in result.comparison_requests if r.preparation and r.preparation['action'] == 'upgrade_armor']


def test_saved_sazabi_upgrade_prices_only_matching_defense_and_keeps_current_price(tmp_path):
    extraction = replay('sazabi_mental_sheath')['extraction']
    result = assess_result(extraction, profiles=[])
    requests = armor_requests(result)
    assert len(requests) == 45
    assert {r.contract['properties']['1855'] for r in requests} == set(range(210, 255))
    request = next(r for r in requests if r.contract['properties']['1855'] == 254)
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
    # A fourth seller offers another possible roll; it must not change this quote.
    rows.append(
        {
            **rows[0],
            'seller_id': 'other',
            'listing_id': 'other',
            'ask_ist': 100,
            'properties': {**rows[0]['properties'], '1855': 253},
        }
    )
    report = retrieve_draft(extraction, database(tmp_path, rows), as_of=date(2026, 9, 25))
    assert report['price_estimate']['estimate_ist'] is None
    quoted = [
        r
        for r in report['assessment']['comparison_results']
        if r.get('outcome_ask_estimate', {}).get('estimate_ist') is not None
    ]
    assert len(quoted) == 1
    assert quoted[0]['contract']['properties']['1855'] == 254
    assert quoted[0]['outcome_ask_estimate']['sellers'] == 3
    text = '\n'.join(price_lines(report))
    assert 'If upgrading to Giant Conch rolls 254 defense' in text
    assert '210-254' in text
    assert 'Ko' in text
    assert 'Lem' in text
    assert 'Perfect Diamond' in text
    assert result.contract.properties['1855'] == 177
    assert all(r.contract['base_code'] == result.upgrades[0].target_code for r in requests)
    assert all(r.contract['properties']['427'] == 19 for r in requests)


def test_guardian_upgrade_does_not_quote_unreachable_defense_or_unknown_sockets():
    extraction = replay('guardian_angel')['extraction']
    assert not armor_requests(assess_result(extraction, profiles=[]))
    extraction['item'].update(sockets=0, socket_contents='empty', filled_sockets=0, empty_sockets=0, socket_items=[])
    result = assess_result(extraction, profiles=[])
    requests = armor_requests(result)
    assert len(requests) == 110
    assert {r.contract['properties']['1855'] for r in requests} == {base * 287 // 100 for base in range(421, 531)}
    assert all(r.contract['properties']['1855'] != 1209 for r in requests)
    assert result.contract.properties['1855'] == 789
