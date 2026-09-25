"""Immutable artifact bytes scoped to one appraisal, without global stale reads."""

import hashlib
import os
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from pricing.knowledge.definition_store import fingerprint


@dataclass(frozen=True)
class Artifact:
    data: bytes
    generation: str


_PINNED = ContextVar('appraisal_artifacts', default=None)
_STRICT = ContextVar('appraisal_artifacts_strict', default=False)


def _read(path):
    with path.open('rb') as stream:
        before = fingerprint(os.fstat(stream.fileno()))
        raw = stream.read()
        if before != fingerprint(os.fstat(stream.fileno())) or before != fingerprint(path.stat()):
            raise ValueError(f'Offline artifact changed while reading: {path}')
    return Artifact(raw, hashlib.sha256(raw).hexdigest())


def read_artifact(path):
    path = Path(path).resolve()
    pinned = _PINNED.get()
    if _STRICT.get() and (pinned is None or path not in pinned):
        raise ValueError(f'Artifact absent from pinned publication: {path}')
    return pinned[path].data if pinned is not None and path in pinned else _read(path).data


@contextmanager
def artifact_snapshot(paths):
    pinned = dict(_PINNED.get() or {})
    for value in paths:
        path = Path(value).resolve()
        if path not in pinned:
            if _STRICT.get():
                raise ValueError(f'Artifact absent from pinned publication: {path}')
            pinned[path] = _read(path)
    snapshot = MappingProxyType(pinned)
    token = _PINNED.set(snapshot)
    try:
        yield snapshot
    finally:
        _PINNED.reset(token)


@contextmanager
def supplied_artifacts(mapping):
    """Use an explicit complete bundle; never fall back to working-tree files."""
    token = _PINNED.set(MappingProxyType(dict(mapping)))
    strict = _STRICT.set(True)
    try:
        yield
    finally:
        _STRICT.reset(strict)
        _PINNED.reset(token)
