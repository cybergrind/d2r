"""Source-bound single recipe-material pricing dispositions from the offline cache."""

import argparse
import json
from collections import Counter
from datetime import UTC, date, datetime

from pricing.knowledge.assessment.handlers.quest_material import QuestMaterialHandler
from pricing.knowledge.assessment.maintenance.fixed_market_review import MARKET, FixedMarketReview
from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.assessment.policies.quest_materials import TRADEABLE, definitions
from pricing.knowledge.refresh import atomic_json


OUTPUT = 'pricing/data/appraisal-quest-material-market-review.json'
INPUTS = (
    MARKET,
    'pricing/data/appraisal-market-manifest.json',
    'pricing/data/wp-f-ladder.json',
    'third-parties/d2data/json/misc.json',
    'third-parties/d2data/json/cubemain.json',
    'third-parties/d2data/json/allstrings-eng.json',
    'inventory_tracking/items/data/item_metadata.json',
    'pricing/knowledge/assessment/policies/quest_materials.py',
    'pricing/knowledge/assessment/handlers/quest_material.py',
    'pricing/knowledge/market_quest_materials.py',
    'pricing/knowledge/market_fixed_facets.py',
    'pricing/knowledge/market.py',
    'pricing/knowledge/market_mechanics.py',
    'pricing/knowledge/cache_dates.py',
    'pricing/knowledge/assessment/comparables.py',
    'pricing/knowledge/assessment/adapters/capture.py',
    'pricing/knowledge/assessment/maintenance/fixed_market_review.py',
    'pricing/knowledge/assessment/maintenance/quest_material_market_review.py',
)
REVIEW = FixedMarketReview(
    scope='single_native_recipe_material',
    label='Recipe material',
    description='native recipe material',
    artifact='quest_material_market_reviews',
    family='quest_material',
    limit='One reviewed material; excludes lots, key/statue/shard sets, portals and character quest utility.',
    inputs=INPUTS,
    definitions=lambda: {code: row for code, row in definitions().items() if code in TRADEABLE},
    handler=QuestMaterialHandler,
)
build_review = REVIEW.build
apply_quest_material_market_reviews = REVIEW.apply


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', type=date.fromisoformat, default=datetime.now(UTC).date())
    args = parser.parse_args()
    review = build_review(ROOT, args.as_of)
    atomic_json(ROOT / OUTPUT, review)
    print(json.dumps(dict(Counter(r['price'].get('unavailable_reason', 'estimate') for r in review['rows']))))


if __name__ == '__main__':
    main()
