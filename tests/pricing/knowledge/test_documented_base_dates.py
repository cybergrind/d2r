"""WP-B day recovery changes provenance, never scope or unknown item facts."""

import hashlib
from copy import deepcopy

import pytest

from pricing.knowledge.market import import_cache
from tests.pricing.knowledge.test_cache_dates import cache_root
from tests.pricing.knowledge.test_documented_cache_dates import write
from tests.pricing.knowledge.test_market import listing


REVIEW = 'pricing/knowledge/documented_collection_dates.json'
RAW = 'pricing/raw/traderie/monarch.json'
SOURCE = 'pricing/data/wp-b-prices.json'
LOG = 'pricing/data/wp-b.md'
IDS = 'pricing/tools/wp_b_ids.txt'


def text_hash(root, path, text):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare(root):
    cache_root(root)
    raw = [listing(item_id='123', updated_at='2026-09-18T12:00:00Z')]
    source = {
        '_meta': {
            'pulled': '2026-09-18',
            'source': 'Traderie JSON API https://traderie.com/api/diablo2resurrected/listings?item=<id>&page=0..3 '
            '(50/page, page 0-based), via pricing/tools/traderie.py listings <id> 4 --json '
            '(no server filter); raw in pricing/raw/traderie/<slug>.json',
        },
        'monarch': {
            'name': 'Monarch',
            'item_id': '123',
            'pulled_pages': 1,
            'n_total': 1,
            'n_scope': 1,
            'game_version_dist_all': {'reign of the warlock': 1},
            'game_version_dist_sc_nl_pc': {'reign of the warlock': 1},
            'buckets': {},
        },
    }
    entry = {
        'path': RAW,
        'sha256': write(root, RAW, raw),
        'catalog_id': '123',
        'listing_count': 1,
        'source': {
            'path': SOURCE,
            'sha256': write(root, SOURCE, source),
            'locator': '/monarch',
            'scope_locator': '/monarch/n_scope',
        },
        'collection_log': {
            'path': LOG,
            'sha256': text_hash(
                root,
                LOG,
                '# WP-B (pulled 2026-09-18; v2 regenerated same day)\n'
                'Raw: pricing/raw/traderie/{archon-plate,…,mancatcher}.json\n',
            ),
        },
        'catalog_ids': {'path': IDS, 'sha256': text_hash(root, IDS, 'monarch 123\n')},
    }
    review = {'schema_version': 1, 'files': [entry]}
    write(root, REVIEW, review)
    return raw, source, review


def repin(root, raw, source, review):
    entry = review['files'][0]
    entry['sha256'] = write(root, RAW, raw)
    entry['source']['sha256'] = write(root, SOURCE, source)
    write(root, REVIEW, review)


def test_documented_base_day_retains_exact_ask_and_unknown_facts(tmp_path):
    raw, source, review = prepare(tmp_path)
    raw[0]['properties'] = [p for p in raw[0]['properties'] if p['property_id'] != 738]
    repin(tmp_path, raw, source, review)
    rows, manifest = import_cache(tmp_path)
    assert rows[0]['observed_at'] == '2026-09-18'
    assert rows[0]['observation_date_source']['document']['field'] == '/_meta/pulled'
    assert rows[0]['observation_date_basis'] == 'documented_collection'
    assert rows[0].get('ethereal') is None
    assert rows[0]['ask_ist'] == 2
    assert manifest['files'][0]['observed_at'] == '2026-09-18'


@pytest.mark.parametrize(
    'mutation',
    [
        'catalog',
        'ids',
        'raw-count',
        'scope-count',
        'versions',
        'scoped-versions',
        'date',
        'future-update',
        'raw-reference',
        'query',
        'cross-item',
        'log-date',
        'ids-hash',
    ],
)
def test_changed_base_collection_proof_does_not_supply_date(tmp_path, mutation):
    raw, source, review = prepare(tmp_path)
    entry = review['files'][0]
    if mutation == 'catalog':
        raw[0]['item_id'] = '999'
    if mutation == 'ids':
        entry['catalog_ids']['sha256'] = text_hash(tmp_path, IDS, 'monarch 999\n')
    if mutation == 'raw-count':
        source['monarch']['n_total'] = 2
    if mutation == 'scope-count':
        source['monarch']['n_scope'] = 0
    if mutation == 'versions':
        source['monarch']['game_version_dist_all'] = {'unset': 1}
    if mutation == 'scoped-versions':
        source['monarch']['game_version_dist_sc_nl_pc'] = {}
    if mutation == 'date':
        source['_meta']['pulled'] = '20260918'
    if mutation == 'future-update':
        raw[0]['updated_at'] = '2026-09-19T00:00:00Z'
    if mutation == 'raw-reference':
        source['_meta']['source'] = 'A different collection.'
    if mutation == 'query':
        source['_meta']['source'] = source['_meta']['source'].replace('page=0..3', 'page=0..1')
    if mutation == 'cross-item':
        entry['source']['scope_locator'] = '/other/n_scope'
    if mutation == 'log-date':
        entry['collection_log']['sha256'] = text_hash(tmp_path, LOG, '# WP-B (pulled 2026-09-19)\n')
    if mutation == 'ids-hash':
        entry['catalog_ids']['sha256'] = '0' * 64
    repin(tmp_path, raw, source, review)
    rows, manifest = import_cache(tmp_path)
    assert rows[0]['observed_at'] is None
    assert manifest['files'][0]['observation_date_error']


