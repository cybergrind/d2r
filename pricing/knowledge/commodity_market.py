"""Rebuild authorized commodity pulls offline, independently of equipment research."""

import hashlib
import json
from pathlib import Path

from pricing.knowledge.market import normalize_listing


ROOT = Path(__file__).resolve().parents[2]


def build(root=ROOT):
    inputs = {}
    sources = []
    for name in ('wp-f-ladder.json', 'appraisal-traderie-catalog.json'):
        path = root / 'pricing/data' / name
        raw = path.read_bytes()
        source = str(path.relative_to(root))
        sources.append({'id': source, 'path': source, 'sha256': hashlib.sha256(raw).hexdigest()})
        inputs[name] = json.loads(raw)
    ladder = inputs['wp-f-ladder.json']
    catalog = {str(r['id']): r for r in inputs['appraisal-traderie-catalog.json']['items']}
    currencies = {k.lower(): v['ist'] for k, v in ladder.items() if isinstance(v, dict) and 'ist' in v}
    rows = []
    for path in sorted((root / 'pricing/raw/traderie').glob('appraisal-commodities-*/*-page*.json')):
        raw = path.read_bytes()
        cached = json.loads(raw)
        source = {'path': str(path.relative_to(root)), 'sha256': hashlib.sha256(raw).hexdigest()}
        sources.append({'id': source['path'], **source})
        for listing in cached['listings']:
            row = normalize_listing(
                listing,
                name=cached['name'],
                category=cached['type'],
                source=source['path'],
                observed_at=cached['fetched_at'],
                currencies=currencies,
            )
            identity = catalog.get(str(listing.get('item_id')), {})
            if identity.get('name') != cached['name'] or identity.get('type') != cached['type']:
                row['evidence_kind'] = 'unverified_identity'
            elif (
                listing.get('active') is not True
                or listing.get('selling') is not True
                or listing.get('completed') is not False
            ):
                row['evidence_kind'] = 'unverified_listing'
            row['observation_date_source'] = {**source, 'field': '/fetched_at'}
            row['observation_date_basis'] = 'documented_collection'
            row['conversion'].update(
                snapshot_id='pricing/data/wp-f-ladder.json', snapshot_date=ladder.get('_meta', {}).get('date')
            )
            rows.append(row)
    return {'schema_version': 1, 'sources': sources, 'rows': rows}


if __name__ == '__main__':
    from pricing.knowledge.refresh import atomic_json

    document = build()
    atomic_json(ROOT / 'pricing/data/appraisal-commodity-market.json', document)
    print(json.dumps({'observations': len(document['rows']), 'sources': len(document['sources'])}))
