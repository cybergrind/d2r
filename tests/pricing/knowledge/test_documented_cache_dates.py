import hashlib
import json

import pytest

from pricing.knowledge.market import import_cache
from tests.pricing.knowledge.test_cache_dates import cache_root
from tests.pricing.knowledge.test_market import listing


REVIEW = 'pricing/knowledge/documented_collection_dates.json'
RAW = 'pricing/raw/traderie/wph-example.json'
SOURCE = 'pricing/data/wp-h-jewels-charms.json'
LOG = 'pricing/data/wp-h.md'


def write(root, path, value):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value))
    return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare(root):
    cache_root(root)
    rows = [listing(item_id='123', updated_at='2026-09-18T12:00:00Z')]
    raw_hash = write(root, RAW, rows)
    source = {
        '_meta': {'date': '2026-09-18', 'raw': 'pricing/raw/traderie/wph-*.json'},
        'item': {
            'n_scope': 1,
            'sources': [
                {
                    'url': 'https://traderie.com/api/diablo2resurrected/listings?item=123&page=0..1',
                    'date': '2026-09-18',
                    'kind': 'asks (Traderie, SC/NL/PC client-filtered)',
                }
            ],
        },
    }
    source_hash = write(root, SOURCE, source)
    (root / LOG).write_text('# WP-H (pulled 2026-09-18)\nRaw: pricing/raw/traderie/wph-*.json\n')
    log_hash = hashlib.sha256((root / LOG).read_bytes()).hexdigest()
    review = {
        'schema_version': 1,
        'files': [
            {
                'path': RAW,
                'sha256': raw_hash,
                'catalog_id': '123',
                'listing_count': 1,
                'source': {
                    'path': SOURCE,
                    'sha256': source_hash,
                    'locator': '/item/sources/0',
                    'scope_locator': '/item/n_scope',
                },
                'collection_log': {'path': LOG, 'sha256': log_hash},
            }
        ],
    }
    write(root, REVIEW, review)
    return rows, source, review


def test_explicit_dated_research_can_supply_bare_cache_collection_day(tmp_path):
    prepare(tmp_path)
    rows, manifest = import_cache(tmp_path)
    assert rows[0]['observed_at'] == '2026-09-18'
    assert rows[0]['observation_date_basis'] == 'documented_collection'
    assert rows[0]['observation_date_precision'] == 'day'
    proof = rows[0]['observation_date_source']
    assert proof['path'] == RAW
    assert proof['document']['path'] == SOURCE
    assert proof['document']['field'] == '/item/sources/0/date'
    assert proof['review']['path'] == REVIEW
    assert manifest['files'][0]['observed_at'] == '2026-09-18'


