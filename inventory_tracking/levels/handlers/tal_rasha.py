"""Tal Rasha's Tombs: the Orifice in the true tomb, Kaa or a chest in the others, the way back.

All optional: only the staff tomb has the Talrasha room (D2MOO DrlgMaze; fixture tal_rasha_true_tomb). With `DURIEL`
the Orifice's mark sits on the object its room's file places (levels/data/preset_objects.json: one layout per turn,
lvlprest 460-463), and a tomb whose rooms hold no Talrasha room has none (`Guidance.absent`: the client holds every
room of the level from its entry), so a route's `use` of it is done there (routes/progress.py `done`).
"""

from inventory_tracking.levels.handler import Handler, PoiSpec, previous
from inventory_tracking.levels.model import DURIEL_PORTAL, ORIFICE


TOMB = 'Act 2 - Tomb'
# The way into Duriel's Lair (73), 2026-10-21 (the player: "start implementation for ready to build items without
# questions"): the Orifice's mark clicks the Duriel's Lair portal beside it (objects.txt 100, levels/model.py
# DURIEL_PORTAL) and the catalogue's tombs lead into the lair by it (routes/catalog/act2.py `tombs`). The portal is
# there, open, in every game of a difficulty whose Horadric Staff quest the character finished (D2MOO A2Q6.cpp
# ACT2Q6_Callback13_PlayerStartedGame, OBJECTS_InitFunction21_HoradricOrifice). On 2026-10-21 ~14:45 (the player:
# "after that shard's stack go to 90, let's use act2 shards", "make sure that we're focused on the correct finishing
# the act and killing boss"): the zone graph hangs the lair off whichever toured tomb holds the mark
# (routes/zone_graph.py `Node.side`). Off: the mark only a place, no route into 73
DURIEL = True


def orifice(duriel: bool = DURIEL) -> PoiSpec:
    """The Orifice's mark: with `duriel` on the object, clicking the portal beside it, and absent from a tomb without
    it; else the Talrasha room, as before."""
    pattern = rf'{TOMB} Talrasha [NSEW]'
    if not duriel:
        return PoiSpec('Orifice', pattern, optional=True, family=TOMB)
    return PoiSpec('Orifice', pattern, optional=True, family=TOMB, each=True, thing=ORIFICE, use=DURIEL_PORTAL)


def handlers(duriel: bool = DURIEL) -> list[Handler]:
    """The tombs' handler (`orifice`)."""
    return [
        Handler(
            "Tal Rasha's Tombs",
            frozenset(range(66, 73)),
            (
                orifice(duriel),
                PoiSpec('Ancient Kaa', rf'{TOMB} Kaa [NSEW]', optional=True, family=TOMB),
                PoiSpec('Chest', rf'{TOMB} Chest [NSEW]', optional=True, family=TOMB),
                previous(TOMB, 'Canyon of the Magi'),
            ),
            confirmed=True,
        )
    ]


HANDLERS = handlers()
