"""Immutable build-role judgments owned by the assessment domain."""

from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Literal

from pricing.knowledge.assessment.domain.facts import freeze


@dataclass(frozen=True)
class RoleAssessment:
    id: str
    build: str
    variant: str
    side: str
    slot: str
    role: str
    review_status: str
    source: Mapping
    status: Literal['unknown', 'failed', 'partial', 'matched']
    rule_trace: Mapping | None
    skill_trace: Mapping | None
    dependencies: tuple[Mapping, ...]
    equipment: Mapping | None
    ethereal_preference: Mapping | None
    preferences: tuple[Mapping, ...]
    matched: tuple[str, ...]
    missing: tuple[str, ...]
    failed: tuple[str, ...]
    important_rolls: tuple[Mapping, ...]
    alternatives: tuple[str, ...]

    def __post_init__(self):
        for field in fields(self):
            object.__setattr__(self, field.name, freeze(getattr(self, field.name)))
