"""Reviewed, hash-bound collection records for otherwise undated raw lists."""

import hashlib
import json
from pathlib import PurePosixPath
from urllib.parse import parse_qs, urlsplit

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.policies.sources import resolve_pointer
from pricing.knowledge.cache_dates import collection_day_evidence


REVIEW_PATH = 'pricing/knowledge/documented_collection_dates.json'
RAW_DIRECTORY = PurePosixPath('pricing/raw/traderie')
RAW_REFERENCE = 'pricing/raw/traderie/wph-*.json'
SOURCE_PATH = 'pricing/data/wp-h-jewels-charms.json'
LOG_PATH = 'pricing/data/wp-h.md'
ASK_KIND = 'asks (Traderie, SC/NL/PC client-filtered)'


def load_reviews(root):
    path = root / REVIEW_PATH
    try:
        raw = read_artifact(path)
    except FileNotFoundError:
        return {}, None
    return parse_reviews(raw), {'path': REVIEW_PATH, 'sha256': hashlib.sha256(raw).hexdigest()}


def parse_reviews(raw):
    document = json.loads(raw)
    if document.get('schema_version') != 1 or not isinstance(document.get('files'), list):
        raise ValueError('Invalid documented collection-date registry')
    result = {}
    for review in document['files']:
        path = PurePosixPath(review['path'])
        base_review = review.get('source', {}).get('path') == 'pricing/data/wp-b-prices.json'
        if (
            path.parent != RAW_DIRECTORY
            or (not path.name.startswith('wph-') and not base_review)
            or path.suffix != '.json'
            or str(path) != review['path']
            or review['path'] in result
        ):
            raise ValueError('Duplicate or unsupported collection-date cache path')
        result[review['path']] = review
    return result


def _read(root, source, expected_path):
    path = root / source['path']
    if source['path'] != expected_path or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Unsupported collection-date source path')
    raw = read_artifact(path)
    if hashlib.sha256(raw).hexdigest() != source['sha256']:
        raise ValueError('Collection-date source fingerprint changed')
    return raw


def _original_scope_count(listings):
    # This reconstructs the cited research denominator, not today's valuation scope.
    expected = {799: ('string', 'softcore'), 800: ('bool', False), 798: ('string', 'PC')}
    count = 0
    for row in listings:
        props = row.get('properties') or []
        valid = True
        for key, (kind, value) in expected.items():
            fields = [p for p in props if p.get('property_id') == key]
            valid &= bool(
                len(fields) == 1
                and fields[0].get('type') == kind
                and type(fields[0].get(kind)) is type(value)
                and fields[0].get(kind) == value
            )
        count += valid
    return count


def documented_day(root, data, digest, review, registry):
    """Return a cited collection day or an explicit error; never repair raw data."""
    if review.get('source', {}).get('path') == 'pricing/data/wp-b-prices.json':
        from pricing.knowledge.documented_base_dates import documented_day as base_day

        return base_day(root, data, digest, review, registry)
    try:
        if (
            not isinstance(data, list)
            or not data
            or digest != review['sha256']
            or not (root / review['path']).resolve().is_relative_to(root.resolve())
        ):
            raise ValueError('Changed or unsupported bare collection cache')
        source = review['source']
        parent, separator, index = source['locator'].rpartition('/sources/')
        if not separator or index != '0' or source['scope_locator'] != parent + '/n_scope':
            raise ValueError('Collection date and scope must belong to the same research item')
        document = json.loads(_read(root, source, SOURCE_PATH))
        note = _read(root, review['collection_log'], LOG_PATH).decode()
        evidence = resolve_pointer(document, source['locator'])
        day, error, _ = collection_day_evidence({'pulled': evidence['date'], 'listings': data})
        if error or not day:
            raise ValueError(error or 'Missing explicit documented collection day')
        parsed = urlsplit(evidence['url'])
        expected_query = {'item': [review['catalog_id']], 'page': ['0..1']}
        if (
            (parsed.scheme, parsed.netloc, parsed.path) != ('https', 'traderie.com', '/api/diablo2resurrected/listings')
            or parsed.fragment
            or parse_qs(parsed.query) != expected_query
            or evidence.get('kind') != ASK_KIND
            or document.get('_meta', {}).get('date') != day
            or RAW_REFERENCE not in document.get('_meta', {}).get('raw', '')
            or 'pulled ' + day not in note.splitlines()[0]
            or RAW_REFERENCE not in note
        ):
            raise ValueError('Research record does not bind this collection date and query')
        if (
            not isinstance(review['catalog_id'], str)
            or not review['catalog_id'].isdigit()
            or type(review['listing_count']) is not int
            or len(data) != review['listing_count']
            or any(str(row.get('item_id')) != review['catalog_id'] for row in data)
        ):
            raise ValueError('Collection catalog identity or listing count differs')
        count = resolve_pointer(document, source['scope_locator'])
        if type(count) is not int or count != _original_scope_count(data):
            raise ValueError('Collection scope count differs from the dated research')
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
                'document': {'path': source['path'], 'sha256': source['sha256'], 'field': source['locator'] + '/date'},
                'collection_log': dict(review['collection_log']),
            },
        )
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as error:
        return None, 'Unverified documented collection date: ' + str(error), None


def runtime_paths(root, reviews=None):
    if reviews is None:
        reviews, _ = load_reviews(root)
    paths = {REVIEW_PATH, SOURCE_PATH, LOG_PATH, *reviews}
    if any(review.get('source', {}).get('path') == 'pricing/data/wp-b-prices.json' for review in reviews.values()):
        from pricing.knowledge.documented_base_dates import IDS_PATH, LOG_PATH as BASE_LOG, SOURCE_PATH as BASE_SOURCE

        paths.update((BASE_SOURCE, BASE_LOG, IDS_PATH))
    return {root / path: 'reviewed collection-date provenance' for path in sorted(paths)}


def validate_records(root):
    reviews, registry = load_reviews(root)
    for review in reviews.values():
        raw = read_artifact(root / review['path'])
        _, error, _ = documented_day(root, json.loads(raw), hashlib.sha256(raw).hexdigest(), review, registry)
        if error:
            raise ValueError(error)
