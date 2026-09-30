"""Explicit main/Standard/MF Renewed Black Cleft uses, not invented roll bounds.

The native immunity core is fixed; illustrated extra modifiers are observations,
not minima or a replacement for the still-missing custom generator definitions.
"""

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_renewed_sunder import cases


CASES = tuple(
    cases(
        roles=tuple(
            'blessed-hammer-paladin-renewed-black-cleft-' + variant + '-renewed-sunder'
            for variant in ('main-alternatives', 'standard', 'magic-find')
        ),
        player_class='Paladin',
        prefix='hammer',
    )
)
