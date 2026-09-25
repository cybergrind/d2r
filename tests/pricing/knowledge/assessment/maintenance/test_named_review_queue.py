from datetime import date

from pricing.knowledge.assessment.maintenance.coverage import audit_named
from pricing.knowledge.assessment.maintenance.market_readiness import audit
from tests.pricing.knowledge.assessment.maintenance.test_market_readiness import row


def test_cached_listing_gaps_are_joined_to_build_demand_without_promoting_tiers(tmp_path):
    definitions = {('unique', name): {'base_codes': []} for name in ('Vampire Gaze', 'No cache')}
    market = audit(
        [row(ethereal=None, sockets=None), row(listing_id='foreign', scope_status='rejected')], today=date(2026, 9, 25)
    )
    demand = [
        {
            'category': 'unique',
            'name': 'Vampire Gaze',
            'id': 'merc',
            'side': 'mercenary',
            'details': {'recommended': True, 'resolution_status': 'resolved'},
        }
    ]
    report = audit_named(definitions, {}, {}, tmp_path, demand=demand, market_readiness=market)
    items = {r['name']: r for r in report['rows']}
    assert items['Vampire Gaze']['market']['scoped_observations'] == 1
    assert items['Vampire Gaze']['market']['gaps'] == {'ethereal': 1, 'sockets': 1}
    assert items['Vampire Gaze']['tier'] is None
    assert items['No cache']['market']['scoped_observations'] == 0
    assert report['market_as_of'] == '2026-09-25'
    assert report['review_queue'][0]['name'] == 'Vampire Gaze'
    assert report['review_queue'][0]['next_action'] == 'resolve_listing_facets'
    assert report['review_queue'][1]['next_action'] == 'find_scoped_evidence'


def test_structurally_ready_rows_request_comparison_review_not_a_price_or_tier(tmp_path):
    definitions = {('unique', 'Vampire Gaze'): {'base_codes': []}}
    market = audit([row()], today=date(2026, 9, 25))
    report = audit_named(definitions, {}, {}, tmp_path, market_readiness=market)
    assert report['review_queue'][0]['next_action'] == 'review_exact_comparisons'
    assert report['rows'][0]['tier'] is None
    assert report['identity_policy_complete'] is False
    # Omitting a market audit is distinct from proving an empty cache.
    unaudited = audit_named(definitions, {}, {}, tmp_path)
    assert unaudited['rows'][0]['market'] is None
    assert unaudited['review_queue'][0]['next_action'] == 'audit_cached_market'
