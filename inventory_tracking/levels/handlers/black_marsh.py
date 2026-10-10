"""Black Marsh: the Forgotten Tower entrance and the border gaps to Tamoe Highland and Dark Wood.

Tower confirmed 2026-09-30 (fixture black_marsh from evidence; the user checked the direction). The
first outdoor level: its Room2 list holds 8x8 chunks named 'Wild Border N' (level edge),
feature presets such as 'Tower 1', and Def 0 (generated terrain with no layout information).
Exits 2026-10-01, unconfirmed: D2MOO gAct1MonasteryDrlgLink links Black Marsh to Tamoe Highland
(7) and Dark Wood (5) to Black Marsh (handler.ExitsHandler, as in Cold Plains). The waypoint is
an object, not a preset, and is only in memory near the player (plan.md): not marked.
The tower is the level's first mark (user, 2026-10-10): the next level here is the Forgotten Tower,
so the teleport step runs Black Marsh -> Forgotten Tower -> Tower Cellar 1-5.
"""

from inventory_tracking.levels.handler import Exit, ExitsHandler, PoiSpec


HANDLERS = [
    ExitsHandler(
        'Black Marsh',
        frozenset({6}),
        (PoiSpec('Forgotten Tower', r'Act 1 - Tower 1', 'stairs'),),
        confirmed=True,  # the tower; the exits are unconfirmed
        exits=(Exit(7, 'Tamoe Highland'), Exit(5, 'Dark Wood', 'previous')),
        pois_first=True,
    )
]
