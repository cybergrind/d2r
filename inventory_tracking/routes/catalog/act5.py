"""Act 5 routes (levels/routes.md)."""

from inventory_tracking.routes.model import Route, enter, fight, leave, level, loot, stand, use


CHEST = 'Super chest'
UNREAD = 'the red portal is not in the map files: its object is not read yet'


def hell_pit(name: str, start: int, outside: int, pit: int, *before) -> Route:
    """A red portal on an outdoor level into a pit whose dead ends hold super chests."""
    return Route(
        name,
        (start,),
        (*before, level(outside, use(name, pit, pending=UNREAD)), level(pit, use(CHEST), loot(), leave())),
    )


ROUTES = [
    hell_pit('Abaddon', 111, 111, 125, level(110, enter('Frigid Highlands', 111))),
    hell_pit('Pit of Acheron', 112, 112, 126),
    hell_pit('Infernal Pit', 117, 117, 127),
    Route(
        'Frozen River',
        (113,),
        (level(113, enter('Frozen River', 114)), level(114, fight('Frozenstein', 'Anya'), loot(), leave())),
    ),
    Route(
        'Drifter Cavern',
        (115,),
        (level(115, enter('Drifter Cavern', 116)), level(116, use(CHEST), loot(), leave())),
    ),
    Route(
        'Icy Cellar',
        (118,),
        (
            level(118, enter('Icy Cellar', 119)),
            level(119, fight('Snapchip Shatter', CHEST), use(CHEST), loot(), leave()),
        ),
    ),
    Route(
        'Nihlathak',
        (123,),
        (
            level(121, enter('Halls of Anguish', 122)),
            level(122, enter('Next level', 123)),
            level(123, enter('Next level', 124)),
            level(124, fight('Nihlathak Boss', 'Nihlathak'), loot(), leave()),
        ),
    ),
    Route(
        'Baal',
        (129,),
        (
            level(120, enter('The Worldstone Keep 1', 128)),
            *(level(area, enter('Next level', area + 1)) for area in (128, 129, 130)),
            # The hall, the five waves (Lister leads the last), then the portal Baal leaves by.
            level(131, stand('Throne'), fight('Lister the Tormentor'), loot(), use('Worldstone Chamber', 132)),
            level(132, fight('Baal', 'Baal'), loot(), leave()),
        ),
    ),
]
