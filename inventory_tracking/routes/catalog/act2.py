"""Act 2 routes (levels/routes.md)."""

from inventory_tracking.routes.model import Route, clear, enter, fight, leave, level, loot, use


TOMBS = (66, 67, 68, 69, 70, 71, 72)

ROUTES = [
    Route(
        'Radament',
        (40, 48),
        (
            level(47, enter('Next level', 48)),
            level(48, enter('Next level', 49)),
            level(49, fight('Radament', 'Radament'), loot(), leave()),
        ),
    ),
    Route(
        'Stony Tomb',
        (40,),
        (
            level(41, enter('Stony Tomb', 55)),
            level(55, enter('Next level', 59)),
            level(59, fight('Creeping Feature', 'Creeping Feature'), loot(), leave()),
        ),
    ),
    Route(
        'Halls of the Dead',
        (42, 57),
        (
            level(42, enter('Halls of the Dead', 56)),
            level(56, enter('Next level', 57)),
            level(57, enter('Next level', 60)),
            level(60, fight('Bloodwitch the Wild', 'Horadric Cube'), loot(), leave()),
        ),
    ),
    Route(
        'Maggot Lair',
        (43,),
        (
            level(43, enter('Maggot Lair', 62)),
            level(62, enter('Next level', 63)),
            level(63, enter('Next level', 64)),
            level(64, fight('Coldworm the Burrower', 'Coldworm'), loot(), leave()),
        ),
    ),
    Route(
        'Ancient Tunnels',
        (44,),
        (level(44, enter('Ancient Tunnels', 65)), level(65, use('Chest'), loot(), leave())),
    ),
    Route(
        'Claw Viper Temple',
        (44,),
        (
            level(44, enter('Valley of Snakes', 45), alternate=True),
            level(45, enter('Claw Viper Temple', 58)),
            level(58, enter('Next level', 61)),
            level(61, fight('Fangskin', 'Fangskin'), loot(), leave()),
        ),
    ),
    Route('Canyon of the Magi', (46,), (level(46, clear(), loot(), leave()),)),
    *(
        Route(
            f"Tal Rasha's Tomb {number}",
            (46,),
            (level(46, enter('Tomb', tomb), alternate=True), level(tomb, clear(), loot(), leave())),
        )
        for number, tomb in enumerate(TOMBS, 1)
    ),
    Route(
        'Summoner',
        (40, 52, 74),
        (
            level(50, enter('Harem 2', 51)),
            level(51, enter('Palace Cellar 1', 52)),
            level(52, enter('Palace Cellar 2', 53)),
            level(53, enter('Palace Cellar 3', 54)),
            level(54, use('Arcane Sanctuary', 74)),
            level(74, fight('The Summoner', 'Summoner'), loot(), leave()),
        ),
    ),
]
