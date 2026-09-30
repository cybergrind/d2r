"""Bounded exclusions for exact embedded tooltips in explicitly Hardcore advice."""

from pricing.knowledge.assessment.maintenance.embedded_evidence import _read_pin
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.hardcore_bounds import validate_hardcore_bounds


def validate_hardcore_review(review, root):
    if any(key in review for key in ('profile_id', 'profile_fingerprint', 'use_fingerprint')):
        raise ValueError('Hardcore embedded exclusion cannot endorse a Softcore role')
    evidence = review['evidence']
    guide = section_inventory(_read_pin(evidence['guide'], root))
    validate_hardcore_bounds(guide['sections'], review['section_range'], evidence['reference']['position'])
