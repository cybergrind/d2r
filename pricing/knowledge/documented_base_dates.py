"""Hash-bound WP-B collection days; legacy bucket scope is provenance only."""

import hashlib
import json
from collections import Counter
from pathlib import PurePosixPath

from pricing.knowledge.cache_dates import collection_day_evidence
from pricing.knowledge.documented_cache_dates import _read


SOURCE_PATH = 'pricing/data/wp-b-prices.json'
LOG_PATH = 'pricing/data/wp-b.md'
IDS_PATH = 'pricing/tools/wp_b_ids.txt'
RAW_DIRECTORY = PurePosixPath('pricing/raw/traderie')
RAW_REFERENCE = 'pricing/raw/traderie/{archon-plate,…,mancatcher}.json'
QUERY = 'https://traderie.com/api/diablo2resurrected/listings?item=<id>&page=0..3'


def original_counts(listings):
    """Reconstruct the collector denominator, without changing valuation scope."""
    all_versions, scope_versions = Counter(), Counter()
    count = 0
    for row in listings:
        properties = {p['property_id']: p.get(p['type']) for p in (row.get('properties') or [])}
        version = properties.get(1854) or 'unset'
        if type(version) is not str:
            raise ValueError('Invalid original game-version property')
        all_versions[version] += 1
        if properties.get(799) == 'softcore' and properties.get(800) is False and properties.get(798) == 'PC':
            scope_versions[version] += 1
            count += 'lord of destruction' not in version and 'classic' not in version
    return count, dict(all_versions), dict(scope_versions)


def checked_distribution(value, expected):
    return type(value) is dict and all(type(v) is int and v > 0 for v in value.values()) and value == expected


def documented_day(root, data, digest, review, registry):
    try:
        path = PurePosixPath(review['path'])
        slug = path.stem
        if (
            path.parent != RAW_DIRECTORY
            or path.suffix != '.json'
            or str(path) != review['path']
            or not slug
            or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in slug)
            or not (root / review['path']).resolve().is_relative_to(root.resolve())
            or type(data) is not list
            or not data
            or digest != review['sha256']
        ):
            raise ValueError('Changed or unsupported WP-B raw collection')
        source = review['source']
        if source.get('locator') != '/' + slug or source.get('scope_locator') != '/' + slug + '/n_scope':
            raise ValueError('WP-B source locator differs from raw basename')
        document = json.loads(_read(root, source, SOURCE_PATH))
        note = _read(root, review['collection_log'], LOG_PATH).decode()
        ids_text = _read(root, review['catalog_ids'], IDS_PATH).decode()
        pairs = [line.split() for line in ids_text.splitlines() if line.strip()]
        if any(len(pair) != 2 for pair in pairs) or len({pair[0] for pair in pairs}) != len(pairs):
            raise ValueError('Malformed or duplicate WP-B catalog mapping')
        ids = dict(pairs)
        catalog = review['catalog_id']
        if type(catalog) is not str or not catalog.isascii() or not catalog.isdecimal() or ids.get(slug) != catalog:
            raise ValueError('WP-B catalog mapping differs')
        meta = document['_meta']
        day, error, _ = collection_day_evidence({'pulled': meta['pulled'], 'listings': data})
        if error or not day:
            raise ValueError(error or 'Missing documented WP-B collection day')
        if (
            QUERY not in meta.get('source', '')
            or 'raw in pricing/raw/traderie/<slug>.json' not in meta['source']
            or not note.splitlines()[0].startswith('# WP-B')
            or 'pulled ' + day not in note.splitlines()[0]
            or RAW_REFERENCE not in note
        ):
            raise ValueError('WP-B collection log/query does not bind this date')
        evidence = document[slug]
        if (
            type(review['listing_count']) is not int
            or review['listing_count'] != len(data)
            or type(evidence['n_total']) is not int
            or evidence['n_total'] != len(data)
            or evidence['item_id'] != catalog
            or any(str(row.get('item_id')) != catalog for row in data)
        ):
            raise ValueError('WP-B catalog identity or raw count differs')
        seen = {}
        for row in data:
            key = row['id']
            if key in seen and row != seen[key]:
                raise ValueError('Conflicting duplicate listing records')
            seen[key] = row
        count, all_versions, scope_versions = original_counts(data)
        if (
            type(evidence['n_scope']) is not int
            or evidence['n_scope'] != count
            or not checked_distribution(evidence['game_version_dist_all'], all_versions)
            or not checked_distribution(evidence['game_version_dist_sc_nl_pc'], scope_versions)
        ):
            raise ValueError('WP-B research denominator differs from raw collection')
        return (
            day,
            None,
            {
                'path': review['path'],
                'sha256': digest,
                'review': {
                    'path': registry['path'],
                    'entry_sha256': hashlib.sha256(
                        json.dumps(review, sort_keys=True, separators=(',', ':')).encode()
                    ).hexdigest(),
                },
                'document': {'path': source['path'], 'sha256': source['sha256'], 'field': '/_meta/pulled'},
                'collection_log': dict(review['collection_log']),
                'catalog_ids': dict(review['catalog_ids']),
            },
        )
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as error:
        return None, 'Unverified documented WP-B collection date: ' + str(error), None
