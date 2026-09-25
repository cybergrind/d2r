"""Named-tier fallback from already published exact current-item ask bands.

Thresholds follow WP-I /_meta/tiers (2026-09-18), Ist=1. HR and High merge into
high; the Floor band maps to the requested trash trade tier, not a discard rule.
This policy never relaxes comparisons or creates a numerical price estimate.
"""

from pricing.knowledge.assessment.comparables import MIN_SELLERS
from pricing.knowledge.assessment.domain.comparison_results import ComparisonResult
from pricing.knowledge.market import valid_positive


TIERS = ('trash', 'low', 'med', 'high')
BOUNDARIES = (0.2, 0.8, 2.5)
SCOPE = 'Softcore / Non-Ladder / PC / Reign of the Warlock'


def resolve_market_tier(facts, reviewed, current):
    if isinstance(current, ComparisonResult):
        current = {
            name: getattr(current, name)
            for name in ('state', 'request_ids', 'contract', 'segment_id', 'price_estimate')
        }
    if reviewed.get('status') != 'pending_review' or facts.rarity not in ('unique', 'set'):
        return reviewed
    if not current or current.get('state') != 'observed' or 'current' not in current.get('request_ids', ()):
        return reviewed
    contract = current.get('contract') or {}
    estimate = current.get('price_estimate') or {}
    if (
        contract.get('policy') != 'named'
        or contract.get('name') != facts.name
        or contract.get('rarity') != facts.rarity
        or current.get('segment_id') != 'exact_current_variant'
        or estimate.get('basis') != 'classified_exact_variant_asks'
        or estimate.get('scope') != SCOPE
        or type(estimate.get('sellers')) is not int
        or estimate['sellers'] < MIN_SELLERS
    ):
        return reviewed
    low, median, high = (estimate.get(key) for key in ('low_ist', 'estimate_ist', 'high_ist'))
    dates = estimate.get('dates')
    if (
        not all(valid_positive(value) for value in (low, median, high))
        or not low <= median <= high
        or not dates
        or not all(isinstance(value, str) and value for value in dates)
    ):
        return reviewed
    first = sum(low >= boundary for boundary in BOUNDARIES)
    last = sum(high >= boundary for boundary in BOUNDARIES)
    possible = list(TIERS[first : last + 1])
    return {
        'status': 'market_supported' if len(possible) == 1 else 'conditional',
        'tier': possible[0] if len(possible) == 1 else None,
        'possible_tiers': possible,
        'reasons': [],
        'basis': 'Tier of the verified exact current-item ask band; leveling and build usefulness are independent.',
        'ask_band_ist': {'low': low, 'median': median, 'high': high},
        'sellers': estimate['sellers'],
        'source': {
            'kind': 'exact_comparable_asks',
            'request_id': 'current',
            'date': max(dates),
            'as_of': estimate.get('publication_policy', {}).get('as_of'),
            'threshold_source': 'pricing/data/wp-i-uniques-misc.json#/_meta/tiers',
            'threshold_date': '2026-09-18',
        },
    }
