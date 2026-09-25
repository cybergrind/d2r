"""Shared immutable definition generations, reloaded after offline publication."""

import hashlib
import json
import os
from collections.abc import Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from threading import RLock

from pricing.knowledge.assessment.domain.facts import freeze


def fingerprint(stat):
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


@dataclass(frozen=True)
class DefinitionCatalog:
    generation: str
    named: Mapping
    runewords: Mapping
    named_variants: Mapping


class DefinitionStore:
    def __init__(self, path):
        self.path = Path(path)
        self._signature = None
        self._catalog = None
        self._lock = RLock()

    def load(self):
        with self._lock:
            signature = fingerprint(self.path.stat())
            if signature == self._signature:
                return self._catalog
            with self.path.open('rb') as stream:
                before = fingerprint(os.fstat(stream.fileno()))
                raw = stream.read()
                if before != fingerprint(os.fstat(stream.fileno())):
                    raise ValueError('Definitions changed while reading')
            document = json.loads(raw)
            if document.get('schema_version') != 1 or not isinstance(document.get('rows'), list):
                raise ValueError('Unsupported definitions schema')
            named, runewords, variants = {}, {}, {}
            for row in document['rows']:
                quality = row.get('rarity')
                if quality not in ('unique', 'set', 'runeword'):
                    continue
                key = row['name'] if quality == 'runeword' else (quality, row['name'])
                target = runewords if quality == 'runeword' else named
                if quality == 'runeword' and key in target and target[key] != row:
                    raise ValueError(f'Conflicting runeword definition: {key}')
                if quality != 'runeword':
                    variants.setdefault(key, []).append(row)
                # Preserve existing last-record named lookup semantics (legacy
                # identities such as Azurewrath have multiple table versions).
                # All variants remain available for the identity migration.
                target[key] = row
            result = DefinitionCatalog(
                hashlib.sha256(raw).hexdigest(), freeze(named), freeze(runewords), freeze(variants)
            )
            self._catalog, self._signature = result, before
            return result


STORE = DefinitionStore(Path(__file__).resolve().parents[1] / 'data/appraisal-definitions.json')


_PINNED = ContextVar('appraisal_definition_catalog', default=None)


def catalog():
    pinned = _PINNED.get()
    return pinned if pinned is not None else STORE.load()


@contextmanager
def definition_snapshot(current=None):
    current = catalog() if current is None else current
    token = _PINNED.set(current)
    try:
        yield current
    finally:
        _PINNED.reset(token)
