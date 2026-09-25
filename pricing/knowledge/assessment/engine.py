"""Assessment orchestration; utility and trade evidence remain independent."""

from contextlib import nullcontext
from dataclasses import replace

from pricing.knowledge.artifacts import artifact_snapshot
from pricing.knowledge.assessment.adapters.assessment import legacy_payload
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.base_use import assess_runeword_base
from pricing.knowledge.assessment.domain.comparison_requests import ComparisonRequest
from pricing.knowledge.assessment.domain.context import AssessmentContext
from pricing.knowledge.assessment.domain.results import AssessmentGeneration, AssessmentResult
from pricing.knowledge.assessment.ethereal import ethereal_preference
from pricing.knowledge.assessment.handlers import HANDLERS
from pricing.knowledge.assessment.inputs import artifact_inputs
from pricing.knowledge.assessment.mechanics.armor_comparisons import armor_upgrade_requests
from pricing.knowledge.assessment.mechanics.prepared_comparisons import socket_outcome_requests
from pricing.knowledge.assessment.mechanics.upgrade_comparisons import upgrade_outcome_requests
from pricing.knowledge.assessment.mechanics.upgrade_defense import with_defense_outcomes
from pricing.knowledge.assessment.mechanics.upgrades import upgrade_paths
from pricing.knowledge.assessment.policies.leveling import assess_leveling
from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from pricing.knowledge.assessment.profiles import assess_role_results, load_candidates, profile_snapshot
from pricing.knowledge.assessment.registry import classify
from pricing.knowledge.definition_store import definition_snapshot


def assess(extraction, *, profiles=None, loadout=None):
    return legacy_payload(assess_result(extraction, profiles=profiles, loadout=loadout))


def assess_result(extraction, *, profiles=None, loadout=None):
    loadout = AssessmentContext.from_input(loadout)
    with (
        definition_snapshot() as definitions,
        artifact_snapshot(artifact_inputs()) as artifacts,
        profile_snapshot() if profiles is None else nullcontext() as loaded_profiles,
    ):
        result = _assess(extraction, profiles=profiles, loadout=loadout)
        return replace(
            result,
            generation=AssessmentGeneration(
                definitions.generation,
                loaded_profiles.bundle.generation if loaded_profiles and loaded_profiles.bundle else None,
                {str(path): artifact.generation for path, artifact in artifacts.items()},
            ),
        )


def _assess(extraction, *, profiles=None, loadout=None):
    facts = normalize(extraction)
    family, policy = classify(facts)
    if profiles is None:
        profiles, cached_gaps = load_candidates(facts)
        # Per-item diagnostics must never mutate the shared profile cache.
        coverage_gaps = list(cached_gaps)
    else:
        coverage_gaps = []
    contract, gaps = HANDLERS[policy].contract(facts, family)
    upgrades = with_defense_outcomes(facts, contract, upgrade_paths(facts))
    roles = assess_role_results(facts, profiles, loadout, upgrades=upgrades)
    base_uses = assess_runeword_base(facts)
    if not roles:
        coverage_gaps.append('No reviewed build-role profile applies; absence is not evidence of no demand.')
    requests = (
        (
            ComparisonRequest(
                'current',
                'exact_current_variant',
                contract.to_dict(),
                tuple(r.id for r in roles if r.status in ('matched', 'partial')),
            ),
        )
        if contract
        else ()
    )
    requests += socket_outcome_requests(facts, contract, base_uses)
    requests += upgrade_outcome_requests(facts, contract, upgrades)
    requests += armor_upgrade_requests(facts, contract, upgrades)
    return AssessmentResult(
        family=family,
        quality_policy=policy,
        facts=facts,
        roles=roles,
        base_uses=base_uses,
        leveling=assess_leveling(facts, loadout=loadout),
        trade_tier=assess_tier(facts),
        ethereal_preference=ethereal_preference(facts, roles=roles, base_uses=base_uses),
        coverage_gaps=coverage_gaps,
        price_gaps=gaps,
        contract=contract,
        comparison_requests=requests,
        upgrades=upgrades,
    )
