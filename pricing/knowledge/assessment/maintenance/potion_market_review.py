"""Reviewed pricing dispositions for native ordinary potions, one unit at a time."""

import argparse
import json
from collections import Counter
from datetime import UTC, date, datetime

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.handlers.consumable import ConsumableHandler
from pricing.knowledge.assessment.maintenance.fixed_market_review import MARKET, FixedMarketReview
from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.assessment.policies.consumables import SOURCE, definitions
from pricing.knowledge.refresh import atomic_json


OUTPUT = 'pricing/data/appraisal-potion-market-review.json'
INPUTS = (
    MARKET,
    'pricing/data/appraisal-market-manifest.json',
    'pricing/knowledge/cache_dates.py',
    'pricing/data/wp-f-ladder.json',
    'third-parties/d2data/json/misc.json',
    'inventory_tracking/items/data/item_metadata.json',
    'pricing/knowledge/assessment/policies/consumables.py',
    'pricing/knowledge/market_consumables.py',
    'pricing/knowledge/market_fixed_facets.py',
    'pricing/knowledge/market.py',
    'pricing/knowledge/market_mechanics.py',
    'pricing/knowledge/assessment/handlers/consumable.py',
    'pricing/knowledge/assessment/comparables.py',
    'pricing/knowledge/assessment/adapters/capture.py',
    'pricing/knowledge/assessment/maintenance/potion_market_review.py',
    'pricing/knowledge/assessment/maintenance/fixed_market_review.py',
)

REVIEW = FixedMarketReview(
    scope='single_ordinary_native_potion',
    label='Potion',
    description='ordinary native potion',
    artifact='potion_market_reviews',
    family='consumable',
    limit='One ordinary native potion; excludes bulk lots, quest potions and throwing weapons.',
    inputs=INPUTS,
    definitions=lambda: definitions(read_artifact(SOURCE)),
    handler=ConsumableHandler,
)
audit_potions = REVIEW.audit
build_review = REVIEW.build
apply_potion_market_reviews = REVIEW.apply


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', type=date.fromisoformat, default=datetime.now(UTC).date())
    args = parser.parse_args()
    review = build_review(ROOT, args.as_of)
    atomic_json(ROOT / OUTPUT, review)
    print(json.dumps(dict(Counter(r['price'].get('unavailable_reason', 'estimate') for r in review['rows']))))


if __name__ == '__main__':
    main()
