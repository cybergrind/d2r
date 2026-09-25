from datetime import date

from inventory_tracking.appraisal.sections import price_lines
from pricing.knowledge.assessment.engine import assess_result
from pricing.knowledge.assessment.maintenance.replay import replay
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.test_pipeline_context import database


def test_saved_unique_weapon_upgrade_compares_target_base_only(tmp_path):
    extraction = replay('hellplague')['extraction']
    result = assess_result(extraction, profiles=[])
    upgrades = [r for r in result.comparison_requests if r.preparation and r.preparation['action'] == 'upgrade_weapon']
    assert len(upgrades) == 2
    for request, path in zip(upgrades, result.upgrades, strict=True):
        assert request.contract['base_code'] == path.target_code
        assert request.contract['name'] == 'Hellplague'
        assert request.contract['properties'] == result.contract.properties
        assert request.contract['ethereal'] == result.contract.ethereal
        assert request.contract['socket_contents'] == result.contract.socket_contents
        assert len(request.preparation['steps']) == len(path.steps)
    request = upgrades[-1]
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
    report = retrieve_draft(extraction, database(tmp_path, rows), as_of=date(2026, 9, 25))
    assert report['price_estimate']['estimate_ist'] is None
    quoted = [
        r
        for r in report['assessment']['comparison_results']
        if r.get('outcome_ask_estimate', {}).get('estimate_ist') is not None
    ]
    assert len(quoted) == 1
    assert quoted[0]['contract']['base_code'] == result.upgrades[-1].target_code
    text = '\n'.join(price_lines(report))
    assert f'After upgrading to {result.upgrades[-1].target_name}' in text
    assert '2 x Perfect Emerald' in text
    assert 'requirements' in text
    assert result.facts.base_code != request.contract['base_code']


def test_incomplete_weapon_and_armor_upgrades_have_no_outcome_quote():
    for stem in ('dread_edge', 'guardian_angel'):
        extraction = replay(stem)['extraction']
        if stem == 'dread_edge':
            extraction['decoded_stats'] = [
                row for row in extraction['decoded_stats'] if row.get('memory_stat', {}).get('id') != 56
            ]
        result = assess_result(extraction, profiles=[])
        assert result.upgrades
        assert not any(
            r.preparation and r.preparation['action'] == 'upgrade_weapon' for r in result.comparison_requests
        )


def test_rare_weapon_target_uses_upgraded_base_name_and_rare_recipe():
    from dataclasses import replace

    from pricing.knowledge.assessment.handlers import HANDLERS
    from pricing.knowledge.assessment.mechanics.upgrade_comparisons import upgrade_outcome_requests
    from pricing.knowledge.assessment.mechanics.upgrades import upgrade_paths
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    item = replace(
        facts('Cinquedeas', 'rare', 'Dread Edge'),
        ethereal=True,
        stats={f'{stat}:0': {'status': 'decoded', 'value': 80} for stat in (17, 18)},
        properties={'510': 80},
    )
    contract, gaps = HANDLERS['affixed'].contract(item, 'weapon')
    assert contract is not None, gaps
    (request,) = upgrade_outcome_requests(item, contract, upgrade_paths(item))
    assert request.contract['name'] == 'Fanged Knife'
    assert request.contract['rarity'] == 'rare'
    assert request.contract['ethereal'] is True
    assert request.preparation['steps'][0]['source'].endswith('#135')
    assert request.contract['properties'] == contract.properties


def test_set_weapon_upgrade_uses_set_recipe_and_preserves_identity():
    from dataclasses import replace

    from pricing.knowledge.assessment.handlers import HANDLERS
    from pricing.knowledge.assessment.mechanics.upgrade_comparisons import upgrade_outcome_requests
    from pricing.knowledge.assessment.mechanics.upgrades import upgrade_paths
    from tests.pricing.knowledge.assessment.test_socket_survival_comparisons import socketed_item

    item = replace(
        socketed_item('Military Pick', 'set', "Tancred's Crowbill", [], {}), socket_contents='empty', gaps=()
    )
    contract, gaps = HANDLERS['named'].contract(item, 'weapon')
    assert contract is not None, gaps
    requests = upgrade_outcome_requests(item, contract, upgrade_paths(item))
    assert len(requests) == 2
    assert requests[0].preparation['steps'][0]['source'].endswith('#151')
    assert requests[1].preparation['steps'][1]['source'].endswith('#153')
    assert all(r.contract['name'] == "Tancred's Crowbill" for r in requests)


def test_saved_dread_edge_now_supports_exact_weapon_upgrade_comparison():
    result = assess_result(replay('dread_edge')['extraction'], profiles=[])
    requests = [r for r in result.comparison_requests if r.preparation and r.preparation['action'] == 'upgrade_weapon']
    assert len(requests) == 1
    assert requests[0].contract['name'] == 'Fanged Knife'
    assert requests[0].contract['properties']['535'] == 0.5
    assert requests[0].contract['properties']['536'] == 16.5
