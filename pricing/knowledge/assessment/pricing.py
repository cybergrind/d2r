"""Pure finalization of an assessment with its evaluated market evidence."""

from dataclasses import replace

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.domain.priced import PricedAssessment
from pricing.knowledge.assessment.policies.market_tiers import resolve_market_tier


def finalize_assessment(assessment, results, *, fallback_rows=(), today=None):
    current = next((result for result in results if result.is_current), None)
    comparisons = current.comparisons if current else evaluate(None, fallback_rows)
    estimate = thaw(current.price_estimate) if current else price_from_comparables(comparisons, today=today)
    if (
        estimate.get('unavailable_reason') == 'unclassified'
        and (
            assessment.quality_policy in ('base', 'affixed', 'named', 'runeword')
            or assessment.quality_policy == assessment.family in ('consumable', 'socket_material', 'supply')
        )
        and (
            assessment.facts.capture_complete is not True
            or any(getattr(assessment.facts, field) is None for field in ('ethereal', 'sockets', 'socket_contents'))
        )
    ):
        # No market comparison was possible: this is not an examined cache miss.
        # Retain all price gaps below, including any additional mapping/rule gaps.
        estimate['unavailable_reason'] = 'capture_incomplete'
    tier = resolve_market_tier(assessment.facts, assessment.trade_tier, current)
    unmapped = [gap for gap in assessment.price_gaps if gap.startswith('No verified market mapping')]
    estimate['notes'].extend(gap for gap in assessment.price_gaps if gap not in unmapped)
    if unmapped:
        estimate['notes'].append(
            f'{len(unmapped)} observed modifiers cannot yet be compared to market listings; details in JSON.'
        )
    finalized = tuple(replace(result, price_estimate=estimate) if result is current else result for result in results)
    return PricedAssessment(replace(assessment, trade_tier=tier), finalized, comparisons, estimate)
