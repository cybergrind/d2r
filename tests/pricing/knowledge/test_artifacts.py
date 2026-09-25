import pytest


def test_artifact_snapshot_keeps_bytes_and_nested_generation_until_scope_exits(tmp_path):
    from pricing.knowledge.artifacts import artifact_snapshot, read_artifact

    path = tmp_path / 'catalog.json'
    path.write_bytes(b'old')

    def interrupted():
        with artifact_snapshot([path]) as snapshot:
            original = snapshot[path.resolve()]
            path.write_bytes(b'new')
            assert read_artifact(path) == b'old'
            with artifact_snapshot([path]) as nested:
                assert nested[path.resolve()] is original
            raise RuntimeError('interrupted')

    with pytest.raises(RuntimeError, match='interrupted'):
        interrupted()
    assert read_artifact(path) == b'new'
