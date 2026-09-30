"""Hammerdin inventory variants independently checked against guide charm lists.

Standard and Magic Find carry Gheed; Standard, Magic Find and Ubers carry
Annihilus and a Paladin Torch. Starter and Hardcore are not inferred.
"""

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_inventory_charms import cases


CASES = tuple(
    cases(
        build='blessed-hammer-paladin',
        player_class='Paladin',
        class_id=3,
        prefix='hammer',
        variants={'gheed': (1, 2), 'annihilus': (1, 2, 3), 'torch': (1, 2, 3)},
    )
)
