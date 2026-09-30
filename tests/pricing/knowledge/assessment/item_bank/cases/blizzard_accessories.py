"""Blizzard's explicit farming/defensive alternatives; attack speed and leech are not spell utility."""

from tests.pricing.knowledge.assessment.item_bank.cases.berserk_defensive_accessories import (
    SPECS as DEFENSIVE,
    cases as defensive_cases,
)
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_farming_accessories import cases as farming_cases
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_bk_ring import cases as bk_cases
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_farming_accessories import SPECS_FOR_CASTER


CASES = (
    *defensive_cases('blizzard-sorceress', 'Sorceress', 'blizzard', specs=DEFENSIVE[:1]),
    *farming_cases('blizzard-sorceress', 'Sorceress', 'blizzard', specs=SPECS_FOR_CASTER, excluded=('79:0', '93:0')),
    *bk_cases('blizzard-sorceress', 'Sorceress', 'blizzard', source_index=1),
)
