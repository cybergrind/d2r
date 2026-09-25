"""Immutable semantic capture facts, independent of storage and presentation."""

from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from enum import StrEnum
from types import MappingProxyType


class FactStatus(StrEnum):
    KNOWN = 'known'
    UNKNOWN = 'unknown'
    NOT_APPLICABLE = 'not_applicable'
    CONFLICTING = 'conflicting'


@dataclass(frozen=True)
class Fact[T]:
    value: T | None
    status: FactStatus
    origin: str = 'observed'


@dataclass(frozen=True)
class StatKey:
    stat_id: int
    parameter: int = 0

    def __str__(self):
        return f'{self.stat_id}:{self.parameter}'


def freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({k: freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(v) for v in value)
    return value


def thaw(value):
    if isinstance(value, Mapping):
        return {k: thaw(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [thaw(v) for v in value]
    return value


@dataclass(frozen=True)
class ItemFacts:
    name: str | None
    base_name: str | None
    base_code: str | None
    item_type: str | None
    rarity: str | None
    runeword: str | None
    identified: bool | None
    ethereal: bool | None
    sockets: int | None
    socket_contents: str | None
    socket_items: list
    capture_complete: bool
    stats: dict = field(default_factory=dict)
    properties: dict = field(default_factory=dict)
    gaps: list = field(default_factory=list)
    projection_gaps: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)

    filled_sockets: int | None = None
    empty_sockets: int | None = None
    item_level: int | None = None

    @property
    def socket_state(self):
        from pricing.knowledge.assessment.domain.sockets import socket_state

        return socket_state(
            self.sockets, self.socket_contents, self.socket_items, self.filled_sockets, self.empty_sockets
        )

    def to_dict(self):
        return {
            f.name: thaw(getattr(self, f.name))
            for f in fields(self)
            if f.name != 'item_level' or self.item_level is not None
        }

    def __post_init__(self):
        if type(self.item_level) is not int or not 1 <= self.item_level <= 99:
            object.__setattr__(self, 'item_level', None)
        for name in ('socket_items', 'stats', 'properties', 'gaps', 'projection_gaps', 'provenance'):
            object.__setattr__(self, name, freeze(getattr(self, name)))

    def fact(self, name):
        if name not in {f.name for f in fields(self)}:
            raise KeyError(name)
        value = getattr(self, name)
        conflicting = (
            name in ('sockets', 'socket_contents') and self.socket_state.total.status == FactStatus.CONFLICTING
        )
        status = FactStatus.CONFLICTING if conflicting else FactStatus.UNKNOWN if value is None else FactStatus.KNOWN
        return Fact(value, status)

    def stat(self, key: StatKey):
        row = self.stats.get(str(key))
        if row is None or row.get('status') != 'decoded':
            return Fact(None, FactStatus.UNKNOWN)
        if f'Duplicate native stat {key}.' in self.gaps:
            return Fact(None, FactStatus.CONFLICTING)
        value = row.get('value')
        return Fact(value, FactStatus.UNKNOWN if value is None else FactStatus.KNOWN, row.get('origin', 'observed'))
