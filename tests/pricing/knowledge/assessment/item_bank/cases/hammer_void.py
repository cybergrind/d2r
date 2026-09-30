"""Hammerdin Void alternative: legal daggers and native low-roll casting utility."""

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_void import cases


CASES = tuple(
    cases(
        'blessed-hammer-paladin',
        'Paladin',
        'hammer',
        keys=('127:0', '105:0', '357:0', '80:0'),
        excluded=('204:5572', '97:402'),
    )
)
