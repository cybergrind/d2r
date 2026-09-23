"""Offline market normalization and conservative comparable selection."""

import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path


VERSION = 'reign of the warlock'


def scope_status(properties):
    """Return verified, rejected, or unknown; absent scope is never accepted."""
    if '800' in properties and properties['800'] is not False:
        return 'rejected'
    expected = {'799': 'softcore', '800': False, '798': 'PC'}
    if any(key in properties and properties[key] != value for key, value in expected.items()):
        return 'rejected'
    versions = {part.strip().lower() for part in str(properties.get('1854', '')).split(',')}
    if VERSION not in versions:
        known = {'classic', 'classic (base game)', 'lord of destruction'}
        return 'rejected' if versions & known else 'unknown'
    return 'verified' if all(key in properties for key in expected) else 'unknown'


def valid_positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def convert_groups(prices, currencies):
    groups = {}
    unknown = set()
    for price in prices or []:
        group = groups.setdefault(str(price.get('group') or 0), {'total': 0, 'complete': True})
        name = price.get('name', '')
        key = name.lower().removesuffix(' rune')
        value = currencies.get(key)
        quantity = price.get('quantity', 1)
        if not valid_positive(value) or not valid_positive(quantity):
            group['complete'] = False
            unknown.add(name)
        else:
            group['total'] += value * quantity
    complete = [group['total'] for group in groups.values() if group['complete']]
    return (min(complete) if complete else None), {'groups': groups, 'unknown_currencies': sorted(unknown)}


def property_values(raw):
    """Traderie array-valued metadata is serialized in its string field."""
    return {str(p['property_id']): p.get(p['type'] if p['type'] in ('number', 'bool') else 'string') for p in raw}


def socket_contents(properties):
    if '934' not in properties or properties['934'] is None:
        return 'unknown'
    return 'empty' if properties['934'] in ('', []) else 'filled'


def normalize_listing(listing, *, name, category, source, observed_at=None, currencies=None):
    """Preserve source properties and currency terms; never infer a missing fetch date."""
    properties = property_values(listing.get('properties') or [])
    ask, conversion = convert_groups(listing.get('prices'), currencies or {})
    amount = listing.get('amount')
    unit = 'stack_total' if category in ('runes', 'gems') else 'single_item' if amount == 1 else 'ambiguous'
    if unit == 'stack_total':
        if valid_positive(amount) and ask is not None:
            ask /= amount
        else:
            ask = None
    identity = f'{source}:{listing.get("id")}:{observed_at}'
    row = {
        'id': hashlib.sha256(identity.encode()).hexdigest()[:24],
        'kind': 'market',
        'name': name,
        'category': category,
        'catalog_id': str(listing.get('item_id', '')),
        'evidence_kind': 'ask',
        'listing_id': listing.get('id'),
        'seller_id': listing.get('seller_id'),
        'source': source,
        'observed_at': observed_at,
        'observation_date_basis': 'fetch' if observed_at else 'unknown',
        'listing_updated_at': listing.get('updated_at'),
        'scope_status': scope_status(properties),
        'properties': properties,
        'socket_contents': socket_contents(properties),
        'raw_properties': listing.get('properties') or [],
        'amount': amount,
        'unit_policy': unit,
        'prices': listing.get('prices') or [],
        'ask_ist': ask,
        'conversion': conversion,
    }
    for field, key in [('rarity', '797'), ('sockets', '402'), ('ethereal', '738')]:
        value = properties.get(key)
        valid = (
            (field == 'ethereal' and type(value) is bool)
            or (field == 'sockets' and type(value) in (int, float) and value in range(7))
            or (field == 'rarity' and isinstance(value, str))
        )
        if valid:
            row[field] = value
    return row


def matches(row, predicates):
    for key, expected in (predicates or {}).items():
        if key == 'properties':
            if not matches(row, {f'properties.{k}': v for k, v in expected.items()}):
                return False
            continue
        value = row.get('properties', {}).get(key[11:]) if key.startswith('properties.') else row.get(key)
        if value is None or value != expected:
            return False
    return True


