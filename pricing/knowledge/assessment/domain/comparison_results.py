"""Immutable market outcomes with separate observed and prepared estimates."""

from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Literal

from pricing.knowledge.assessment.domain.facts import freeze


@dataclass(frozen=True)
class ComparisonResult:
    request_id: str
    segment_id: str
    contract: Mapping
    role_ids: tuple[str, ...]
    state: Literal['observed', 'prepared']
    policy_version: int
    request_ids: tuple[str, ...]
    comparisons: Mapping
    price_estimate: Mapping
    preparation: Mapping | None = None
    outcome_comparisons: Mapping | None = None
    outcome_ask_estimate: Mapping | None = None

    def __post_init__(self):
        for field in fields(self):
            object.__setattr__(self, field.name, freeze(getattr(self, field.name)))

    @property
    def is_current(self):
        return self.state == 'observed' and 'current' in self.request_ids
