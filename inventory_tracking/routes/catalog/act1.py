"""Act 1 routes (levels/routes.md)."""

from inventory_tracking.routes.model import Route, clear, enter, fight, leave, level, loot, use


CHEST = 'Super chest'

ROUTES = [
    Route(
        'Den of Evil',
        (1,),
        (level(2, enter('Den of Evil', 8)), level(8, fight('Corpsefire', 'Corpsefire'), loot(), leave())),
    ),
    Route(
        'Cave',
        (3,),
        (
            level(3, enter('Cave', 9)),
            level(9, fight('Coldcrow', 'Coldcrow'), loot(), enter('Next level', 13)),
            level(13, use(CHEST), loot(), leave()),
        ),
    ),
    Route(
        'Mausoleum',
        (3,),
        (
            level(3, enter('Burial Grounds', 17), alternate=True),
            level(17, fight('Blood Raven', 'Graveyard'), loot(), enter('Mausoleum', 19)),
            level(19, use('Chest'), loot(), leave()),
        ),
    ),
    Route(
        'Crypt',
        (3,),
        (
            level(3, enter('Burial Grounds', 17), alternate=True),
            level(17, enter('Crypt', 18), alternate=True),
            level(18, fight('Bonebreaker', 'Bonebreak'), loot(), leave()),
        ),
    ),
    Route(
        'Tristram',
        (4,),
        (level(4, use('Tristram', 38)), level(38, use("Wirt's body"), loot(), leave())),
    ),
    Route(
        'Underground Passage',
        (5,),
        (
            level(5, enter('Underground Passage', 10)),
            level(10, enter('Level 2', 14)),
            level(14, use(CHEST), loot(), leave()),
        ),
    ),
    Route(
        'Countess',
        (6,),
        (
            level(6, enter('Forgotten Tower', 20)),
            level(20, enter('Tower Cellar 1', 21)),
            *(level(area, enter('Next level', area + 1)) for area in (21, 22, 23, 24)),
            level(25, fight('The Countess', 'Countess'), loot(), leave()),
        ),
    ),
    Route(
        'Hole',
        (6,),
        (
            level(6, enter('Hole 1', 11), alternate=True),
            level(11, enter('Next level', 15)),
            level(15, use(CHEST), loot(), leave()),
        ),
    ),
    Route(
        'Pit',
        (27,),
        (
            level(27, enter('Monastery Gate', 26)),
            level(26, enter('Tamoe Highland', 7)),
            level(7, enter('Pit', 12)),
            level(12, enter('Next level', 16)),
            level(16, use(CHEST), loot(), leave()),
        ),
    ),
    Route(
        'Andariel',
        (27, 29, 32, 35),
        (
            level(27, enter('Barracks', 28), alternate=True),
            *(level(area, enter('Next level', area + 1)) for area in (28, 29, 30)),
            level(31, enter('Inner Cloister', 32)),
            level(32, enter('Cathedral', 33)),
            level(33, enter('Catacombs 1', 34)),
            *(level(area, enter('Next level', area + 1)) for area in (34, 35, 36)),
            level(37, fight('Andariel', 'Andariel'), loot(), leave()),
        ),
    ),
    Route('Cow Level', (1,), (level(39, clear(), loot(), leave()),)),
]
