"""Immutable assessment after current and prepared market evaluation."""

from collections.abc import Mapping
from dataclasses import dataclass

from pricing.knowledge.assessment.domain.comparison_results import ComparisonResult
from pricing.knowledge.assessment.domain.facts import freeze
from pricing.knowledge.assessment.domain.results import AssessmentResult


@dataclass(frozen=True)
class PricedAssessment:
    assessment: AssessmentResult
    comparison_results: tuple[ComparisonResult, ...]
    comparisons: Mapping
    price_estimate: Mapping

    def __post_init__(self):
        object.__setattr__(self, 'comparison_results', tuple(self.comparison_results))
        object.__setattr__(self, 'comparisons', freeze(self.comparisons))
        object.__setattr__(self, 'price_estimate', freeze(self.price_estimate))

    @property
    def current(self):
        return next((result for result in self.comparison_results if result.is_current), None)
