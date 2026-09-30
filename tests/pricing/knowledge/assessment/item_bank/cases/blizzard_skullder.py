"""Blizzard Body Armor/4: Skullder skill/MF utility and observed self-repair."""

from tests.pricing.knowledge.assessment.item_bank.cases.hammer_mf_armor import SPECS, cases


_, ITEM, KEYS = SPECS[0]
CASES = tuple(
    cases(
        build='blizzard-sorceress',
        player_class='Sorceress',
        prefix='blizzard',
        specs=(('skullder-body-armor-utility-alternative', ITEM, KEYS),),
    )
)
