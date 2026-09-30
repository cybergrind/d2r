"""Blizzard Standard/Tal mercenary Fortitude: native armor, no legacy ebug bonus."""

from tests.pricing.knowledge.assessment.item_bank.cases.holy_bolt_fortitude import cases


CASES = tuple(
    case
    for variant in (1, 3)
    for quality in ('normal', 'superior', 'low_quality')
    for case in cases(
        role=f'blizzard-sorceress-{variant}-merc-fortitude',
        prefix=f'blizzard/fortitude/{variant}',
        build='blizzard-sorceress',
        variant=variant,
        quality=quality,
        player_class='Sorceress',
        mercenary='Act 2 Might',
    )
)
