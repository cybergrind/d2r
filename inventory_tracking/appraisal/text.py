"""Compatibility entry points; ItemAssessment owns the shared presentation."""

from inventory_tracking.appraisal.presentation import ItemAssessment, result_tones
from inventory_tracking.appraisal.sections import (
    assessment_lines as assessment_lines,
    base_lines as base_lines,
    price_lines as price_lines,
    unresolved_lines as unresolved_lines,
    value_watch_lines as value_watch_lines,
)
from inventory_tracking.presentation import PALETTE


def format_appraisal(record, frozen=None):
    return ItemAssessment.from_record(record, frozen).to_text()


def roll_styles(record):
    return {text: PALETTE[tone] for text, tone in result_tones(record.get('result', {})).items()}
