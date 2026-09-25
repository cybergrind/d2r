"""Legal hypothetical upgrade routes, not recommendations or market contracts."""

from collections.abc import Mapping
from dataclasses import dataclass, fields

from pricing.knowledge.assessment.domain.facts import freeze, thaw


@dataclass(frozen=True)
class UpgradePath:
    source_code: str
    target_code: str
    target_name: str
    steps: tuple
    preconditions: tuple[str, ...] = ('horadric_cube', 'ingredients_available', 'wearer_requirements')
    changed: tuple[str, ...] = ('base', 'base_damage_or_defense', 'requirements')
    preserved: tuple[str, ...] = ('identity', 'quality', 'modifiers', 'ethereal', 'sockets', 'socket_contents')
    defense_outcome: Mapping | None = None

    def __post_init__(self):
        object.__setattr__(self, 'steps', freeze(self.steps))
        object.__setattr__(self, 'defense_outcome', freeze(self.defense_outcome))

    def to_dict(self):
        return {
            f.name: thaw(getattr(self, f.name))
            for f in fields(self)
            if f.name != 'defense_outcome' or self.defense_outcome is not None
        }
