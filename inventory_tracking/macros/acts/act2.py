"""Act 2 terrorized by a Eastern Worldstone Shard (the kind `act2`, "Shard: Act 2"). The player, 2026-10-20 ~22:50:
"act2: act2 shard -> canyon of the magic -> toms ... -> duriel -> rest of tombs -> arcane sanctuary ->
summoner -> rest of arcane sanctuary -> rest of zones one by one".

The plan (pinned by tests/inventory_tracking/macros/acts/test_act2.py): the Canyon of the Magi, then its seven tombs
one by one (the nearest entrance not entered first), the Arcane Sanctuary and the Summoner, the Palace Cellars, the
Harem up the stairs from the Palace Cellar waypoint, Radament, Sewers 1 up the stairs from the Sewers 2 waypoint, then
the act's rest (the Halls of the Dead, the Maggot Lair, the Claw Viper Temple, the Stony Tomb, the Ancient Tunnels),
then the rotation.

Duriel is skipped, said (`Macro: act: act 2 step 2 (Duriel to 73): …: skipped`): the catalogue has no way into
Duriel's Lair (73). Its entrance is no warp (levels.txt gives 73 none): the game spawns the Duriel's Lair portal
(objects.txt 100) beside the Orifice (152) in the true tomb only (D2MOO A2Q6.cpp ACT2Q6_Timer_UpdateObjects: at x - 13,
y + 3 of it, once the staff is in), and which tomb is the true one is read only inside it
(levels/handlers/tal_rasha.py `Orifice`). The tour cannot branch into it yet: a tomb's script has one way on (its way
back), a `use` of a mark six tombs lack would hold their runs, and tzroutine's tour has no side level; the Orifice's
room (lvlprest 460-463) is not in levels/data/preset_objects.json either.
"""

from inventory_tracking.macros.acts.engine import WORKED, ActScript, Rest, Trip


DURIEL_MISSING = (
    "no way into Duriel's Lair yet: its portal is spawned beside the Orifice of the true tomb, found only inside it, "
    'and the tomb tour has no side trip'
)

SCRIPT = ActScript(
    2,
    (
        Trip("Tal Rasha's Tombs", 66, crossed=WORKED),  # the Canyon (46), then the seven tombs one by one
        Trip('Duriel', 73, missing=DURIEL_MISSING),  # "-> duriel -> rest of tombs": the tour plays on without him
        Trip('Summoner', 74),  # the Arcane Sanctuary from its own waypoint, the Summoner
        Trip('Summoner', 54, waypoint=52, crossed=WORKED),  # the rest of it: Palace Cellars 1-3
        Trip('Harem', 50, waypoint=52, crossed=WORKED),  # Harem 2 and 1, up the stairs (no walk from Lut Gholein)
        Rest(zone='Act2-ArcaneSanctuary'),  # nothing left of it now; a level a later catalogue adds
        Trip('Radament', 49, crossed=WORKED),  # Lut Gholein's sewers: Sewers 2 and 3, Radament
        Trip('Sewers 1', 47, waypoint=48, crossed=WORKED),  # Sewers 1, up the stairs from Sewers 2 (no town walk)
        # then the act's rest, one zone by one: the Halls of the Dead, the Maggot Lair, the Claw Viper Temple, the Stony
        # Tomb (walked out of Lut Gholein), the Ancient Tunnels
    ),
    ready=True,
)
