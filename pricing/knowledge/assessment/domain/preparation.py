"""Hypothetical socket actions, kept separate from observed item facts."""

from dataclasses import dataclass, fields

from pricing.knowledge.assessment.domain.facts import freeze, thaw


@dataclass(frozen=True)
class PreparationOption:
    destination: str
    target_sockets: int
    action: str
    feasibility: str
    preconditions: tuple[str, ...] = ()
    outcomes: tuple = ()
    destroys_contents: bool = False
    resources: tuple = ()
    source: str | None = None
    steps: tuple = ()

    def __post_init__(self):
        object.__setattr__(self, 'preconditions', tuple(self.preconditions))
        object.__setattr__(self, 'outcomes', freeze(self.outcomes))
        object.__setattr__(self, 'resources', freeze(self.resources))
        object.__setattr__(self, 'steps', freeze(self.steps))

    def to_dict(self):
        return {f.name: thaw(getattr(self, f.name)) for f in fields(self) if f.name != 'steps' or self.steps}


@dataclass(frozen=True)
class SocketPreparation:
    status: str
    messages: tuple[str, ...]
    options: tuple[PreparationOption, ...] = ()
