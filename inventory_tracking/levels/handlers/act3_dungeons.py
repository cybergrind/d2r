"""Swampy Pit 1-2 and Flayer Dungeon 1-2: the stairs down and the way back.

Unconfirmed (D2MOO DRLGMAZE_PlaceAct3DungeonStuff, 2026-10-01; no evidence yet): each level places
one 'Dungeon Prev' and one 'Dungeon Next'. Swampy Pit 3 and Flayer Dungeon 3 (Khalim's Brain)
are single 'Dungeon Treasure' presets covering the level, so they have no handler.
"""

from inventory_tracking.levels.handler import previous, stairs_down


DUNGEON = 'Act 3 - Dungeon'

HANDLERS = [
    stairs_down('Swampy Pit 1', areas={86}, family=DUNGEON, extra=[previous(DUNGEON, 'Flayer Jungle')]),
    stairs_down('Swampy Pit 2', areas={87}, family=DUNGEON, extra=[previous(DUNGEON, 'Swampy Pit 1')]),
    stairs_down('Flayer Dungeon 1', areas={88}, family=DUNGEON, extra=[previous(DUNGEON, 'Flayer Jungle')]),
    stairs_down('Flayer Dungeon 2', areas={89}, family=DUNGEON, extra=[previous(DUNGEON, 'Flayer Dungeon 1')]),
]
