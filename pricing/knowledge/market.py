"""Offline market normalization and conservative comparable selection."""

import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

from pricing.knowledge.assessment.observations import superseded_rows
from pricing.knowledge.cache_dates import collection_day_evidence
from pricing.knowledge.documented_cache_dates import documented_day, load_reviews
from pricing.knowledge.market_mechanics import apply_mechanics
from pricing.knowledge.market_named_aliases import canonicalize_named_catalog


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
    # In-stock amount is available inventory, not a verified priced lot.
    # Traderie getting-started/seller: offers may request a subset of stock.
    if listing.get('stock') is True and amount != 1:
        unit, ask = 'ambiguous', None
    identity = f'{source}:{listing.get("id")}:{observed_at}'
    row = {
        'id': hashlib.sha256(identity.encode()).hexdigest()[:24],
        'kind': 'market',
        'name': name,
        'category': category,
        'catalog_id': str(listing.get('item_id', '')),
        'evidence_kind': (
            'inactive_listing'
            if listing.get('active') is False or listing.get('completed') is True
            else 'buy_offer'
            if listing.get('selling') is False
            else 'ask'
        ),
        'listing_status': {key: listing.get(key) for key in ('active', 'selling', 'completed')},
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
        'listing_stock': listing.get('stock'),
        'unit_policy': unit,
        'prices': listing.get('prices') or [],
        'ask_ist': ask,
        'conversion': conversion,
    }
    normalize_facets(row)
    return row


def normalize_facets(row):
    """Rebuild variant facts from source properties and verified catalog identity."""
    catalog_name = row.pop('catalog_name', None)
    if catalog_name:
        row['name'] = catalog_name
    for field in (
        'rarity',
        'sockets',
        'ethereal',
        'rarity_basis',
        'base_code',
        'base_upgrade',
        'base_rarity',
        'base_selector_properties',
        'socket_contents_basis',
        'facet_basis',
        'mechanics_conflicts',
    ):
        row.pop(field, None)
    canonicalize_named_catalog(row)
    properties, category = row['properties'], row['category']
    row['socket_contents'] = socket_contents(properties)
    for field, key in [('rarity', '797'), ('sockets', '402'), ('ethereal', '738')]:
        value = properties.get(key)
        valid = (
            (field == 'ethereal' and type(value) is bool)
            or (field == 'sockets' and type(value) in (int, float) and value in range(7))
            or (field == 'rarity' and isinstance(value, str))
        )
        if valid:
            row[field] = value
    catalog_quality = {'uniques': 'unique', 'unique': 'unique', 'sets': 'set', 'set': 'set'}.get(category)
    if 'rarity' not in row and catalog_quality:
        row['rarity'] = catalog_quality
        row['rarity_basis'] = 'named_catalog_category'
    apply_mechanics(row)
    if category == 'runewords':
        from pricing.knowledge.runeword_market import normalize_runeword

        normalize_runeword(row)


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
    rows = list(rows)
    superseded = superseded_rows(rows)
    selected = [
        r
        for index, r in enumerate(rows)
        if index not in superseded
        and r.get('evidence_kind') == 'ask'
        and r.get('scope_status') == 'verified'
        and matches(r, predicates)
    ]
    votes = {}
    representatives = {}
    observations = 0
    for row in selected:
        if row.get('unit_policy') == 'ambiguous' or not row.get('seller_id') or not valid_positive(row.get('ask_ist')):
            continue
        observations += 1
        seller = row['seller_id']
        votes[seller] = min(votes.get(seller, float('inf')), row['ask_ist'])
        key = (
            row['ask_ist'],
            str(row.get('listing_id', '')),
            str(row.get('observed_at', '')),
            str(row.get('source', '')),
        )
        if seller not in representatives or key < representatives[seller][0]:
            representatives[seller] = (key, row)
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
            for _, r in sorted(representatives.values(), key=lambda pair: (pair[0], str(pair[1]['seller_id'])))[:3]
        ],
    }


def import_cache(root, catalog=None):
    """Import cached evidence, preserving explicit collection days and strict scope."""
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
    date_reviews, date_registry = load_reviews(root)
    manifest = {
        'schema_version': 1,
        'files': [],
        'currency_snapshot': str(ladder_path.relative_to(root)),
        'currency_snapshot_date': ladder['_meta']['date'],
    }
    for path in sorted((root / 'pricing/raw/traderie').glob('*.json')):
        try:
            raw = path.read_bytes()
            data = json.loads(raw)
        except (ValueError, OSError) as error:
            manifest['files'].append({'path': str(path.relative_to(root)), 'error': str(error)})
            continue
        listings = data if isinstance(data, list) else data.get('listings', [])
        observed_at, date_error, date_field = collection_day_evidence(data)
        file_info = {
            'path': str(path.relative_to(root)),
            'sha256': hashlib.sha256(raw).hexdigest(),
            'observed_at': observed_at,
            'listing_count': len(listings),
        }
        date_proof = None
        if review := date_reviews.get(file_info['path']):
            observed_at, date_error, date_proof = documented_day(root, data, file_info['sha256'], review, date_registry)
            file_info['observed_at'] = observed_at
            if date_proof:
                file_info['observation_date_source'] = date_proof
        if date_error:
            file_info['observation_date_error'] = date_error
        manifest['files'].append(file_info)
        for listing in listings:
            if not isinstance(listing, dict) or 'properties' not in listing:
                continue
            identity = (listing.get('id'), listing.get('updated_at'), observed_at)
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
                observed_at=observed_at,
                currencies=currencies,
            )
            if observed_at:
                row['observation_date_basis'] = 'documented_collection' if date_proof else 'cache_pulled'
                row['observation_date_precision'] = 'day'
                row['observation_date_source'] = date_proof or {
                    'path': file_info['path'],
                    'sha256': file_info['sha256'],
                    'field': date_field,
                }
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
    for path in sorted((root / 'pricing/raw/traderie/runeword-refresh').glob('*-page*.json')):
        cached = json.loads(path.read_text())
        manifest['files'].append(
            {
                'path': str(path.relative_to(root)),
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'observed_at': cached['observed_at'],
                'listing_count': len(cached['response']['listings']),
            }
        )
        for listing in cached['response']['listings']:
            row = normalize_listing(
                listing,
                name=cached['item']['name'],
                category='runewords',
                source=cached['source'],
                observed_at=cached['observed_at'],
                currencies=currencies,
            )
            if row['evidence_kind'] == 'ask' and (
                listing.get('active') is not True or listing.get('selling') is not True
            ):
                row['evidence_kind'] = 'unverified_listing'
            row['conversion'].update(
                snapshot_id=manifest['currency_snapshot'], snapshot_date=manifest['currency_snapshot_date']
            )
            rows.append(row)
    manifest['scope_counts'] = dict(Counter(r['scope_status'] for r in rows))
    manifest['observations'] = len(rows)
    return rows, manifest
