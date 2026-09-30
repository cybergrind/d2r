"""Blizzard Standard/MF/Set inventory charms; Hardcore source is outside this scope."""

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_inventory_charms import cases


CASES = tuple(
    cases(
        build='blizzard-sorceress',
        player_class='Sorceress',
        class_id=1,
        prefix='blizzard',
        variants={'gheed': (2,), 'annihilus': (1, 2, 3), 'torch': (1, 2, 3)},
        role_overrides={
            'annihilus': ('blizzard-standard-annihilus', 'blizzard-mf-annihilus', 'blizzard-set-annihilus')
        },
    )
)
