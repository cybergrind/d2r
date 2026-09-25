import hashlib
import json

import pytest

from pricing.knowledge.market import import_cache
from tests.pricing.knowledge.test_market import listing


def cache_root(root):
    data = root / 'pricing/data'
    data.mkdir(parents=True)
    for name in ('wp-b-prices.json', 'wp-i-uniques-misc.json'):
        (data / name).write_text('{}')
    (data / 'wp-f-ladder.json').write_text(json.dumps({'_meta': {'date': '2026-09-18'}, 'Ist': {'ist': 1}}))
    cache = root / 'pricing/raw/traderie'
    cache.mkdir(parents=True)
    return cache


def test_explicit_pull_day_survives_import_with_hash_and_day_precision(tmp_path):
    cache = cache_root(tmp_path)
    raw = listing(updated_at='2026-09-18T23:59:59Z', active=True, selling=True)
    # An earlier alphabetical bare copy must not erase the dated observation.
    (cache / 'a-bare.json').write_text(json.dumps([raw]))
    path = cache / 'z-dated.json'
    path.write_text(json.dumps({'pulled': '2026-09-18', 'listings': [raw]}))
    rows, manifest = import_cache(tmp_path)
    dated = [r for r in rows if r['observed_at'] == '2026-09-18']
    assert len(dated) == 1
    row = dated[0]
    assert row['observation_date_basis'] == 'cache_pulled'
    assert row['observation_date_precision'] == 'day'
    assert row['observation_date_source'] == {
        'path': 'pricing/raw/traderie/z-dated.json',
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'field': '/pulled',
    }
    assert manifest['files'][1]['observed_at'] == '2026-09-18'
    assert any(r['observed_at'] is None for r in rows)


@pytest.mark.parametrize('pulled', [None, False, '20260918', '2026-02-30', '2026-09-18T12:00:00Z'])
def test_invalid_or_absent_pull_day_never_uses_listing_date_or_filename(tmp_path, pulled):
    cache = cache_root(tmp_path)
    (cache / 'dated-2026-09-18.json').write_text(
        json.dumps(
            {
                'pulled': pulled,
                'listings': [listing(updated_at='2026-09-18T12:00:00Z')],
            }
        )
    )
    rows, manifest = import_cache(tmp_path)
    assert rows[0]['observed_at'] is None
    assert manifest['files'][0]['observed_at'] is None


def test_listing_updated_after_pull_day_invalidates_cache_date(tmp_path):
    cache = cache_root(tmp_path)
    (cache / 'contradiction.json').write_text(
        json.dumps(
            {
                'pulled': '2026-09-18',
                'listings': [listing(updated_at='2026-09-19T00:00:00Z')],
            }
        )
    )
    rows, manifest = import_cache(tmp_path)
    assert rows[0]['observed_at'] is None
    assert 'after' in manifest['files'][0]['observation_date_error']
