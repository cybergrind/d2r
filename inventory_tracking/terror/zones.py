"""Herald groups: levels that share one Herald kill counter, with the article's mean population.

Groups, levels and weights are the installed game's (terror_zones/data/desecratedzones-game.json,
extracted 2026-10-02 with terror_zones/game_files.py): levels with the same `zone_data_id` share
a counter and each carries a `zone_completion_weight`; `zone` is the Terror Zone they are
terrorized with. Five levels of Terror Zones have no group at all (Forgotten Tower, Valley of
Snakes, Harem Level 1, Duriel's Lair, Worldstone Chamber). Names and populations:
terror_zones/data/article-zones.json (Patch 3.2 article, mean monsters per group). Each Tal
Rasha tomb is its own group at the article's small-false size (124): which tomb is real (390)
or the big false one (270) varies per game.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class HeraldGroup:
    act: int
    name: str
    population: int
    zone: str  # Terror Zone id: these levels are terrorized together
    zone_data: str  # zone_data_id: the levels sharing one Herald counter
    areas: tuple[int, ...]
    weights: tuple[float, ...]  # zone_completion_weight per area


TOMB = "Tal Rasha's Tomb"  # the real/big tomb varies per game: each at the article's small size

GROUPS: tuple[HeraldGroup, ...] = (
    HeraldGroup(
        1,
        'Burial Grounds, Crypt and Mausoleum',
        203,
        'Act1-BurialGrounds',
        'Act1-BurialGrounds',
        (17, 18, 19),
        (1, 1, 1),
    ),
    HeraldGroup(
        1,
        'Inner Cloister, Cathedral and Catacombs',
        374,
        'Act1-Catacombs',
        'Act1-Catacombs',
        (32, 33, 34, 35, 36, 37),
        (0.5, 1, 2, 2, 2, 1),
    ),
    HeraldGroup(1, 'Cold Plains', 209, 'Act1-ColdPlains', 'Act1-ColdPlains', (3,), (1,)),
    HeraldGroup(1, 'Cave levels', 181, 'Act1-ColdPlains', 'Act1-ColdPlains-Cave', (9, 13), (3, 1)),
    HeraldGroup(1, 'Dark Wood', 233, 'Act1-DarkWood', 'Act1-DarkWood', (5,), (1,)),
    HeraldGroup(1, 'Underground Passage levels', 255, 'Act1-DarkWood', 'Act1-DarkWood-Cave', (10, 14), (3, 1)),
    HeraldGroup(1, 'Blood Moor', 113, 'Act1-BloodMoor', 'Act1-BloodMoor', (2,), (1,)),
    HeraldGroup(1, 'Den of Evil', 67, 'Act1-BloodMoor', 'Act1-BloodMoor-Cave', (8,), (1,)),
    HeraldGroup(1, 'Barracks', 102, 'Act1-Jail', 'Act1-Barracks', (28,), (1,)),
    HeraldGroup(1, 'Jail levels', 252, 'Act1-Jail', 'Act1-Jail', (29, 30, 31), (1, 1, 1)),
    HeraldGroup(1, 'Cow Level', 501, 'Act1-MooMooFarm', 'Act1-MooMooFarm', (39,), (1,)),
    HeraldGroup(1, 'Stony Field and Tristram', 229, 'Act1-Tristram', 'Act1-Tristram', (4, 38), (3, 1)),
    HeraldGroup(1, 'Black Marsh', 199, 'Act1-Tower', 'Act1-Tower-Wilderness', (6,), (1,)),
    HeraldGroup(1, 'Hole levels', 178, 'Act1-Tower', 'Act1-Tower-Cave', (11, 15), (3, 1)),
    HeraldGroup(1, 'Tower Cellar levels', 260, 'Act1-Tower', 'Act1-Tower', (21, 22, 23, 24, 25), (2, 2, 2, 2, 1)),
    HeraldGroup(
        1,
        'Tamoe Highland and Outer Cloister',
        278,
        'Act1-Monastery',
        'Act1-Monastery-Wilderness',
        (7, 26, 27),
        (2, 1, 1),
    ),
    HeraldGroup(1, 'Pit levels', 223, 'Act1-Monastery', 'Act1-Monastery-Cave', (12, 16), (3, 1)),
    HeraldGroup(2, 'Lut Gholein Sewer levels', 315, 'Act2-Sewers', 'Act2-Sewers', (47, 48, 49), (1, 1, 1)),
    HeraldGroup(2, 'Rocky Waste', 152, 'Act2-RockyWaste', 'Act2-RockyWaste', (41,), (1,)),
    HeraldGroup(2, 'Stony Tomb levels', 115, 'Act2-RockyWaste', 'Act2-RockyWaste-Tomb', (55, 59), (1, 1)),
    HeraldGroup(2, 'Dry Hills', 147, 'Act2-DryHills', 'Act2-DryHills', (42,), (1,)),
    HeraldGroup(2, 'Halls of the Dead levels', 352, 'Act2-DryHills', 'Act2-DryHills-Tomb', (56, 57, 60), (1, 1, 1)),
    HeraldGroup(2, 'Far Oasis', 200, 'Act2-FarOasis', 'Act2-FarOasis', (43,), (1,)),
    HeraldGroup(2, 'Maggot Lair Level 1', 129, 'Act2-FarOasis', 'Act2-FarOasis-LairA', (62,), (1,)),
    HeraldGroup(2, 'Maggot Lair Level 2', 98, 'Act2-FarOasis', 'Act2-FarOasis-LairB', (63,), (1,)),
    HeraldGroup(2, 'Maggot Lair Level 3', 83, 'Act2-FarOasis', 'Act2-FarOasis-LairC', (64,), (1,)),
    HeraldGroup(2, 'Lost City', 168, 'Act2-LostCity', 'Act2-LostCity', (44,), (1,)),
    HeraldGroup(2, 'Claw Viper Temple levels', 221, 'Act2-LostCity', 'Act2-LostCity-Tomb', (58, 61), (3, 1)),
    HeraldGroup(2, 'Ancient Tunnels', 106, 'Act2-LostCity', 'Act2-LostCity-Sewer', (65,), (1,)),
    HeraldGroup(2, 'Canyon of the Magi', 182, 'Act2-TalRashas', 'Act2-TalRashas', (46,), (1,)),
    HeraldGroup(2, f'{TOMB} 1', 124, 'Act2-TalRashas', 'Act2-TalRashas-Tomb1', (66,), (1,)),
    HeraldGroup(2, f'{TOMB} 2', 124, 'Act2-TalRashas', 'Act2-TalRashas-Tomb2', (67,), (1,)),
    HeraldGroup(2, f'{TOMB} 3', 124, 'Act2-TalRashas', 'Act2-TalRashas-Tomb3', (68,), (1,)),
    HeraldGroup(2, f'{TOMB} 4', 124, 'Act2-TalRashas', 'Act2-TalRashas-Tomb4', (69,), (1,)),
    HeraldGroup(2, f'{TOMB} 5', 124, 'Act2-TalRashas', 'Act2-TalRashas-Tomb5', (70,), (1,)),
    HeraldGroup(2, f'{TOMB} 6', 124, 'Act2-TalRashas', 'Act2-TalRashas-Tomb6', (71,), (1,)),
    HeraldGroup(2, f'{TOMB} 7', 124, 'Act2-TalRashas', 'Act2-TalRashas-Tomb7', (72,), (1,)),
    HeraldGroup(2, 'Harem Level 2', 84, 'Act2-ArcaneSanctuary', 'Act2-ArcaneSanctuary-Harem', (51,), (1,)),
    HeraldGroup(
        2, 'Palace Cellar levels', 247, 'Act2-ArcaneSanctuary', 'Act2-ArcaneSanctuary-Basement', (52, 53, 54), (1, 1, 1)
    ),
    HeraldGroup(2, 'Arcane Sanctuary', 469, 'Act2-ArcaneSanctuary', 'Act2-ArcaneSanctuary', (74,), (1,)),
    HeraldGroup(3, 'Spider Forest', 341, 'Act3-SpiderForest', 'Act3-SpiderForest', (76,), (1,)),
    HeraldGroup(3, 'Arachnid Lair', 63, 'Act3-SpiderForest', 'Act3-SpiderForest-Cave1', (84,), (1,)),
    HeraldGroup(3, 'Spider Cavern', 61, 'Act3-SpiderForest', 'Act3-SpiderForest-Cave2', (85,), (1,)),
    HeraldGroup(3, 'Great Marsh', 326, 'Act3-GreatMarsh', 'Act3-GreatMarsh', (77,), (1,)),
    HeraldGroup(3, 'Flayer Jungle', 475, 'Act3-FlayerJungle', 'Act3-FlayerJungle', (78,), (1,)),
    HeraldGroup(
        3, 'Swampy Pit levels', 187, 'Act3-FlayerJungle', 'Act3-FlayerJungle-Dungeon1', (86, 87, 90), (1, 1, 1)
    ),
    HeraldGroup(
        3, 'Flayer Dungeon levels', 212, 'Act3-FlayerJungle', 'Act3-FlayerJungle-Dungeon2', (88, 89, 91), (2, 2, 1)
    ),
    HeraldGroup(3, 'Lower Kurast', 115, 'Act3-Kurast', 'Act3-Kurast1', (79,), (1,)),
    HeraldGroup(3, 'Kurast Bazaar', 148, 'Act3-Kurast', 'Act3-Kurast2', (80,), (1,)),
    HeraldGroup(3, 'Upper Kurast and Kurast Causeway', 135, 'Act3-Kurast', 'Act3-Kurast3', (81, 82), (9, 1)),
    HeraldGroup(3, 'Kurast Sewer levels', 188, 'Act3-Kurast', 'Act3-KurastSewer', (92, 93), (4, 1)),
    HeraldGroup(
        3,
        'All Kurast temple levels',
        170,
        'Act3-Kurast',
        'Act3-KurastTemple',
        (94, 95, 96, 97, 98, 99),
        (1, 1, 1, 1, 1, 1),
    ),
    HeraldGroup(3, 'Travincal', 110, 'Act3-Travincal', 'Act3-Travincal', (83,), (1,)),
    HeraldGroup(
        3, 'Durance of Hate levels', 409, 'Act3-DuranceOfHate', 'Act3-DuranceOfHate', (100, 101, 102), (2, 3, 1)
    ),
    HeraldGroup(4, 'Outer Steppes', 187, 'Act4_OuterSteppes', 'Act4_OuterSteppes1', (104,), (1,)),
    HeraldGroup(4, 'Plains of Despair', 193, 'Act4_OuterSteppes', 'Act4_OuterSteppes2', (105,), (1,)),
    HeraldGroup(4, 'City of the Damned', 211, 'Act4-RiverOfFlame', 'Act4-RiverOfFlame1', (106,), (1,)),
    HeraldGroup(4, 'River of Flame', 231, 'Act4-RiverOfFlame', 'Act4-RiverOfFlame2', (107,), (1,)),
    HeraldGroup(4, 'Chaos Sanctuary', 189, 'Act4-ChaosSanctuary', 'Act4-ChaosSanctuary', (108,), (1,)),
    HeraldGroup(5, 'Bloody Foothills', 488, 'Act5-BloodyFoothils', 'Act5-BloodyFoothils1', (110,), (1,)),
    HeraldGroup(5, 'Frigid Highlands', 339, 'Act5-BloodyFoothils', 'Act5-BloodyFoothils2', (111,), (1,)),
    HeraldGroup(5, 'Abaddon', 117, 'Act5-BloodyFoothils', 'Act5-BloodyFoothils3', (125,), (1,)),
    HeraldGroup(5, 'Arreat Plateau', 277, 'Act5-ArreatPlateau', 'Act5-ArreatPlateau1', (112,), (1,)),
    HeraldGroup(5, 'Pit of Acheron', 87, 'Act5-ArreatPlateau', 'Act5-ArreatPlateau2', (126,), (1,)),
    HeraldGroup(5, 'Crystalline Passage', 146, 'Act5-CrystallinePassage', 'Act5-CrystallinePassage1', (113,), (1,)),
    HeraldGroup(5, 'Frozen River', 203, 'Act5-CrystallinePassage', 'Act5-CrystallinePassage2', (114,), (1,)),
    HeraldGroup(5, "Nihlathak's Temple and Halls of Anguish", 414, 'Act5-Halls', 'Act5-Halls1', (121, 122), (1, 3)),
    HeraldGroup(5, 'Halls of Pain', 405, 'Act5-Halls', 'Act5-Halls2', (123,), (1,)),
    HeraldGroup(5, 'Halls of Vaught', 178, 'Act5-Halls', 'Act5-Halls3', (124,), (1,)),
    HeraldGroup(
        5, 'Glacial Trail and Drifter Cavern', 233, 'Act5-GlacialTrail', 'Act5-GlacialTrail', (115, 116), (3, 1)
    ),
    HeraldGroup(5, "Ancients' Way and Icy Cellar", 281, 'Act5-AncientsWay', 'Act5-AncientsWay', (118, 119), (3, 1)),
    HeraldGroup(5, 'Frozen Tundra', 374, 'Act5-FrozenTundra', 'Act5-FrozenTundra1', (117,), (1,)),
    HeraldGroup(5, 'Infernal Pit', 115, 'Act5-FrozenTundra', 'Act5-FrozenTundra2', (127,), (1,)),
    HeraldGroup(
        5,
        'Worldstone Keep and Throne',
        580,
        'Act5-WorldstoneKeep',
        'Act5-WorldstoneKeep',
        (128, 129, 130, 131),
        (2, 2, 2, 1),
    ),
)

# Tomb sizes by Room2 count (evidence 2026-10-02: Orifice tomb 72 rooms, Kaa tomb 48, chest
# tombs 24-28) against the article's real / big false / small false tombs.
TOMB_SIZES = ((60, 390), (36, 270))


def group_population(group: HeraldGroup, level_rooms: int | None = None) -> int:
    """The group's mean population; a Tal Rasha tomb by the room count of the tomb entered."""
    if group.name.startswith(TOMB) and level_rooms:
        return next((size for rooms, size in TOMB_SIZES if level_rooms >= rooms), group.population)
    return group.population


_BY_AREA = {area: group for group in GROUPS for area in group.areas}


def group_of(area: int) -> HeraldGroup | None:
    return _BY_AREA.get(area)
