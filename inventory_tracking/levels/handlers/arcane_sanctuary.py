"""Arcane Sanctuary: the Summoner, at his arm's DS1 spot (Summ*.ds1; S and E seen in game, W and N not).

The mark is beside him (user, 2026-10-11: "teleport not in boss and his group, but slightly offset the
point"); measurements in history/handlers_arcane_sanctuary.md.
"""

from inventory_tracking.levels.handler import target


SUMMONER_AT = {
    'Act 2 - Arcane Summoner W': (35, 20),
    'Act 2 - Arcane Summoner E': (20, 35),
    'Act 2 - Arcane Summoner S': (20, 20),
    'Act 2 - Arcane Summoner N': (20, 30),
}

STAND = (10, 15)  # world units from his spot to the mark: the landing below his platform

HANDLERS = [
    target(
        'Arcane Sanctuary',
        areas={74},
        label='Summoner',
        preset=r'Act 2 - Arcane Summoner [NSEW]',
        at_in={name: (x + STAND[0], y + STAND[1]) for name, (x, y) in SUMMONER_AT.items()},
        confirmed=True,
    )
]
