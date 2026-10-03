import json

from pricing.triage.engine import Tables
from pricing.triage.runtime import retrieve
from tests.inventory_tracking.appraisal.test_text import saved_result


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
    original = tables.load()
    assert tables.load() is original
    (tmp_path / 'rules.json').write_text(json.dumps({'keep_ist': 12.5, 'rows': []}))
    assert tables.load()['rules']['keep_ist'] == 12.5
    assert original['rules']['keep_ist'] == 0.25


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
    assert first.text == 'SELL — asks 0.25 Ist median · 10 sellers · 2026-10-03'
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


def test_unapproved_type_uses_legacy_and_keeps_triage_as_candidate(monkeypatch):
    from pricing.triage import runtime

    observation = saved_result()['result']['extraction']
    monkeypatch.setattr(runtime, 'enabled', lambda _: False)
    monkeypatch.setattr('inventory_tracking.appraisal.memory_backend.memory_evidence', lambda *_: {'legacy': True})
    result = runtime.guarded_retrieve(observation, None)
    assert result['legacy'] is True
    assert 'triage' not in result
    assert 'triage_candidate' in result
    assert runtime.shop_retrieve(observation) == {}
    monkeypatch.setattr(runtime, 'enabled', lambda _: True)
    assert 'triage' in runtime.guarded_retrieve(observation, None)


def test_quest_material_uses_fast_path_without_legacy_assessment(monkeypatch):
    from pricing.triage import runtime

    def forbidden(*args, **kwargs):
        raise AssertionError('Legacy appraisal called for enabled material')

    observation = {
        'item': {
            'name': 'Uber Ancient Summon Material Act 1',
            'base_code': 'ua1',
            'rarity': 'normal',
            'ethereal': False,
            'identified': True,
            'sockets': 0,
            'socket_contents': 'empty',
            'affixes': [],
        },
        'source': {'stat_capture_complete': True},
        'decoded_stats': [],
    }
    monkeypatch.setattr('inventory_tracking.appraisal.memory_backend.memory_evidence', forbidden)
    result = runtime.guarded_retrieve(observation, None)
    assert result['triage']['band']['name'] == "Talic's Anguish"
    assert result['triage']['decision_ist'] is not None
