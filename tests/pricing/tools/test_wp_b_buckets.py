import json
from pathlib import Path

import pytest

from tests.pricing.scope_cases import VERIFIED, listings


if not (Path(__file__).resolve().parents[3] / 'pricing/data/wp-f-ladder.json').exists():
    pytest.skip('wp_b_buckets reads the local, git-ignored rune ladder at import', allow_module_level=True)

from pricing.tools import wp_b_buckets


def test_buckets_keep_exactly_the_kb_scope(tmp_path, monkeypatch):
    raw = tmp_path / 'pricing/raw/traderie'
    raw.mkdir(parents=True)
    (raw / 'flail.json').write_text(json.dumps(listings()))
    monkeypatch.setattr(wp_b_buckets, 'ROOT', str(tmp_path))
    result = wp_b_buckets.analyze('flail', 'id')
    assert result is not None
    assert result['n_scope'] == len(VERIFIED)
    rows = [row for bucket in result['buckets'].values() for row in bucket['cheapest']]
    assert sorted(row['listing_id'] for row in rows) == sorted(VERIFIED)
