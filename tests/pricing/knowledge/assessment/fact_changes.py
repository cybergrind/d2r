"""Typed field changes for `dataclasses.replace` on `ItemFacts` in tests."""

from collections.abc import Mapping, Sequence
from typing import TypedDict


class FactChanges(TypedDict, total=False):
    """Any subset of `ItemFacts` fields, typed as the dataclass declares them."""

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
    socket_items: Sequence
    capture_complete: bool
    stats: Mapping
    properties: Mapping
    gaps: Sequence
    projection_gaps: Sequence
    provenance: Mapping
    filled_sockets: int | None
    empty_sockets: int | None
    item_level: int | None
    native_affixes: dict | None


def fact_changes(*changes: FactChanges) -> tuple[FactChanges, ...]:
    """The changes in order; the call types each dict literal as `FactChanges`."""
    return changes
