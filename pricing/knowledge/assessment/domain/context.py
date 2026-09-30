"""Immutable optional loadout facts; malformed input never proves a role mismatch."""

from collections.abc import Mapping
from dataclasses import dataclass, fields

from pricing.knowledge.assessment.domain.equipment import EQUIPMENT_CONTEXT_FIELDS, equipment_snapshot
from pricing.knowledge.assessment.domain.facts import Fact, FactStatus


COLLECTION_CONTEXT_FIELDS = frozenset({'player_items', 'mercenary_items', 'player_swap_items'})

NUMERIC_CONTEXT_FIELDS = frozenset(
    {
        'player_level',
        'player_strength',
        'player_dexterity',
        'player_total_fcr',
        'player_total_fhr',
        'mercenary_level',
        'mercenary_strength',
        'mercenary_dexterity',
    }
)


@dataclass(frozen=True)
class AssessmentContext:
    player_class: str | None = None
    player_level: int | None = None
    player_strength: int | None = None
    player_dexterity: int | None = None
    player_items: tuple[str, ...] | frozenset[str] | None = None
    mercenary_type: str | None = None
    mercenary_level: int | None = None
    mercenary_strength: int | None = None
    mercenary_dexterity: int | None = None
    mercenary_items: tuple[str, ...] | frozenset[str] | None = None
    # Explicit total for the assessed loadout, never inferred from a hover.
    player_total_fcr: int | None = None
    # Explicit intended encounter/activity; never inferred from gear or mercenary type.
    activity: str | None = None
    # Explicit recovery total for this loadout; a hovered item cannot supply it.
    player_total_fhr: int | None = None
    # Equipment on the alternate weapon set, not inventory or the active set.
    player_swap_items: tuple[str, ...] | frozenset[str] | None = None

    # Explicit slot facts, separate from name-only membership and hovered inventory.
    player_equipment: Mapping | None = None
    mercenary_equipment: Mapping | None = None
    player_swap_equipment: Mapping | None = None

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name in EQUIPMENT_CONTEXT_FIELDS:
                value = equipment_snapshot(value)
            elif field.name in COLLECTION_CONTEXT_FIELDS:
                valid = isinstance(value, (list, tuple, set, frozenset)) and all(
                    type(item) is str and bool(item.strip()) for item in value
                )
                # Sequences record actual copies; sets establish membership only.
                value = (
                    (frozenset(value) if isinstance(value, (set, frozenset)) else tuple(sorted(value)))
                    if valid
                    else None
                )
            elif field.name in NUMERIC_CONTEXT_FIELDS:
                value = value if type(value) is int and value >= 0 else None
            else:
                value = value if type(value) is str and value.strip() else None
            object.__setattr__(self, field.name, value)

    @classmethod
    def from_input(cls, value):
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            return cls()
        return cls(**{field.name: value.get(field.name) for field in fields(cls)})

    def fact(self, name):
        if name not in CONTEXT_FIELDS:
            raise KeyError(name)
        value = getattr(self, name)
        return Fact(value, FactStatus.UNKNOWN if value is None else FactStatus.KNOWN, 'loadout')


CONTEXT_FIELDS = frozenset(field.name for field in fields(AssessmentContext))
