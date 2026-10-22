"""Act 2 routes (levels/routes.md)."""

from inventory_tracking.levels.handlers.tal_rasha import DURIEL
from inventory_tracking.routes.model import Route, back, enter, fight, leave, level, loot, tour, use


TOMBS = (66, 67, 68, 69, 70, 71, 72)
DURIELS_LAIR = 73


def tombs(duriel: bool = DURIEL) -> Route:
    """The Canyon cleared first (a full clear's rest of the level comes before the route's goal), then its seven tombs
    one by one, the nearest not yet entered first, each cleared and left by its way back (the player, 00:45 on
    2026-10-18: "for canyon of the magi loop: we should go through every tomb one by one"; "Canyon first, then tombs").
    A tomb's own script is its way back alone: a full clear does the tomb before it, and a `clear` stage is never done.

    `duriel` (levels/handlers/tal_rasha.py DURIEL, 2026-10-21): each tomb's way on is the Orifice's portal into
    Duriel's Lair first, done where the tomb has no Orifice (its mark absent: routes/progress.py `done`), so only the
    true tomb's run goes into the lair, whichever tomb it is; Duriel fought there, his loot, the game's end or the
    Town Portal back to the tour (macros/tzroutine.py `produce`). The player, 2026-10-20 ~22:50: "toms ... -> duriel ->
    rest of tombs"."""
    way_in = (use('Orifice', DURIELS_LAIR),) if duriel else ()
    lair = (level(DURIELS_LAIR, fight('Duriel', 'Duriel'), loot(), leave()),) if duriel else ()
    return Route(
        "Tal Rasha's Tombs",
        (46,),
        (
            level(46, tour('Tomb', TOMBS), loot(), leave()),
            *(level(tomb, *way_in, back('Canyon of the Magi', 46)) for tomb in TOMBS),
            *lair,
        ),
    )


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
            level(40, enter('Rocky Waste', 41), alternate=True),  # on foot, as act1.py's Rogue Encampment
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
    tombs(),
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
    # Act 2 by its script (macros/acts/act2.py): the levels the town's own way in leaves out, reached up the stairs
    # from a waypoint instead (Lut Gholein marks only its way to the desert and its waypoint, levels/exits.py; the
    # connectors 40→50 and 40→47 have no catalogue stage). The player, 2026-10-20 ~22:50: "arcane sanctuary ->
    # summoner -> rest of arcane sanctuary -> rest of zones one by one". The stairs are the levels' warps
    # (levels.txt Vis: 52 → 51 → 50, 48 → 47); not played yet.
    Route(
        'Harem',
        (52,),
        (
            level(52, enter('Harem 2', 51), alternate=True),
            level(51, enter('Harem 1', 50), alternate=True),
            level(50, loot(), leave(), alternate=True),
        ),
    ),
    Route(
        'Sewers 1',
        (48,),
        (level(48, enter('Sewers 1', 47), alternate=True), level(47, loot(), leave(), alternate=True)),
    ),
]
