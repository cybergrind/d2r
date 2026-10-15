"""Market evidence read a row at a time (user, 2026-10-15): `appraisal-market.jsonl` is 187 MB and about 1.1 GB once
parsed whole, so a reader parses only the rows it keeps. Every row begins `{"id":"<id>",` (refresh.py writes them
so), which gives a row's id without parsing it, and its name follows its kind: a reader that wants some names
parses only their rows. A row that begins otherwise is parsed for its id or name."""

import hashlib
import io
import json
import re
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any

from pricing.knowledge.artifacts import artifact_generation, artifact_lines, lazy_artifact
from pricing.knowledge.names import normalize_name


ROW_ID = re.compile(rb'\{"id":"([^"\\]*)"')
ROW_NAME = re.compile(rb'\{"id":"[^"\\]*","kind":"[^"\\]*","name":"((?:[^"\\]|\\.)*)"')


def row_id(line: bytes) -> str:
    found = ROW_ID.match(line)
    return found.group(1).decode() if found else json.loads(line)['id']


def row_name(line: bytes) -> object:
    found = ROW_NAME.match(line)
    return json.loads(b'"' + found.group(1) + b'"') if found else json.loads(line).get('name')


@dataclass(frozen=True)
class Market:
    """One market file: its sha256, and its lines read anew whenever its rows are asked for. Equal and hashed by the
    sha256 alone, so a cache keyed by it keeps no bytes."""

    sha256: str
    lines: Callable[[], Iterable[bytes]] = field(compare=False, repr=False)

    def rows(self) -> Iterator[dict[str, Any]]:
        for line in self.lines():
            if line.strip():
                yield json.loads(line)

    def with_ids(self, ids: Iterable[str]) -> list[dict[str, Any]]:
        """The rows whose id is one of `ids`, in the file's order; only those are parsed."""
        wanted = set(ids)
        return [json.loads(line) for line in self.lines() if line.strip() and row_id(line) in wanted]

    def named(self, names: Iterable[object]) -> list[dict[str, Any]]:
        """The rows whose name is one of `names` once normalized (`normalize_name`), in the file's order; only those
        are parsed."""
        wanted = {normalize_name(name) for name in names}
        return [json.loads(line) for line in self.lines() if line.strip() and normalize_name(row_name(line)) in wanted]


def market_of(raw: bytes) -> Market:
    """A market from bytes in hand (a test's own rows)."""
    return Market(hashlib.sha256(raw).hexdigest(), lambda: io.BytesIO(raw))


def file_market(path) -> Market:
    """The working tree's market at `path`: hash-checked a chunk at a time, then read a line at a time, refused if
    the file changes in between (artifacts.py LazyArtifact)."""
    artifact = lazy_artifact(path)
    return Market(artifact.generation, artifact.lines)


def published_market(path) -> Market:
    """The market at `path` as `read_artifact` would give it: the pinned publication's under a published snapshot,
    read a line at a time and never held whole."""
    return Market(artifact_generation(path), lambda: artifact_lines(path))
