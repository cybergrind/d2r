"""Reviewed pricing dispositions for native individual scrolls, one unit at a time."""

import argparse
import json
from collections import Counter
from datetime import UTC, date, datetime

from pricing.knowledge.assessment.handlers.supply import SupplyHandler
from pricing.knowledge.assessment.maintenance.fixed_market_review import MARKET, FixedMarketReview
from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.assessment.policies.supplies import SCROLLS, definitions
from pricing.knowledge.refresh import atomic_json


OUTPUT = 'pricing/data/appraisal-scroll-market-review.json'
INPUTS = (
    MARKET,
    'pricing/data/appraisal-market-manifest.json',
    'pricing/knowledge/cache_dates.py',
    'pricing/data/wp-f-ladder.json',
    'third-parties/d2data/json/misc.json',
    'inventory_tracking/items/data/item_metadata.json',
    'pricing/knowledge/assessment/policies/consumables.py',
    'pricing/knowledge/assessment/policies/supplies.py',
    'pricing/knowledge/market_supplies.py',
    'pricing/knowledge/market_fixed_facets.py',
    'pricing/knowledge/market.py',
    'pricing/knowledge/market_mechanics.py',
    'pricing/knowledge/assessment/handlers/supply.py',
    'pricing/knowledge/assessment/comparables.py',
    'pricing/knowledge/assessment/adapters/capture.py',
    'pricing/knowledge/assessment/maintenance/scroll_market_review.py',
    'pricing/knowledge/assessment/maintenance/fixed_market_review.py',
)

REVIEW = FixedMarketReview(
    scope='single_ordinary_native_scroll',
    label='Scroll',
    description='ordinary native scroll',
    artifact='scroll_market_reviews',
    family='supply',
    limit='One individual ordinary scroll; excludes tomes, bulk lots and quest/unused scrolls.',
    inputs=INPUTS,
    definitions=lambda: {code: row for code, row in definitions().items() if code in SCROLLS},
    handler=SupplyHandler,
)
audit_scrolls = REVIEW.audit
build_review = REVIEW.build
apply_scroll_market_reviews = REVIEW.apply


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', type=date.fromisoformat, default=datetime.now(UTC).date())
    args = parser.parse_args()
    review = build_review(ROOT, args.as_of)
    atomic_json(ROOT / OUTPUT, review)
    print(json.dumps(dict(Counter(r['price'].get('unavailable_reason', 'estimate') for r in review['rows']))))


if __name__ == '__main__':
    main()
