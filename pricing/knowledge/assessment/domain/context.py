"""Immutable optional loadout facts; malformed input never proves a role mismatch."""

from collections.abc import Mapping
from dataclasses import dataclass, fields

from pricing.knowledge.assessment.domain.facts import Fact, FactStatus


NUMERIC_CONTEXT_FIELDS = frozenset(
    {
        'player_level',
        'player_strength',
        'player_dexterity',
        'player_total_fcr',
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

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name.endswith('_items'):
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
