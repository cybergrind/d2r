"""A reviewed single-scroll price cannot close native stack pricing."""

from datetime import date

from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.assessment.maintenance.scroll_market_review import apply_scroll_market_reviews, build_review


def test_scroll_review_applies_only_to_two_individual_native_scrolls():
    review = build_review(ROOT, date(2026, 9, 28))
    assert {r['name'] for r in review['rows']} == {'Scroll of Identify', 'Scroll of Town Portal'}
    assert all(r['contract']['policy'] == 'supply' for r in review['rows'])
    rows = [
        {
            'kind': 'identity',
            'name': name,
            'category': 'misc',
            'catalog_ids': [code],
            'dimensions': {'discovery': {'state': 'reviewed'}, 'market': {'state': 'pending'}},
        }
        for code, name in [('isc', 'Scroll of Identify'), ('ibk', 'Tome of Identify'), ('0sc', 'Scroll of Knowledge')]
    ]
    apply_scroll_market_reviews(rows, review, ROOT)
    assert rows[0]['dimensions']['market']['state'] == 'reviewed'
    assert rows[1]['dimensions']['market']['state'] == 'pending'
    assert rows[2]['dimensions']['market']['state'] == 'pending'
