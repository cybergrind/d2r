"""Immutable artifact bytes scoped to one appraisal, without global stale reads."""

import hashlib
import io
import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from pricing.knowledge.definition_store import fingerprint


@dataclass(frozen=True)
class Artifact:
    data: bytes
    generation: str


@dataclass(frozen=True)
class LazyArtifact:
    """An artifact hash-checked once and then read from its file when asked: held as its hash and the file's stamp,
    not its bytes (the market is 187 MB, and a runtime held it for as long as it lived). A file whose stamp
    changed since the check is refused, as `_read` refuses a file that changes while it is read."""

    path: Path
    generation: str
    stamp: tuple[int, ...]

    @property
    def data(self) -> bytes:
        artifact = _read(self.path)
        if artifact.generation != self.generation:
            raise ValueError(f'Offline artifact changed since it was checked: {self.path}')
        return artifact.data

    def lines(self) -> Iterator[bytes]:
        with self.path.open('rb') as stream:
            if fingerprint(os.fstat(stream.fileno())) != self.stamp:
                raise ValueError(f'Offline artifact changed since it was checked: {self.path}')
            yield from stream
            if fingerprint(os.fstat(stream.fileno())) != self.stamp:
                raise ValueError(f'Offline artifact changed while reading: {self.path}')


CHUNK = 1 << 20  # bytes hashed at a time by `lazy_artifact`


def lazy_artifact(path) -> LazyArtifact:
    """`path` hash-checked a chunk at a time, nothing of it kept."""
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        stamp = fingerprint(os.fstat(stream.fileno()))
        while chunk := stream.read(CHUNK):
            digest.update(chunk)
        if stamp != fingerprint(os.fstat(stream.fileno())) or stamp != fingerprint(path.stat()):
            raise ValueError(f'Offline artifact changed while reading: {path}')
    return LazyArtifact(path, digest.hexdigest(), stamp)


_PINNED: ContextVar[Mapping[Path, Any] | None] = ContextVar('appraisal_artifacts', default=None)
_STRICT = ContextVar('appraisal_artifacts_strict', default=False)


def _read(path):
    with path.open('rb') as stream:
        before = fingerprint(os.fstat(stream.fileno()))
        raw = stream.read()
        if before != fingerprint(os.fstat(stream.fileno())) or before != fingerprint(path.stat()):
            raise ValueError(f'Offline artifact changed while reading: {path}')
    return Artifact(raw, hashlib.sha256(raw).hexdigest())


def _pinned(path):
    """The pinned artifact of `path` (resolved), None for a path read from the working tree."""
    pinned = _PINNED.get()
    if _STRICT.get() and (pinned is None or path not in pinned):
        raise ValueError(f'Artifact absent from pinned publication: {path}')
    return pinned[path] if pinned is not None and path in pinned else None


def read_artifact(path):
    path = Path(path).resolve()
    artifact = _pinned(path)
    return artifact.data if artifact is not None else _read(path).data


def artifact_generation(path) -> str:
    """The sha256 of `path`'s bytes as `read_artifact` would give them, without keeping them."""
    path = Path(path).resolve()
    artifact = _pinned(path)
    return artifact.generation if artifact is not None else lazy_artifact(path).generation


def artifact_lines(path) -> Iterator[bytes]:
    """`path`'s lines as `read_artifact` would give its bytes, read a line at a time from a lazy or working-tree
    file; each line keeps its line end."""
    path = Path(path).resolve()
    artifact = _pinned(path)
    if isinstance(artifact, LazyArtifact):
        yield from artifact.lines()
    elif artifact is not None:
        yield from io.BytesIO(artifact.data)
    else:
        with path.open('rb') as stream:
            yield from stream


@contextmanager
def artifact_snapshot(paths):
    pinned: dict[Path, Any] = dict(_PINNED.get() or {})
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
