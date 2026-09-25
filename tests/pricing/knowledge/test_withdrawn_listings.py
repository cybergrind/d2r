import json

import pytest

from pricing.knowledge.market import import_cache, summarize
from tests.pricing.knowledge.assessment.test_listing_history import row
from tests.pricing.knowledge.test_market import listing


def test_withdrawal_supersedes_old_ask_before_watch_filtering():
    old = row('2026-09-23T12:00:00Z', 1)
    withdrawn = {**row('2026-09-24T12:00:00Z', 1), 'evidence_kind': 'inactive_listing'}
    for rows in ([old, withdrawn], [withdrawn, old]):
        assert summarize(rows)['priced_sellers'] == 0


@pytest.mark.parametrize(('latest_active', 'kind'), [(False, 'inactive_listing'), (None, 'unverified_listing')])
def test_runeword_import_retains_inactive_observations_for_supersession(tmp_path, latest_active, kind):
    data = tmp_path / 'pricing/data'
    data.mkdir(parents=True)
    for name in ('wp-b-prices.json', 'wp-i-uniques-misc.json'):
        (data / name).write_text('{}')
    (data / 'wp-f-ladder.json').write_text(json.dumps({'_meta': {'date': '2026-09-24'}, 'Ist': {'ist': 1}}))
    cache = tmp_path / 'pricing/raw/traderie/runeword-refresh'
    cache.mkdir(parents=True)
    for page, active in enumerate((True, latest_active)):
        payload = {
            'item': {'name': 'Spirit'},
            'source': 'fixture',
            'observed_at': f'2026-09-{23 + page}T12:00:00Z',
            'response': {'listings': [listing(active=active, selling=True, completed=active is False)]},
        }
        (cache / f'spirit-page{page}.json').write_text(json.dumps(payload))
    rows, _ = import_cache(tmp_path)
    assert len(rows) == 2
    assert rows[1]['evidence_kind'] == kind
    assert summarize(rows)['priced_sellers'] == 0
