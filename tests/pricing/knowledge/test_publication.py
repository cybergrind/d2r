import json

import pytest

from pricing.knowledge.index import build_index, index_status
from pricing.knowledge.publication import current_generation, publish


def fixture(tmp_path, value):
    source = tmp_path / 'source.json'
    source.write_text(json.dumps({'schema_version': 1, 'rows': [{'kind': 'catalog', 'name': value}]}))
    database = tmp_path / 'kb.sqlite3'
    build_index([source], database)
    return source, database


def test_publication_pins_old_generation_and_includes_extra_rules(tmp_path):
    _, database = fixture(tmp_path, 'old')
    rules = tmp_path / 'rules.json'
    rules.write_text('{"version": 1}')
    store = tmp_path / 'published'
    old = publish(database, repository=tmp_path, store=store, extra_paths=[rules])
    _, database = fixture(tmp_path, 'new')
    rules.write_text('{"version": 2}')
    new = publish(database, repository=tmp_path, store=store, extra_paths=[rules])
    assert current_generation(store).generation == new.generation != old.generation
    assert json.loads(old.artifact('source.json').read_text())['rows'][0]['name'] == 'old'
    assert json.loads(old.artifact('rules.json').read_text())['version'] == 1
    assert index_status(old.database)['sources'][0]['sha256'] != index_status(new.database)['sources'][0]['sha256']


def test_changed_index_source_or_validation_failure_preserves_current(tmp_path):
    source, database = fixture(tmp_path, 'old')
    store = tmp_path / 'published'
    old = publish(database, repository=tmp_path, store=store)
    source.write_text('{"schema_version": 1, "rows": []}')
    with pytest.raises(ValueError, match='source generation'):
        publish(database, repository=tmp_path, store=store)
    assert current_generation(store).generation == old.generation
    _, database = fixture(tmp_path, 'new')

    def reject(bundle):
        assert bundle.database.is_file()
        raise ValueError('invalid policy')

    with pytest.raises(ValueError, match='invalid policy'):
        publish(database, repository=tmp_path, store=store, validate=reject)
    assert current_generation(store).generation == old.generation


def test_tampered_generation_and_unsafe_pointer_fail_closed(tmp_path):
    _, database = fixture(tmp_path, 'old')
    store = tmp_path / 'published'
    bundle = publish(database, repository=tmp_path, store=store)
    bundle.artifact('source.json').write_text('tampered')
    with pytest.raises(ValueError, match='hash'):
        current_generation(store)
    (store / 'current.json').write_text('{"generation": "../outside"}')
    with pytest.raises(ValueError, match='generation'):
        current_generation(store)
