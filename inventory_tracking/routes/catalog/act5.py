"""Act 5 routes (levels/routes.md)."""

from inventory_tracking.routes.model import Route, clear, enter, fight, leave, level, loot, stand, use


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
    # The act 5 shard's levels no route above reaches from a waypoint (macros/acts/act5.py; the player, 2026-10-20
    # ~22:50: "act5: act5 shard -> throne -> baal -> halls -> nihiltak -> rest of zones"). Each walks back up from a
    # waypoint, so every script is another route's way through its level (alternate): the level card and the rotating
    # zones keep the routes above. Unplayed in the game (2026-10-20).
    # Up from the Halls of Pain: the up stairs are the Temple's SE quadrant ('Temple SE up', or 'SE Waypoint' when the
    # waypoint takes it: D2MOO DrlgMaze.cpp DRLGMAZE_PlaceAct5TempleStuff), warp slot 0 = levels.txt Vis0 (122 from
    # 123, 121 from 122), marked by levels/exits.py `warp_exits` with the level's name. Pindleskin stands at the
    # Temple Entrance's stairs (terror/data/elites.json preset 1088), where the walk up comes in.
    Route(
        'Halls of Anguish',
        (123,),
        (
            level(123, enter('Halls of Anguish', 122), alternate=True),
            level(122, enter("Nihlathak's Temple", 121), alternate=True),
            level(121, fight('Pindleskin', 'Pindleskin'), loot(), leave(), alternate=True),
        ),
    ),
    # Up from the Worldstone Keep 2 waypoint: its 'Baal Prev' stairs (levels/handlers/worldstone_keep.py)
    Route(
        'Worldstone Keep 1',
        (129,),
        (
            level(129, enter('Worldstone Keep 1', 128), alternate=True),
            level(128, clear(), loot(), leave(), alternate=True),
        ),
    ),
    # Back from the Frigid Highlands waypoint: 'Barricade To Siege' (levels/handlers/act5_outdoors.py, unconfirmed);
    # Harrogath's way out on foot is not known (levels/town_gate.py has no act 5 town)
    Route(
        'Bloody Foothills',
        (111,),
        (
            level(111, enter('Bloody Foothills', 110), alternate=True),
            level(110, clear(), loot(), leave(), alternate=True),
        ),
    ),
]
