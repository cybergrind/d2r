"""Standard and Ubers Holy Freeze mercenary Fortitude from their exact guide loadouts."""

from tests.pricing.knowledge.assessment.item_bank.cases.holy_bolt_fortitude import cases


CASES = tuple(
    case
    for variant in (1, 3)
    for quality in ('normal', 'superior', 'low_quality')
    for case in cases(
        role=f'blessed-hammer-paladin-{variant}-merc-fortitude',
        prefix=f'hammer/fortitude/{variant}',
        build='blessed-hammer-paladin',
        variant=variant,
        quality=quality,
    )
)