def summarize(rows, predicates=None):
    """Watch bands without predicates; exact bands only for explicitly requested facets."""
    selected = [r for r in rows if r.get('scope_status') == 'verified' and matches(r, predicates)]
    votes = {}
    observations = 0
    for row in selected:
        if row.get('unit_policy') == 'ambiguous' or not row.get('seller_id') or not valid_positive(row.get('ask_ist')):
            continue
        observations += 1
        seller = row['seller_id']
        votes[seller] = min(votes.get(seller, float('inf')), row['ask_ist'])
    values = sorted(votes.values())
    return {
        'band_kind': 'facet_matched' if predicates else 'name_level_watch',
        'priced_sellers': len(votes),
        'priced_observations': observations,
        'thin': len(votes) < 5,
        'min_ist': min(values) if values else None,
        'median_ist': statistics.median(values) if values else None,
        'max_ist': max(values) if values else None,
        'observed_dates': sorted({r['observed_at'] for r in selected if r.get('observed_at')}),
        'unknown_observation_date': any(not r.get('observed_at') for r in selected),
        'representatives': [
            {
                k: r.get(k)
                for k in (
                    'name',
                    'listing_id',
                    'seller_id',
                    'properties',
                    'amount',
                    'ask_ist',
                    'observed_at',
                    'listing_updated_at',
                    'source',
                    'conversion',
                )
            }
            for r in [
                r
                for r in selected
                if r.get('unit_policy') != 'ambiguous' and r.get('seller_id') and valid_positive(r.get('ask_ist'))
            ][:3]
        ],
    }


def import_cache(root, catalog=None):
    """Import historical raw cache, with unknown fetch dates and strict scope quarantine."""
    root = Path(root)
    ladder_path = root / 'pricing/data/wp-f-ladder.json'
    ladder = json.loads(ladder_path.read_text())
    currencies = {k.lower(): v['ist'] for k, v in ladder.items() if isinstance(v, dict) and 'ist' in v}
    lookup = {str(i['id']): i for i in catalog or []}
    for filename in ('wp-b-prices.json', 'wp-i-uniques-misc.json'):
        for row in json.loads((root / 'pricing/data' / filename).read_text()).values():
            if isinstance(row, dict) and row.get('name') and (row.get('item_id') or row.get('traderie_id')):
                iid = str(row.get('item_id') or row.get('traderie_id'))
                lookup.setdefault(iid, {'name': row['name'], 'type': row.get('type', 'base')})
    rows = []
    seen = set()
    manifest = {
        'schema_version': 1,
        'files': [],
        'currency_snapshot': str(ladder_path.relative_to(root)),
        'currency_snapshot_date': ladder['_meta']['date'],
    }
    for path in sorted((root / 'pricing/raw/traderie').glob('*.json')):
        try:
            data = json.loads(path.read_text())
        except (ValueError, OSError) as error:
            manifest['files'].append({'path': str(path.relative_to(root)), 'error': str(error)})
            continue
        listings = data if isinstance(data, list) else data.get('listings', [])
        file_info = {
            'path': str(path.relative_to(root)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'observed_at': None,
            'listing_count': len(listings),
        }
        manifest['files'].append(file_info)
        for listing in listings:
            if not isinstance(listing, dict) or 'properties' not in listing:
                continue
            identity = (listing.get('id'), listing.get('updated_at'))
            if identity in seen:
                continue
            seen.add(identity)
            iid = str(listing.get('item_id', ''))
            item = lookup.get(iid, {})
            row = normalize_listing(
                listing,
                name=item.get('name', f'Unresolved catalog {iid}'),
                category=item.get('type', 'unknown'),
                source=file_info['path'],
                currencies=currencies,
            )
            row['conversion'].update(
                snapshot_id=manifest['currency_snapshot'], snapshot_date=manifest['currency_snapshot_date']
            )
            rows.append(row)
    for path in sorted((root / 'pricing/raw/traderie').glob('appraisal-research-*/representative-probes.json')):
        for probe in json.loads(path.read_text()):
            for listing in probe.get('listings', []):
                row = normalize_listing(
                    listing,
                    name=probe['name'],
                    category=probe['type'],
                    source=probe['source'],
                    observed_at=probe['fetched_at'],
                    currencies=currencies,
                )
                row['observation_date_precision'] = 'day'
                row['conversion'].update(
                    snapshot_id=manifest['currency_snapshot'], snapshot_date=manifest['currency_snapshot_date']
                )
                rows.append(row)
    manifest['scope_counts'] = dict(Counter(r['scope_status'] for r in rows))
    manifest['observations'] = len(rows)
    return rows, manifest
