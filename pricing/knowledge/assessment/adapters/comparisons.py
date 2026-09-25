"""Mutable report projection of immutable comparison results."""

from dataclasses import fields

from pricing.knowledge.assessment.domain.comparison_results import ComparisonResult
from pricing.knowledge.assessment.domain.facts import thaw


def legacy_comparison(result: ComparisonResult):
    return {
        field.name: thaw(getattr(result, field.name))
        for field in fields(result)
        if getattr(result, field.name) is not None
    }


def legacy_comparisons(results):
    return [legacy_comparison(result) for result in results]
