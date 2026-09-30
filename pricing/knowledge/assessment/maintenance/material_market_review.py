"""Reproducible single-item rune/gem pricing dispositions, never inferred fetch dates."""

import argparse
import json
from collections import Counter
from datetime import UTC, date, datetime

from pricing.knowledge.assessment.handlers.socket_material import SocketMaterialHandler
from pricing.knowledge.assessment.maintenance.fixed_market_review import MARKET, FixedMarketReview
from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.refresh import atomic_json
from pricing.knowledge.socket_materials import definitions


OUTPUT = 'pricing/data/appraisal-material-market-review.json'
SCOPE = 'single_loose_rune_or_gem'
INPUTS = (
    MARKET,
    'pricing/knowledge/assessment/maintenance/fixed_market_review.py',
    'pricing/data/appraisal-market-manifest.json',
    'pricing/knowledge/cache_dates.py',
    'pricing/data/wp-f-ladder.json',
    'third-parties/d2data/json/misc.json',
    'inventory_tracking/items/data/item_metadata.json',
    'pricing/knowledge/socket_materials.py',
    'pricing/knowledge/market_socket_materials.py',
    'pricing/knowledge/market_fixed_facets.py',
    'pricing/knowledge/market.py',
    'pricing/knowledge/market_mechanics.py',
    'pricing/knowledge/assessment/handlers/socket_material.py',
    'pricing/knowledge/assessment/comparables.py',
    'pricing/knowledge/assessment/adapters/capture.py',
    'pricing/knowledge/assessment/maintenance/material_market_review.py',
)


REVIEW = FixedMarketReview(
    scope=SCOPE,
    label='Material',
    description='loose native material',
    artifact='material_market_reviews',
    family='socket_material',
    limit='One loose native rune/gem, not a bulk lot, equipped contribution or completed recipe.',
    inputs=INPUTS,
    definitions=definitions,
    handler=SocketMaterialHandler,
)
template_contract = REVIEW.template_contract
audit_materials = REVIEW.audit
review_inputs = REVIEW.review_inputs
build_review = REVIEW.build
apply_material_market_reviews = REVIEW.apply


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', type=date.fromisoformat, default=datetime.now(UTC).date())
    args = parser.parse_args()
    review = build_review(ROOT, args.as_of)
    atomic_json(ROOT / OUTPUT, review)
    print(json.dumps(dict(Counter(r['price'].get('unavailable_reason', 'estimate') for r in review['rows']))))


if __name__ == '__main__':
    main()
