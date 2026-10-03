import json

from pricing.knowledge import artifacts
from pricing.triage import build


def test_ingestion_reads_catalog_once_per_batch_and_refreshes_next_batch(tmp_path, monkeypatch):
    catalog = tmp_path / 'base-catalog.json'
    catalog.write_text('{"version": 1}')
    data = tmp_path / 'pricing/data'
    data.mkdir(parents=True)
    (data / 'appraisal-traderie-catalog.json').write_text(
        json.dumps({'items': [{'id': '1', 'name': 'Example', 'type': 'base'}]})
    )
    (data / 'wp-f-ladder.json').write_text('{}')
    (data / 'appraisal-market.jsonl').write_text('')
    folder = tmp_path / 'pricing/raw/traderie/pull-test'
    folder.mkdir(parents=True)
    (folder / '1-p0.json').write_text(json.dumps({'listings': [{'item_id': '1'}, {'item_id': '1'}]}))
    monkeypatch.setattr(build, 'BASE_CATALOG', catalog, raising=False)
    monkeypatch.setattr(
        build, 'normalize_listing', lambda *args, **kwargs: {'catalog': artifacts.read_artifact(catalog).decode()}
    )
    monkeypatch.setattr(build, 'listing_defaults', lambda row: row)
    monkeypatch.setattr('pricing.triage.currencies.apply_gem_quotes', lambda rows, rates: rows)
    monkeypatch.setattr('pricing.triage.stock_evidence.restore', lambda rows, root: rows)
    reads = []
    original = artifacts._read

    def read(path):
        reads.append(path)
        return original(path)

    monkeypatch.setattr(artifacts, '_read', read)
    rows, _ = build.market_rows(tmp_path)
    assert len(reads) == 1
    assert rows == [{'catalog': '{"version": 1}'}] * 2
    catalog.write_text('{"version": 2}')
    rows, _ = build.market_rows(tmp_path)
    assert len(reads) == 2
    assert rows == [{'catalog': '{"version": 2}'}] * 2
