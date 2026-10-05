"""Read explicitly scoped buyer observations without admitting them as asks."""

import json
from collections import defaultdict

from pricing.knowledge.market import normalize_listing, scope_status
from pricing.triage.bands import instant
from pricing.triage.listing_defaults import normalize


def summarize(documents, catalog, cohort_key):
    groups = defaultdict(lambda: {'buyers': set(), 'listings': set(), 'dates': set(), 'sources': set()})
    unavailable, observed = [], []
    for source, document in documents:
        response = document.get('response', {})
        rows = response.get('listings') if isinstance(response, dict) else None
        date = document.get('_pulled_at')
        if not isinstance(rows, list) or instant(date) is None:
            unavailable.append(source)
            continue
        observed.append(source)
        for raw in rows:
            item = catalog.get(str(raw.get('item_id')))
            if (
                raw.get('selling') is not False
                or raw.get('active') is not True
                or raw.get('completed') is not False
                or not raw.get('id')
                or not raw.get('seller_id')
                or not item
            ):
                continue
            row = normalize(
                normalize_listing(
                    raw,
                    name=item['name'],
                    category=item['type'],
                    source=source,
                    observed_at=date,
                    currencies={},
                )
            )
            if scope_status(row.get('properties', {})) != 'verified':
                continue
            # The offered payment is not a seller's asking price. Cohort routing
            # needs item facets only and must never consume it as price evidence.
            row = row | {'evidence_kind': 'buy', 'ask_ist': None}
            group = groups[cohort_key(row)]
            group['buyers'].add(str(raw['seller_id']))
            group['listings'].add(str(raw['id']))
            group['dates'].add(date)
            group['sources'].add(source)
    return {
        'cohorts': {
            key: {
                'buyers': len(value['buyers']),
                'listings': len(value['listings']),
                'observed_at': max(value['dates']),
                'sources': sorted(value['sources']),
            }
            for key, value in sorted(groups.items())
        },
        'observed_sources': observed,
        'unavailable_sources': unavailable,
        'interpretation': 'Explicit scoped buy listings; missing cohorts are unmeasured, not zero demand.',
    }


def cached_report(root, catalog, cohort_key):
    documents = [
        (str(path.relative_to(root)), json.loads(path.read_text()))
        for path in sorted((root / 'pricing/raw/traderie').glob('buy-side-probe-*.json'))
    ]
    return summarize(documents, catalog, cohort_key)
