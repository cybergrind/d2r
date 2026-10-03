import json
from datetime import date

import pytest

from inventory_tracking.appraisal.text import format_appraisal
from pricing.knowledge.commodity_market import ROOT, build
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.item_bank.models import Item
from tests.pricing.knowledge.assessment.test_pipeline_context import database


@pytest.mark.parametrize('change', [{'item_id': 'wrong'}, {'active': None}, {'selling': None}, {'completed': True}])
def test_importer_does_not_promote_unknown_status_or_conflicting_identity(tmp_path, change):
    page = ROOT / 'pricing/raw/traderie/appraisal-commodities-20261003/700449418-page0.json'
    cached = json.loads(page.read_text())
    listing = next(r for r in cached['listings'] if r['amount'] == 1)
    cached['listings'] = [{**listing, **change}]
    target = tmp_path / page.relative_to(ROOT)
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(cached))
    data = tmp_path / 'pricing/data'
    data.mkdir(parents=True)
    for name in ('wp-f-ladder.json', 'appraisal-traderie-catalog.json'):
        (data / name).write_bytes((ROOT / 'pricing/data' / name).read_bytes())
    [row] = build(tmp_path)['rows']
    assert row['evidence_kind'] != 'ask'


def test_cached_commodity_page_has_reproducible_scoped_unit_quote(tmp_path):
    document = build()
    assert document == json.loads((ROOT / 'pricing/data/appraisal-commodity-market.json').read_text())
    rows = [r for r in document['rows'] if r['name'] == "Talic's Anguish"]
    assert len(rows) == 50
    assert {r['scope_status'] for r in rows} == {'verified', 'rejected'}
    result = retrieve_draft(
        Item('Uber Ancient Summon Material Act 1', 'normal', complete=True).capture(),
        database(tmp_path, rows),
        as_of=date(2026, 10, 3),
    )
    assert result['price_estimate']['estimate_ist'] == 1
    assert result['price_estimate']['sellers'] == 3
    assert all(r['amount'] == 1 for r in result['price_estimate']['comparables'])
    text = format_appraisal({'state': 'complete', 'request_id': 'talic', 'result': result})
    assert "Material: Talic's Anguish" in text
    assert 'Unit price: ~1 Ist' in text
    assert '2026-10-03' in text
    assert 'asks' in text
