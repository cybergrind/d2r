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


# ALONE (2026-10-25 ~17:15), the player: "act 2 tz leveling: use worlstone shard for act 2 / go all canyon of the
# magi + all tals rasha tombs (small + kaa + duriel) / go full arcane sanctuary (+kill summoner)" (the goal of
# 2026-10-24: "best exp/hour we can"). True: the act 2 kind's game is the Eastern shard, then `ALONE_STEPS` only: the
# Canyon of the Magi (46) and its seven tombs one by one (the "small" ones, the one holding Ancient Kaa the Soulless,
# superuniques.txt "Act 2 Super C", killed by the boss ledger's goals, and the true tomb whose Orifice portal leads into
# Duriel's Lair, 73, Duriel killed), then the Arcane Sanctuary (74) from its own waypoint, toured whole (`WHOLE`), the
# Summoner killed; then the game's end (Save and Exit) and the next game. No Palace Cellars, Harem, Radament, Sewers,
# rest of act 2, rotation or other act's shard (actloop.py `alone`). Only where act 2 is the game's own act (played
# first: tzroutine.py `alone_act`); act 2 as another kind's overflow act, or terrorized by hand in TZ, plays `script`'s
# whole order as before. False: the whole order, the rest of the act and the rotation, as before
ALONE = True
# The levels the alone game works whole: every room toured whatever their size (the Arcane Sanctuary's 469 hostiles
# are over agenda.py BIG_LEVEL) or a boss on them (the Summoner's level was a way to him: tz+ on the way, no room
# toured), by tzroutine.py WHOLE. The Canyon (182), the tombs (124 each) and the lair are toured by TZ+ already
WHOLE = frozenset((74,))


DURIEL_MISSING = (
    "no way into Duriel's Lair yet: its portal is spawned beside the Orifice of the true tomb, found only inside it, "
    'and the tomb tour has no side trip'
)


def script(duriel: bool = DURIEL, alone: bool = ALONE) -> ActScript:
    """The act's order; `duriel`: the lair on the tombs' tour (no step of its own), else its step skipped and said;
    `alone`: the act 2 kind's game plays `ALONE_STEPS` only, `WHOLE` toured whole (`ALONE`)."""
    lair: tuple[Step, ...] = () if duriel else (Trip('Duriel', 73, missing=DURIEL_MISSING),)
    only = (*TOMBS_FIRST, *lair, *ALONE_STEPS) if alone else None
    return ActScript(
        2, (*TOMBS_FIRST, *lair, *AFTER_DURIEL), ready=True, alone=only, whole=WHOLE if alone else frozenset()
    )


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
# The alone game's steps after the tombs (`ALONE`): the Arcane Sanctuary from its own waypoint, the Summoner
ALONE_STEPS: tuple[Step, ...] = (Trip('Summoner', 74),)

SCRIPT = script()
