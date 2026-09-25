import json

from pricing.knowledge.assessment.engine import assess
from pricing.knowledge.index import build_index
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.test_base_use import capture, word


def test_engine_includes_runeword_base_suitability_without_market_lookup():
    result = assess(capture(), profiles=[])
    infinity = word(result['base_uses'], 'Infinity')
    assert infinity['role'] == 'Act 2 mercenary'
    assert infinity['status'] == 'perfect preferred base'
    assert assess(capture(quality='magic'), profiles=[])['base_uses'] == []


def test_pipeline_preserves_one_engine_base_evaluation(tmp_path, monkeypatch):
    from pricing.knowledge.assessment import engine

    data = tmp_path / 'rows.json'
    data.write_text(json.dumps({'schema_version': 1, 'rows': []}))
    database = tmp_path / 'kb.sqlite3'
    build_index([data], database)
    calls = []
    expected = [{'runeword': 'Infinity', 'status': 'test result from engine'}]

    def evaluate(facts):
        calls.append(facts)
        return expected

    monkeypatch.setattr(engine, 'assess_runeword_base', evaluate)
    result = retrieve_draft(capture(), database)
    assert len(calls) == 1
    assert calls[0].base_name == 'Giant Thresher'
    assert result['assessment']['base_uses'] == expected
    assert 'uses' not in result['base_assessment']
