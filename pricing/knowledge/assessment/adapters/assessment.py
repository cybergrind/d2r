"""One compatibility projection from typed assessment outcomes; no evaluation."""

from pricing.knowledge.assessment.adapters.roles import legacy_roles
from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.domain.results import AssessmentResult


def legacy_payload(result: AssessmentResult):
    return {
        'version': 1,
        'family': result.family,
        'quality_policy': result.quality_policy,
        'facts': result.facts.to_dict(),
        'roles': legacy_roles(result.roles),
        'base_uses': thaw(result.base_uses),
        'leveling': thaw(result.leveling),
        'trade_tier': thaw(result.trade_tier),
        'ethereal_preference': thaw(result.ethereal_preference),
        'coverage_gaps': thaw(result.coverage_gaps),
        'price_gaps': thaw(result.price_gaps),
        'contract': result.contract.to_dict() if result.contract else None,
        'comparison_requests': [request.to_dict() for request in result.comparison_requests],
        'definition_generation': result.generation.definitions,
        'profile_generation': result.generation.profiles,
        'artifact_generations': thaw(result.generation.artifacts),
        **({'upgrade_paths': [path.to_dict() for path in result.upgrades]} if result.upgrades else {}),
    }
