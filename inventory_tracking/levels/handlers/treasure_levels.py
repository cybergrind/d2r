"""Levels that are one fixed preset: the mark is the object the level is gone into for.

The object's spot per layout: levels/data/preset_objects.json. In the Hell pits only a dead end's
second layout holds a chest, so a level has as many as it rolled.
"""

from inventory_tracking.levels.handler import Handler, PoiSpec, target
from inventory_tracking.levels.model import BRAIN_CHEST, FROZEN_ANYA, HEART_CHEST, SUPER_CHEST


CHEST = 'Super chest'

HANDLERS = [
    target(
        'Cave level 2', areas={13, 14, 15, 16}, label=CHEST, preset=r'Act 1 - Cave Treasure [2-5]', thing=SUPER_CHEST
    ),
    target('Swampy Pit 3', areas={90}, label=CHEST, preset=r'Act 3 - Dungeon Treasure 1', thing=SUPER_CHEST),
    target(
        'Flayer Dungeon 3', areas={91}, label="Khalim's Brain", preset=r'Act 3 - Dungeon Treasure 2', thing=BRAIN_CHEST
    ),
    target(
        'Kurast Sewers 2', areas={93}, label="Khalim's Heart", preset=r'Act 3 - Sewer Treasure X', thing=HEART_CHEST
    ),
    target('Frozen River', areas={114}, label='Anya', preset=r'Act 5 - Ice River [AB]', thing=FROZEN_ANYA),
    target('Ice pool', areas={116, 119}, label=CHEST, preset=r'Act 5 - Ice Pool [AB]', thing=SUPER_CHEST),
    Handler(
        'Hell pit',
        frozenset({125, 126, 127}),
        (PoiSpec(CHEST, r'Act 5 - Lava [NSEW]', each=True, thing=SUPER_CHEST),),
    ),
]
