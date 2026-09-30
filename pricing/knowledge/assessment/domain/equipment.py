"""Explicit equipped-slot snapshots; omission means unknown, null means empty.

Accept ItemFacts or their JSON form. These facts must describe equipment in the
supplied loadout; a hover, name list or inventory capture does not populate them.
"""

from collections.abc import Mapping
from dataclasses import fields
from types import MappingProxyType

from pricing.knowledge.assessment.domain.facts import Fact, FactStatus, ItemFacts


EQUIPMENT_CONTEXT_FIELDS = frozenset({'player_equipment', 'mercenary_equipment', 'player_swap_equipment'})
EQUIPMENT_SLOTS = frozenset(
    {'head', 'body', 'weapon', 'off_hand', 'gloves', 'belt', 'boots', 'amulet', 'ring_left', 'ring_right'}
)
STRING_FIELDS = ('name', 'base_name', 'base_code', 'item_type', 'rarity', 'runeword', 'socket_contents')


def item_snapshot(value):
    if isinstance(value, Fact):
        if value.status != FactStatus.KNOWN:
            return Fact(None, FactStatus.UNKNOWN, 'equipped_slot')
        value = value.value
    if value is None:
        return Fact(None, FactStatus.KNOWN, 'equipped_slot')
    if isinstance(value, ItemFacts):
        value = value.to_dict()
    if not isinstance(value, Mapping) or set(value) - {f.name for f in fields(ItemFacts)}:
        return Fact(None, FactStatus.UNKNOWN, 'equipped_slot')
    stats = value.get('stats', {})
    gaps = value.get('gaps', [])
    if (
        not isinstance(stats, Mapping)
        or any(not isinstance(k, str) or not isinstance(v, Mapping) for k, v in stats.items())
        or not isinstance(gaps, (list, tuple))
        or any(not isinstance(g, str) for g in gaps)
    ):
        return Fact(None, FactStatus.UNKNOWN, 'equipped_slot')
    normalized = {
        key: value.get(key) if type(value.get(key)) is str and value[key].strip() else None for key in STRING_FIELDS
    }
    normalized.update(
        {key: value.get(key) if type(value.get(key)) is bool else None for key in ('identified', 'ethereal')}
    )
    for key in ('sockets', 'filled_sockets', 'empty_sockets'):
        count = value.get(key)
        normalized[key] = count if type(count) is int and 0 <= count <= 6 else None
    children = value.get('socket_items', [])
    if not isinstance(children, (list, tuple)) or any(not isinstance(c, Mapping) for c in children):
        return Fact(None, FactStatus.UNKNOWN, 'equipped_slot')
    for child in children:
        child_stats = child.get('stats', {})
        if not isinstance(child_stats, Mapping) or any(
            not isinstance(key, str) or not isinstance(row, Mapping) for key, row in child_stats.items()
        ):
            return Fact(None, FactStatus.UNKNOWN, 'equipped_slot')
    item = ItemFacts(
        **normalized,
        socket_items=children,
        capture_complete=value.get('capture_complete') is True,
        stats=dict(stats),
        gaps=list(gaps),
        item_level=value.get('item_level'),
    )
    return Fact(item, FactStatus.KNOWN, 'equipped_slot')


def equipment_snapshot(value):
    if not isinstance(value, Mapping) or any(slot not in EQUIPMENT_SLOTS for slot in value):
        return None
    return MappingProxyType({slot: item_snapshot(item) for slot, item in value.items()})
