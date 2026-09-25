import json

import pytest

from pricing.knowledge.artifacts import artifact_snapshot
from pricing.knowledge.assessment import base_use
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.base_use import assess_runeword_base
from pricing.knowledge.index import build_index
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.test_base_use import capture, word


def test_refreshed_recipes_are_pinned_until_next_assessment(tmp_path, monkeypatch):
    document = json.loads(base_use.UTILITY.read_bytes())
    path = tmp_path / 'utility.json'
    path.write_text(json.dumps(document))
    monkeypatch.setattr(base_use, 'UTILITY', path)
    with artifact_snapshot([path]):
        original = word(assess_runeword_base(normalize(capture())), 'Infinity')
        path.write_text(json.dumps({'schema_version': 1, 'rows': []}))
        assert word(assess_runeword_base(normalize(capture())), 'Infinity') == original
        path.unlink()
        assert word(assess_runeword_base(normalize(capture())), 'Infinity') == original
    path.write_text(json.dumps({'schema_version': 1, 'rows': []}))
    assert assess_runeword_base(normalize(capture())) == []


def test_recipes_cannot_be_mutated_by_consumers():
    row = next(r for r in base_use.recipe_catalog() if r.get('kind') == 'base_rule')
    with pytest.raises(TypeError):
        row['details']['recommended'] = False


def test_utility_refresh_requires_matching_index(tmp_path, monkeypatch):
    path = tmp_path / 'utility.json'
    path.write_text(json.dumps({'schema_version': 1, 'rows': []}))
    monkeypatch.setattr(base_use, 'UTILITY', path)
    database = tmp_path / 'kb.sqlite3'
    build_index([path], database)
    path.write_text(json.dumps({'schema_version': 1, 'rows': [], 'revision': 2}))
    with pytest.raises(ValueError, match=r'utility.*index.*rebuild'):
        retrieve_draft(capture(), database)
    build_index([path], database)
    result = retrieve_draft(capture(), database)
    assert str(path.resolve()) in result['assessment']['artifact_generations']
