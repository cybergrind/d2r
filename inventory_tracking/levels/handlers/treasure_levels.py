"""Levels that are one fixed preset: the mark is the object the level is gone into for.

Unconfirmed (installed game files, 2026-10-12; no dump of any of these levels yet). The level's one
preset covers it, so the preset gives no direction; its DS1 file places the object, at another spot
in each layout, and the mark sits there (`thing`; levels/data/preset_objects.json, levels/routes.md).
- The second levels of the act 1 caves ('Cave Treasure 2-5': Cave, Underground Passage, Hole, Pit),
  Swampy Pit 3 ('Dungeon Treasure 1'), Drifter Cavern and the Icy Cellar ('Ice Pool A/B', six
  layouts): the super chest.
- Flayer Dungeon 3 ('Dungeon Treasure 2') and Kurast Sewers 2 ('Sewer Treasure X'): Khalim's chests.
- Frozen River ('Ice River A/B', four layouts) has no super chest: the mark is where Anya stands frozen.
- Abaddon, the Pit of Acheron and the Infernal Pit are 'Act 5 - Lava' mazes: the second layout of a
  dead end (N, S, E, W) holds a super chest, the first none, so a level has as many as it rolled.
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
