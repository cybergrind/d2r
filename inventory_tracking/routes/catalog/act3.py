"""Act 3 routes (levels/routes.md)."""

from inventory_tracking.routes.model import (
    BLADE_WARP,
    DEATH_MARK,
    SIGIL_LETHARGY,
    Route,
    Stage,
    clear,
    enter,
    fight,
    leave,
    level,
    loot,
    stand,
    use,
)


def temple(name: str, start: int, way: tuple[tuple[int, str, int], ...], temple_area: int, *stages: Stage) -> Route:
    """A Kurast temple, a dead end off its city level; `way`: (level, door, level behind it) from the waypoint."""
    path = tuple(level(area, enter(door, to), alternate=True) for area, door, to in way)
    return Route(name, (start,), (*path, level(temple_area, *stages, loot(), leave())))


ROUTES = [
    Route(
        'Spider Cavern',
        (76,),
        (
            level(76, enter('Spider Cavern', 85)),
            level(85, fight('Sszark the Burning', "Khalim's Eye"), loot(), leave()),
        ),
    ),
    Route(
        'Arachnid Lair',
        (76,),
        (level(76, enter('Arachnid Lair', 84), alternate=True), level(84, use('Chest'), loot(), leave())),
    ),
    Route('Great Marsh', (77,), (level(77, clear(), loot(), leave()),)),
    Route(
        'Swampy Pit',
        (78,),
        (
            level(78, enter('Swampy Pit 1', 86)),
            level(86, enter('Next level', 87)),
            level(87, enter('Next level', 90)),
            level(90, use('Super chest'), loot(), leave()),
        ),
    ),
    Route(
        'Flayer Dungeon',
        (78,),
        (
            level(78, enter('Flayer Dungeon 1', 88), alternate=True),
            level(88, enter('Next level', 89)),
            level(89, enter('Next level', 91)),
            level(91, fight('Witch Doctor Endugu', "Khalim's Brain"), loot(), leave()),
        ),
    ),
    Route(
        'Lower Kurast',
        (79,),
        (level(79, use('Super chests', pending='the mark is the camp, not its two chests'), loot(), leave()),),
    ),
    Route(
        'Kurast Sewers',
        (80,),
        (
            level(80, enter('Sewers', 92)),
            level(92, use('Chest'), loot(), enter('Sewers 2', 93)),
            level(93, stand("Khalim's Heart"), loot(), leave()),
        ),
    ),
    temple(
        'Ruined Temple',
        80,
        ((80, 'Ruined Temple', 94),),
        94,
        fight('Battlemaid Sarina', 'Battlemaid Sarina'),
    ),
    temple('Disused Fane', 80, ((80, 'Disused Fane', 95),), 95, clear()),
    temple('Forgotten Reliquary', 81, ((81, 'Forgotten Reliquary', 96),), 96, clear()),
    temple('Forgotten Temple', 81, ((81, 'Forgotten Temple', 97),), 97, clear()),
    temple('Ruined Fane', 81, ((81, 'Kurast Causeway', 82), (82, 'Ruined Fane', 98)), 98, clear()),
    temple('Disused Reliquary', 81, ((81, 'Kurast Causeway', 82), (82, 'Disused Reliquary', 99)), 99, clear()),
    Route(
        'Mephisto',
        (81, 83, 101),
        (
            level(81, enter('Kurast Causeway', 82)),
            level(82, enter('Travincal', 83)),
            level(
                83,
                fight('Ismail Vilehand', 'Council'),
                loot(),
                enter('Durance of Hate', 100),
            ),
            level(100, enter('Next level', 101)),
            level(101, enter('Next level', 102)),
            level(
                102,
                # user, 2026-10-12: Blade Warp to the portal raises the bridge, the way out after the
                # fight; Death Mark sets the demons on him; Sigil: Lethargy; then the kill.
                stand('Red portal', by=BLADE_WARP),
                fight('Mephisto', 'Mephisto', opener=(DEATH_MARK, SIGIL_LETHARGY)),
                loot(),
                use('Red portal', 103),
                leave(),
            ),
        ),
    ),
]
