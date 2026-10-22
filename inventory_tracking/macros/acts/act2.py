"""Act 2 terrorized by a Eastern Worldstone Shard (the kind `act2`, "Shard: Act 2"). The player, 2026-10-20 ~22:50:
"act2: act2 shard -> canyon of the magic -> toms ... -> duriel -> rest of tombs -> arcane sanctuary ->
summoner -> rest of arcane sanctuary -> rest of zones one by one".

The plan (pinned by tests/inventory_tracking/macros/acts/test_act2.py): the Canyon of the Magi, then its seven tombs
one by one (the nearest entrance not entered first), the Arcane Sanctuary and the Summoner, the Palace Cellars, the
Harem up the stairs from the Palace Cellar waypoint, Radament, Sewers 1 up the stairs from the Sewers 2 waypoint, then
the act's rest (the Halls of the Dead, the Maggot Lair, the Claw Viper Temple, the Stony Tomb, the Ancient Tunnels),
then the rotation.

Duriel's Lair (73) has no warp (levels.txt gives it none): the game spawns the Duriel's Lair portal (objects.txt 100)
beside the Orifice (152) in the true tomb only (D2MOO A2Q6.cpp ACT2Q6_Timer_UpdateObjects: at x - 13, y + 3 of it,
open in every game once the character's Horadric Staff quest is done), and which tomb is the true one is read only
inside it (levels/handlers/tal_rasha.py `orifice`). With levels/handlers/tal_rasha.py DURIEL on (2026-10-21) the tour
takes it: every tomb's way on is the Orifice's portal first, done where the tomb has none (its mark absent), so the
true tomb's run goes into the lair, whichever tomb it is; Duriel, his loot, then the Town Portal back to the tour's
rest (macros/tzroutine.py `produce`); the tour's trip is [46, 66 … 72, 73] (routes/tz_routes.py `_sides`), no step
of its own; the zone graph (macros/zonenav.py, on for act 2) hangs the lair under the Canyon as the tour's side level
(routes/zone_graph.py `Node.side`), entered from the tomb that holds the Orifice. On since 2026-10-21 ~14:45 (the
player: "make sure that we're focused on the correct finishing the act and killing boss"). Off: Duriel is skipped,
said (`Macro: act: act 2 step 2 (Duriel to 73): …: skipped`).
"""

from inventory_tracking.levels.handlers.tal_rasha import DURIEL
from inventory_tracking.macros.acts.engine import WORKED, ActScript, Rest, Step, Trip


DURIEL_MISSING = (
    "no way into Duriel's Lair yet: its portal is spawned beside the Orifice of the true tomb, found only inside it, "
    'and the tomb tour has no side trip'
)


def script(duriel: bool = DURIEL) -> ActScript:
    """The act's order; `duriel`: the lair on the tombs' tour (no step of its own), else its step skipped and said."""
    lair: tuple[Step, ...] = () if duriel else (Trip('Duriel', 73, missing=DURIEL_MISSING),)
    return ActScript(2, (*TOMBS_FIRST, *lair, *AFTER_DURIEL), ready=True)


TOMBS_FIRST: tuple[Step, ...] = (
    # the Canyon (46), then the seven tombs one by one ("-> duriel -> rest of tombs": the true tomb's run into the lair
    # with DURIEL, else the tour plays on without him)
    Trip("Tal Rasha's Tombs", 66, crossed=WORKED),
)
AFTER_DURIEL: tuple[Step, ...] = (
    Trip('Summoner', 74),  # the Arcane Sanctuary from its own waypoint, the Summoner
    Trip('Summoner', 54, waypoint=52, crossed=WORKED),  # the rest of it: Palace Cellars 1-3
    Trip('Harem', 50, waypoint=52, crossed=WORKED),  # Harem 2 and 1, up the stairs (no walk from Lut Gholein)
    Rest(zone='Act2-ArcaneSanctuary'),  # nothing left of it now; a level a later catalogue adds
    Trip('Radament', 49, crossed=WORKED),  # Lut Gholein's sewers: Sewers 2 and 3, Radament
    Trip('Sewers 1', 47, waypoint=48, crossed=WORKED),  # Sewers 1, up the stairs from Sewers 2 (no town walk)
    # then the act's rest, one zone by one: the Halls of the Dead, the Maggot Lair, the Claw Viper Temple, the Stony
    # Tomb (walked out of Lut Gholein), the Ancient Tunnels
)

SCRIPT = script()
