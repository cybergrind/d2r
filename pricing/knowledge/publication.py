"""Stage an offline index and its sources, then atomically publish one pointer.

This storage layer validates byte/index consistency. Callers supply policy/schema
validation before promotion and must include non-indexed runtime inputs explicitly.
Generation directories are never overwritten or removed by publication.
"""

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from pricing.knowledge.artifacts import _read
from pricing.knowledge.index import index_status
from pricing.knowledge.snapshot import read_snapshot


DEFAULT_STORE = Path(__file__).resolve().parents[2] / 'pricing/data/generations'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


@dataclass(frozen=True)
class PublishedGeneration:
    directory: Path
    generation: str
    artifacts: object

    @property
    def database(self):
        return self.directory / 'index.sqlite3'

    def artifact(self, relative):
        # Only manifest-listed paths can be resolved.
        return self.directory / 'artifacts' / self.artifacts[relative]['path']


def _load(directory, expected=None):
    manifest = json.loads((directory / 'manifest.json').read_bytes())
    generation = manifest.pop('generation')
    if manifest.get('schema_version') != 1 or digest(encoded(manifest)) != generation:
        raise ValueError('Invalid publication generation manifest')
    if expected is not None and generation != expected:
        raise ValueError('Publication generation differs from pointer')
    for name, entry in manifest['artifacts'].items():
        path = Path(entry['path'])
        if path.is_absolute() or '..' in path.parts or str(path) != name:
            raise ValueError('Invalid publication artifact path')
        target = directory / 'artifacts' / path
        if not target.resolve().is_relative_to(directory.resolve()) or digest(target.read_bytes()) != entry['sha256']:
            raise ValueError(f'Publication artifact hash mismatch: {name}')
    if digest((directory / 'index.sqlite3').read_bytes()) != manifest['index_sha256']:
        raise ValueError('Publication index hash mismatch')
    return PublishedGeneration(
        directory,
        generation,
        MappingProxyType({k: MappingProxyType(v) for k, v in manifest['artifacts'].items()}),
    )


def current_generation(store):
    store = Path(store)
    pointer = json.loads((store / 'current.json').read_bytes())
    generation = pointer.get('generation')
    if not isinstance(generation, str) or not re.fullmatch(r'[0-9a-f]{64}', generation):
        raise ValueError('Invalid publication generation pointer')
    directory = store / 'generations' / generation
    if not directory.resolve().is_relative_to(store.resolve()):
        raise ValueError('Publication generation escapes store')
    return _load(directory, generation)


def publish(database, *, repository, store, extra_paths=(), validate=None):
    repository, store = Path(repository).resolve(), Path(store).resolve()
    generations = store / 'generations'
    generations.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.stage-', dir=store) as temporary:
        stage = Path(temporary)
        staged_database = stage / 'index.sqlite3'
        with read_snapshot(database) as source, sqlite3.connect(staged_database) as target:
            source.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Publication index integrity check failed')
        sources = index_status(staged_database)['sources']
        expected = {Path(row['path']).resolve(): row['sha256'] for row in sources}
        paths = set(expected) | {Path(p).resolve() for p in extra_paths}
        artifacts = {}
        for path in sorted(paths):
            relative = path.relative_to(repository).as_posix()
            artifact = _read(path)
            if path in expected and artifact.generation != expected[path]:
                raise ValueError(f'Index source generation mismatch: {relative}')
            target = stage / 'artifacts' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(artifact.data)
            artifacts[relative] = {'path': relative, 'sha256': artifact.generation}
        manifest = {'schema_version': 1, 'index_sha256': digest(staged_database.read_bytes()), 'artifacts': artifacts}
        generation = digest(encoded(manifest))
        (stage / 'manifest.json').write_bytes(encoded({**manifest, 'generation': generation}))
        candidate = _load(stage, generation)
        if validate is not None:
            validate(candidate)
            # A validator must not change the bytes it approved.
            _load(stage, generation)
        destination = generations / generation
        if destination.exists():
            _load(destination, generation)
        else:
            stage.rename(destination)
        with tempfile.NamedTemporaryFile(dir=store, prefix='.pointer-', delete=False) as stream:
            pointer_path = Path(stream.name)
            try:
                stream.write(encoded({'generation': generation}))
                stream.flush()
                os.fsync(stream.fileno())
                os.replace(pointer_path, store / 'current.json')
            finally:
                pointer_path.unlink(missing_ok=True)
    return _load(destination, generation)


def main():
    import argparse

    from pricing.knowledge.__main__ import DEFAULT_DATABASE
    from pricing.knowledge.published_runtime import load_runtime, runtime_inputs

    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE)
    parser.add_argument('--store', type=Path, default=DEFAULT_STORE)
    args = parser.parse_args()
    bundle = publish(
        args.database, repository=repository, store=args.store, extra_paths=runtime_inputs(), validate=load_runtime
    )
    print(
        json.dumps(
            {'generation': bundle.generation, 'artifacts': len(bundle.artifacts), 'database': str(bundle.database)}
        )
    )


if __name__ == '__main__':
    main()
