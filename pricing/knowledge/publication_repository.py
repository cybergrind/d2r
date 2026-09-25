"""Cached immutable runtimes with last-good handling for failed publication updates."""

import json
from dataclasses import dataclass
from pathlib import Path
from threading import RLock

from pricing.knowledge.definition_store import fingerprint
from pricing.knowledge.publication import current_generation
from pricing.knowledge.published_runtime import LoadedRuntime, load_runtime


@dataclass(frozen=True)
class RuntimeLoad:
    runtime: LoadedRuntime | None
    issues: tuple[str, ...] = ()


class PublicationRepository:
    def __init__(self, store):
        self.store = Path(store)
        self._current = None
        self._index_signature = None
        self._seen = None
        self._issues = ()
        self._lock = RLock()

    def _usable(self):
        if self._current is None:
            return False
        try:
            return fingerprint(self._current.database.stat()) == self._index_signature
        except OSError:
            return False

    def load(self):
        with self._lock:
            try:
                raw = (self.store / 'current.json').read_bytes()
                usable = self._usable()
                if raw == self._seen and usable:
                    return RuntimeLoad(self._current, self._issues)
                pointer = json.loads(raw)
                if usable and pointer.get('generation') == self._current.generation:
                    self._seen, self._issues = raw, ()
                    return RuntimeLoad(self._current)
                bundle = current_generation(self.store)
                before = fingerprint(bundle.database.stat())
                loaded = load_runtime(bundle)
                if before != fingerprint(bundle.database.stat()):
                    raise ValueError('Published index changed during runtime loading')
                self._current, self._index_signature = loaded, before
                self._seen, self._issues = raw, ()
                return RuntimeLoad(loaded)
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                self._issues = (f'Publication update unavailable: {error}',)
                if 'raw' in locals():
                    self._seen = raw
                # Parsed artifact bytes remain pinned in memory. The index is
                # still a file, so a changed/deleted old index cannot be reused.
                return RuntimeLoad(self._current if self._usable() else None, self._issues)
