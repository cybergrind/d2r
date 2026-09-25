"""Report projection of the complete assessment and market result."""

from pricing.knowledge.assessment.adapters.assessment import legacy_payload
from pricing.knowledge.assessment.adapters.comparisons import legacy_comparisons
from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.domain.priced import PricedAssessment


def legacy_priced_payload(result: PricedAssessment):
    assessment = legacy_payload(result.assessment)
    assessment['comparison_results'] = legacy_comparisons(result.comparison_results)
    assessment['comparisons'] = thaw(result.comparisons)
    return {'assessment': assessment, 'price_estimate': thaw(result.price_estimate)}
