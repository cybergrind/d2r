import json

import pytest

from pricing.knowledge import definition_store
from pricing.knowledge.assessment.handlers.definitions import named_definitions
from pricing.knowledge.assessment.handlers.runeword import definitions as assessed_runewords
from pricing.knowledge.runeword_market import definitions as listed_runewords


def publish(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(
        json.dumps(
            {
                'schema_version': 1,
                'rows': [
                    {'rarity': 'runeword', 'name': 'Fixture', 'roll_ranges': {'9': {'min': value, 'max': value}}},
                    {'rarity': 'set', 'name': 'Set Fixture', 'base_codes': ['test']},
                ],
            }
        )
    )
    temporary.replace(path)


def test_all_definition_consumers_reload_same_immutable_generation(tmp_path, monkeypatch):
    path = tmp_path / 'definitions.json'
    publish(path, 10)
    monkeypatch.setattr(definition_store, 'STORE', definition_store.DefinitionStore(path))
    first = definition_store.catalog()
    assert assessed_runewords() is listed_runewords()
    assert assessed_runewords()['Fixture']['roll_ranges']['9']['min'] == 10
    assert ('set', 'Set Fixture') in named_definitions()
    with pytest.raises(TypeError):
        assessed_runewords()['Fixture']['roll_ranges']['9']['min'] = 99
    assert definition_store.catalog() is first
    publish(path, 20)
    second = definition_store.catalog()
    assert first.generation != second.generation
    assert assessed_runewords()['Fixture']['roll_ranges']['9']['min'] == 20
    assert listed_runewords()['Fixture']['roll_ranges']['9']['min'] == 20
    assert first.runewords['Fixture']['roll_ranges']['9']['min'] == 10


def test_invalid_update_is_not_served_as_current_and_valid_update_recovers(tmp_path):
    path = tmp_path / 'definitions.json'
    publish(path, 10)
    store = definition_store.DefinitionStore(path)
    first = store.load()
    path.write_text('{')
    with pytest.raises(json.JSONDecodeError):
        store.load()
    publish(path, 30)
    assert store.load().generation != first.generation


def test_definition_snapshot_pins_nested_consumers_and_releases_after_failure(tmp_path, monkeypatch):
    path = tmp_path / 'definitions.json'
    publish(path, 10)
    monkeypatch.setattr(definition_store, 'STORE', definition_store.DefinitionStore(path))

    def interrupted_assessment():
        with definition_store.definition_snapshot() as original:
            publish(path, 20)
            assert definition_store.catalog() is original
            with definition_store.definition_snapshot() as nested:
                assert nested is original
                assert assessed_runewords()['Fixture']['roll_ranges']['9']['min'] == 10
            raise RuntimeError('assessment interrupted')

    with pytest.raises(RuntimeError, match='assessment interrupted'):
        interrupted_assessment()
    assert assessed_runewords()['Fixture']['roll_ranges']['9']['min'] == 20