@pytest.mark.parametrize(
    'mutation',
    [
        'raw-hash',
        'source-hash',
        'log-hash',
        'wrong-item',
        'wrong-query',
        'wrong-count',
        'wrong-scope-count',
        'later-update',
        'invalid-update',
        'invalid-date',
        'report-date-conflict',
        'not-collection-log',
        'wrong-raw-family',
        'missing-source',
        'source-escape',
    ],
)
def test_unverified_research_binding_never_supplies_a_date(tmp_path, mutation):
    raw, source, review = prepare(tmp_path)
    entry = review['files'][0]
    if mutation == 'raw-hash':
        entry['sha256'] = '0' * 64
    if mutation == 'source-hash':
        entry['source']['sha256'] = '0' * 64
    if mutation == 'log-hash':
        entry['collection_log']['sha256'] = '0' * 64
    if mutation == 'wrong-item':
        raw[0]['item_id'] = '999'
        entry['sha256'] = write(tmp_path, RAW, raw)
    if mutation == 'wrong-query':
        source['item']['sources'][0]['url'] = 'https://traderie.com/api/diablo2resurrected/listings?item=999&page=0..1'
    if mutation == 'wrong-count':
        entry['listing_count'] = 2
    if mutation == 'wrong-scope-count':
        source['item']['n_scope'] = 2
    if mutation in ('later-update', 'invalid-update'):
        raw[0]['updated_at'] = '2026-09-19T00:00:00Z' if mutation == 'later-update' else 'invalid'
        entry['sha256'] = write(tmp_path, RAW, raw)
    if mutation == 'invalid-date':
        source['item']['sources'][0]['date'] = '20260918'
    if mutation == 'report-date-conflict':
        source['_meta']['date'] = '2026-09-19'
    if mutation == 'not-collection-log':
        (tmp_path / LOG).write_text('# Report published 2026-09-18\nRaw: pricing/raw/traderie/wph-*.json\n')
        entry['collection_log']['sha256'] = hashlib.sha256((tmp_path / LOG).read_bytes()).hexdigest()
    if mutation == 'wrong-raw-family':
        source['_meta']['raw'] = 'some-other-collection'
    if mutation not in ('source-hash', 'missing-source', 'source-escape'):
        entry['source']['sha256'] = write(tmp_path, SOURCE, source)
    if mutation == 'missing-source':
        entry['source']['path'] = 'pricing/data/absent.json'
    if mutation == 'source-escape':
        entry['source']['path'] = '../outside.json'
    write(tmp_path, REVIEW, review)
    rows, manifest = import_cache(tmp_path)
    assert rows[0]['observed_at'] is None
    assert rows[0]['observation_date_basis'] == 'unknown'
    assert manifest['files'][0]['observation_date_error']


def test_unlisted_file_cannot_borrow_a_reviewed_date(tmp_path):
    raw, _, _ = prepare(tmp_path)
    raw[0]['id'] = '2'
    write(tmp_path, 'pricing/raw/traderie/wph-another.json', raw)
    rows, _ = import_cache(tmp_path)
    assert next(r for r in rows if r['listing_id'] == '2')['observed_at'] is None


def test_collection_date_recovery_keeps_incompatible_scope_rejected(tmp_path):
    raw, source, review = prepare(tmp_path)
    raw[0]['properties'][1]['bool'] = True
    review['files'][0]['sha256'] = write(tmp_path, RAW, raw)
    source['item']['n_scope'] = 0
    review['files'][0]['source']['sha256'] = write(tmp_path, SOURCE, source)
    write(tmp_path, REVIEW, review)
    rows, _ = import_cache(tmp_path)
    assert rows[0]['observed_at'] == '2026-09-18'
    assert rows[0]['scope_status'] == 'rejected'


def test_published_collection_proof_uses_its_snapshot_not_changed_working_files(tmp_path):
    from pricing.knowledge.artifacts import _read, supplied_artifacts
    from pricing.knowledge.documented_cache_dates import validate_records

    prepare(tmp_path)
    paths = [tmp_path / p for p in (REVIEW, RAW, SOURCE, LOG)]
    snapshot = {p.resolve(): _read(p) for p in paths}
    (tmp_path / SOURCE).write_text('{}')
    with supplied_artifacts(snapshot):
        validate_records(tmp_path)
    with pytest.raises(ValueError, match='fingerprint'):
        validate_records(tmp_path)


def test_review_scope_and_date_cannot_be_borrowed_from_different_research_items(tmp_path):
    _, source, review = prepare(tmp_path)
    source['other'] = {'n_scope': 1}
    review['files'][0]['source']['scope_locator'] = '/other/n_scope'
    review['files'][0]['source']['sha256'] = write(tmp_path, SOURCE, source)
    write(tmp_path, REVIEW, review)
    rows, manifest = import_cache(tmp_path)
    assert rows[0]['observed_at'] is None
    assert manifest['files'][0]['observation_date_error']


def test_conflicting_wrapper_cannot_replace_reviewed_bare_collection(tmp_path):
    raw, _, review = prepare(tmp_path)
    review['files'][0]['sha256'] = write(tmp_path, RAW, {'pulled': '2026-09-19', 'listings': raw})
    write(tmp_path, REVIEW, review)
    rows, manifest = import_cache(tmp_path)
    assert rows[0]['observed_at'] is None
    assert manifest['files'][0]['observation_date_error']