def test_historical_unset_version_count_never_becomes_current_scope(tmp_path):
    raw, source, review = prepare(tmp_path)
    raw[0]['properties'] = [p for p in raw[0]['properties'] if p['property_id'] != 1854]
    source['monarch']['game_version_dist_all'] = {'unset': 1}
    source['monarch']['game_version_dist_sc_nl_pc'] = {'unset': 1}
    repin(tmp_path, raw, source, review)
    rows, _ = import_cache(tmp_path)
    assert rows[0]['observed_at'] == '2026-09-18'
    assert rows[0]['scope_status'] == 'unknown'


def test_identical_raw_duplicate_preserves_collection_count_without_extra_seller(tmp_path):
    raw, source, review = prepare(tmp_path)
    raw.append(deepcopy(raw[0]))
    source['monarch'].update(
        n_total=2,
        n_scope=2,
        game_version_dist_all={'reign of the warlock': 2},
        game_version_dist_sc_nl_pc={'reign of the warlock': 2},
    )
    review['files'][0]['listing_count'] = 2
    repin(tmp_path, raw, source, review)
    rows, _ = import_cache(tmp_path)
    assert len(rows) == 1
    assert rows[0]['observed_at'] == '2026-09-18'


@pytest.mark.parametrize(('field', 'value'), [(800, True), (799, 'hardcore')])
def test_recovered_day_cannot_make_ladder_or_hardcore_comparable(tmp_path, field, value):
    raw, source, review = prepare(tmp_path)
    prop = next(p for p in raw[0]['properties'] if p['property_id'] == field)
    prop[prop['type']] = value
    source['monarch']['n_scope'] = 0
    source['monarch']['game_version_dist_sc_nl_pc'] = {}
    repin(tmp_path, raw, source, review)
    rows, _ = import_cache(tmp_path)
    assert rows[0]['observed_at'] == '2026-09-18'
    assert rows[0]['scope_status'] == 'rejected'


@pytest.mark.parametrize('part', ['raw', 'source', 'log', 'ids'])
def test_stale_source_bytes_cannot_supply_a_base_collection_date(tmp_path, part):
    prepare(tmp_path)
    path = {'raw': RAW, 'source': SOURCE, 'log': LOG, 'ids': IDS}[part]
    with (tmp_path / path).open('a') as stream:
        stream.write('\n')
    rows, manifest = import_cache(tmp_path)
    assert rows[0]['observed_at'] is None
    assert manifest['files'][0]['observation_date_error']


def test_conflicting_duplicate_is_not_accepted_as_one_collection_snapshot(tmp_path):
    raw, source, review = prepare(tmp_path)
    raw.append(deepcopy(raw[0]))
    raw[1]['prices'][0]['quantity'] = 99
    source['monarch'].update(
        n_total=2,
        n_scope=2,
        game_version_dist_all={'reign of the warlock': 2},
        game_version_dist_sc_nl_pc={'reign of the warlock': 2},
    )
    review['files'][0]['listing_count'] = 2
    repin(tmp_path, raw, source, review)
    rows, manifest = import_cache(tmp_path)
    assert all(r['observed_at'] is None for r in rows)
    assert manifest['files'][0]['observation_date_error']


def test_base_date_proof_uses_published_source_snapshot(tmp_path):
    from pricing.knowledge.artifacts import _read, supplied_artifacts
    from pricing.knowledge.documented_cache_dates import validate_records

    prepare(tmp_path)
    paths = [tmp_path / p for p in (REVIEW, RAW, SOURCE, LOG, IDS)]
    snapshot = {p.resolve(): _read(p) for p in paths}
    (tmp_path / IDS).write_text('monarch 999\n')
    with supplied_artifacts(snapshot):
        validate_records(tmp_path)
    with pytest.raises(ValueError, match='fingerprint'):
        validate_records(tmp_path)
