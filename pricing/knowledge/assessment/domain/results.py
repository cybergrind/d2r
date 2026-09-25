"""Immutable assessment outcomes before market retrieval and presentation."""

from collections.abc import Mapping
from dataclasses import dataclass, field

from pricing.knowledge.assessment.domain.comparison_requests import ComparisonRequest
from pricing.knowledge.assessment.domain.contracts import ComparableContract
from pricing.knowledge.assessment.domain.facts import ItemFacts, freeze
from pricing.knowledge.assessment.domain.roles import RoleAssessment
from pricing.knowledge.assessment.domain.upgrades import UpgradePath
from pricing.knowledge.assessment.stat_evaluation import StatEvaluation


@dataclass(frozen=True)
class AssessmentGeneration:
    definitions: str | None = None
    profiles: str | None = None
    artifacts: Mapping = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, 'artifacts', freeze(self.artifacts))


@dataclass(frozen=True)
class AssessmentResult:
    family: str
    quality_policy: str
    facts: ItemFacts
    roles: tuple[RoleAssessment, ...]
    base_uses: tuple[Mapping, ...]
    leveling: tuple[Mapping, ...]
    trade_tier: Mapping
    ethereal_preference: Mapping
    coverage_gaps: tuple[str, ...]
    price_gaps: tuple[str, ...]
    contract: ComparableContract | None
    comparison_requests: tuple[ComparisonRequest, ...]
    generation: AssessmentGeneration = field(default_factory=AssessmentGeneration)
    upgrades: tuple[UpgradePath, ...] = ()
    stat_evaluation: StatEvaluation | None = None

    def __post_init__(self):
        for name in (
            'roles',
            'base_uses',
            'leveling',
            'trade_tier',
            'ethereal_preference',
            'coverage_gaps',
            'price_gaps',
            'comparison_requests',
            'upgrades',
        ):
            object.__setattr__(self, name, freeze(getattr(self, name)))
