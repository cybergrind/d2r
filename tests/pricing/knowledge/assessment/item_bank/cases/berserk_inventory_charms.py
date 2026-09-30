"""Explicit Berserk inventory variants, reviewed in wp-a-builds charm tables.

Starter/Standard Gheed; Standard/Chaos Prep/Max Mobility Annihilus and Barbarian
Torch. Hardcore is not added to these Softcore role expectations.
"""

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_inventory_charms import cases


CASES = tuple(
    cases(
        build='berserk-barbarian',
        player_class='Barbarian',
        class_id=4,
        prefix='berserk',
        variants={'gheed': (0, 1), 'annihilus': (1, 4, 5), 'torch': (1, 4, 5)},
    )
)
