import json

from pricing.triage.engine import Tables
from pricing.triage.runtime import retrieve
from tests.inventory_tracking.appraisal.test_text import saved_result
from tests.pricing.knowledge.reports import present


def test_fast_retrieval_does_not_call_detail_assessment(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Detail engine called on fast path')

    monkeypatch.setattr('pricing.knowledge.assessment.engine.assess_result', forbidden)
    result = retrieve(saved_result()['result']['extraction'])
    assert set(result) == {'triage'}
    assert result['triage']['verdict'] in ('sell', 'slow', 'self', 'vendor')
    assert result['triage']['keep_ist'] == 0.25


def test_table_reload_changes_threshold_without_publication(tmp_path):
    for name, value in [('bands', {'bands': []}), ('rules', {'keep_ist': 0.25, 'rows': []}), ('own', {'rows': []})]:
        (tmp_path / f'{name}.json').write_text(json.dumps(value))
    tables = Tables(tmp_path)
    original = present(tables.load())
    assert tables.load() is original
    rule = {'category': 'base', 'name': 'Example', 'premium': True}
    (tmp_path / 'rules.json').write_text(json.dumps({'keep_ist': 12.5, 'rows': [rule]}))
    assert present(tables.load())['rules']['keep_ist'] == 12.5
    assert original['rules']['keep_ist'] == 0.25
    from pricing.triage.engine import assess

    item = {'category': 'base', 'name': 'Example'}
    assert assess(item, original)['verdict'] == 'vendor'
    assert assess(item, tables.load())['verdict'] == 'sell'


def test_alt_d_card_starts_with_same_dated_triage_band():
    from inventory_tracking.appraisal.presentation import ItemAssessment
    from inventory_tracking.presentation import Tone

    record = saved_result()
    record['result']['triage'] = {
        'verdict': 'sell',
        'reason': 'asks',
        'stale': False,
        'band': {'median_ist': 0.25, 'sellers': 10, 'observed_at': '2026-10-03'},
    }
    first = ItemAssessment.from_record(record).to_osd()[0]
    assert first.text == 'TRADE — asks 0.25 Ist median · 10 sellers · 2026-10-03'
    assert first.tone == Tone.TIER_HIGH


def test_triage_card_has_one_actionable_trade_verdict():
    from inventory_tracking.appraisal.presentation import ItemAssessment

    record = saved_result()
    record['result']['triage'] = {'verdict': 'vendor', 'reason': 'no matching variant', 'band': None}
    record['result']['assessment'] = {'trade_tier': {'status': 'reviewed', 'tier': 'trash'}}
    text = ItemAssessment.from_record(record).to_text()
    assert 'VENDOR — no matching variant' in text
    assert 'Trade tier:' not in text
    assert 'Price: not assessed' not in text


def test_own_use_update_does_not_reload_price_tables(tmp_path, monkeypatch):
    from pathlib import Path

    import pytest

    for name, value in [('bands', {'bands': []}), ('rules', {'keep_ist': 0.25, 'rows': []}), ('own', {'rows': []})]:
        (tmp_path / f'{name}.json').write_text(json.dumps(value))
    tables = Tables(tmp_path)
    original = present(tables.load())
    read_text = Path.read_text
    reads = []

    def read(path, *args, **kwargs):
        reads.append(path.name)
        assert path.name == 'own.json', 'Small own-use update reread the large market tables'
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', read)
    path = tmp_path / 'own.json'
    path.write_text('{invalid')
    with pytest.raises(json.JSONDecodeError):
        tables.load()
    assert tables.data is original
    own = {'rows': [{'category': 'uniques', 'name': 'Example', 'label': 'Personal alternative'}]}
    path.write_text(json.dumps(own))
    updated = present(tables.load())
    assert updated['own'] == own
    assert original['own'] == {'rows': []}
    assert updated['bands'] is original['bands']
    assert updated['commodity_lots'] is original['commodity_lots']
    assert tables.load() is updated
    assert reads == ['own.json', 'own.json']


def test_rule_reload_reuses_bands_but_rebuilds_sale_lots(tmp_path, monkeypatch):
    from pathlib import Path

    import pytest

    from pricing.triage.engine import assess

    band = {
        'category': 'gems',
        'name': 'Perfect Ruby',
        'bucket': 'quantity:10',
        'quantity': 10,
        'q1_ist': 0.1,
        'sellers': 3,
        'liquidity': 'thin',
    }
    for name, value in [('bands', {'bands': [band]}), ('rules', {'keep_ist': 0.25, 'rows': []}), ('own', {'rows': []})]:
        (tmp_path / f'{name}.json').write_text(json.dumps(value))
    tables = Tables(tmp_path)
    original = present(tables.load())
    assert original['commodity_lots']
    read_text = Path.read_text

    def read(path, *args, **kwargs):
        assert path.name != 'bands.json', 'Rule update reparsed market data'
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', read)
    rule = {'category': 'base', 'name': 'Example', 'premium': True}
    (tmp_path / 'rules.json').write_text(json.dumps({'keep_ist': 2, 'rows': [rule]}))
    (tmp_path / 'own.json').write_text('{invalid')
    with pytest.raises(json.JSONDecodeError):
        tables.load()
    assert tables.data is original
    (tmp_path / 'own.json').write_text(json.dumps({'rows': [], 'reviewed_at': '2026-10-06'}))
    updated = present(tables.load())
    assert updated['bands'] is original['bands']
    assert not updated['commodity_lots']
    assert original['commodity_lots']
    assert original['rules']['keep_ist'] == 0.25
    assert updated['own']['reviewed_at'] == '2026-10-06'
    assert assess({'category': 'base', 'name': 'Example'}, updated)['verdict'] == 'sell'

    monkeypatch.setattr(Path, 'read_text', read_text)
    (tmp_path / 'bands.json').write_text(json.dumps({'bands': [band | {'q1_ist': 0.3}], 'revision': 2}))
    refreshed = present(tables.load())
    assert refreshed['bands'] is not updated['bands']
    assert refreshed['commodity_lots']
    assert not updated['commodity_lots']
