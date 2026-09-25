import json

import pytest

from pricing.knowledge import index


def write_source(path, name):
    path.write_text(json.dumps({'schema_version': 1, 'rows': [{'name': name, 'kind': 'demand'}]}))


@pytest.mark.parametrize('timing', ['before_read', 'after_read', 'later_source'])
def test_changed_input_cannot_publish_a_database_with_wrong_source_fingerprint(tmp_path, monkeypatch, timing):
    first, second, database = tmp_path / 'a.json', tmp_path / 'b.json', tmp_path / 'kb.sqlite3'
    write_source(first, 'Original')
    write_source(second, 'Second')
    index.build_index([first, second], database)
    previous = database.read_bytes()
    original_reader = index._read_rows

    def racing_reader(path):
        if timing == 'before_read' and path == first:
            write_source(first, 'Changed')
        yield from original_reader(path)
        if timing == 'after_read' and path == first:
            write_source(first, 'Changed')
        if timing == 'later_source' and path == second:
            write_source(first, 'Changed')

    monkeypatch.setattr(index, '_read_rows', racing_reader)
    with pytest.raises(ValueError, match='changed during'):
        index.build_index([first, second], database)
    assert database.read_bytes() == previous
    assert not list(tmp_path.glob('.appraisal-*.sqlite3'))
