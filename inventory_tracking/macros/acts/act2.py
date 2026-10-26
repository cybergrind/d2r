"""Act 2 terrorized by a Eastern Worldstone Shard (the kind `act2`, "Shard: Act 2"; and the Act 2 TZ leveling kind
`act2tz`, loop.py ACT2_TZ, by `TZ_LEVELING_STEPS`, 2026-10-25, and `TZ_LEVELING_EXTRAS`, 2026-10-26). The player,
2026-10-20 ~22:50: "act2: act2 shard -> canyon of the magic -> toms ... -> duriel -> rest of tombs -> arcane sanctuary
-> summoner -> rest of arcane sanctuary -> rest of zones one by one".

The plan (pinned by tests/inventory_tracking/macros/acts/test_act2.py): the Canyon of the Magi, then its seven tombs
one by one (the nearest entrance not entered first), the Arcane Sanctuary and the Summoner, the Palace Cellars, the
Harem up the stairs from the Palace Cellar waypoint, Radament, Sewers 1 up the stairs from the Sewers 2 waypoint, then
the act's rest (the Halls of the Dead, the Maggot Lair, the Claw Viper Temple, the Stony Tomb, the Ancient Tunnels),
then the rotation.

The Act 2 TZ leveling game (pinned by test_act2_alone.py and test_act2_extras.py): the Eastern shard (from a stack over
game/stash.py EASTERN_FLOOR), the Canyon and its seven tombs with Duriel's Lair, the Arcane Sanctuary toured whole and
the Summoner; then, when a Deep or Northern shard is over the limit, act 4's Chaos Sanctuary toured whole with the seals
and Diablo (the River of Flame only crossed) and act 5's Worldstone Keep 2 and 3 toured whole, the Throne and Baal
(`TZ_LEVELING_EXTRAS`); then Save and Exit.

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
from inventory_tracking.macros.acts.engine import ONLY, WORKED, ActScript, Rest, Step, Trip


# The levels the Act 2 TZ leveling game works whole: every room toured whatever their size (the Arcane Sanctuary's 469
# hostiles are over agenda.py BIG_LEVEL) or a boss on them (the Summoner's level was a way to him: tz+ on the way, no
# room toured), by tzroutine.py WHOLE. The Canyon (182), the tombs (124 each) and the lair are toured by TZ+ already
WHOLE = frozenset((74,))


DURIEL_MISSING = (
    "no way into Duriel's Lair yet: its portal is spawned beside the Orifice of the true tomb, found only inside it, "
    'and the tomb tour has no side trip'
)


def script(duriel: bool = DURIEL) -> ActScript:
    """The act's order; `duriel`: the lair on the tombs' tour (no step of its own), else its step skipped and said.
    `alone`: the Act 2 TZ leveling kind's steps (`TZ_LEVELING_STEPS` after the tombs), `WHOLE` toured whole; `extras`:
    its game's acts 4 and 5 when their shard is over the limit (`TZ_LEVELING_EXTRAS`)."""
    lair: tuple[Step, ...] = () if duriel else (Trip('Duriel', 73, missing=DURIEL_MISSING),)
    steps = (*TOMBS_FIRST, *lair)
    return ActScript(
        2,
        (*steps, *AFTER_DURIEL),
        ready=True,
        alone=(*steps, *TZ_LEVELING_STEPS),
        whole=WHOLE,
        extras=TZ_LEVELING_EXTRAS,
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
# The Act 2 TZ leveling kind's steps after the tombs (loop.py ACT2_TZ, 2026-10-25). The player, ~17:15: "act 2 tz
# leveling: use worlstone shard for act 2 / go all canyon of the magi + all tals rasha tombs (small + kaa + duriel) / go
# full arcane sanctuary (+kill summoner)"; ~17:47: "separate Act 2 TZ Leveling with tal rasha's and arcane sanctuary".
# Its game: the Eastern shard, the Canyon of the Magi (46) and its seven tombs one by one (the "small" ones, the one
# holding Ancient Kaa the Soulless, superuniques.txt "Act 2 Super C", killed by the boss ledger's goals, and the true
# tomb whose Orifice portal leads into Duriel's Lair, 73, Duriel killed), then the Arcane Sanctuary (74) from its own
# waypoint, toured whole (`WHOLE`), the Summoner killed; then the extra acts below, then Save and Exit. No Palace
# Cellars, Harem, Radament, Sewers, rest of act 2, rotation or other act (tzroutine.py `itinerary`, actloop.py `alone`)
TZ_LEVELING_STEPS: tuple[Step, ...] = (Trip('Summoner', 74),)
# The Act 2 TZ leveling game's extra acts (2026-10-26). The player, ~09:00: "let's improve t2 tz leveling with: - if we
# get act 4 extra shard (like now, over 99) - we terrorize it and run baal - if we get act 5 extra shard - we terrorize
# it and do full clear of worldstone keep 2, 3, trone room and baal"; asked whether act 4 meant Baal (act 5's): "act 4
# terrorized: run full CS + Diablo". An extra shard is one over the limit (terrorize.py `over_limit`: its stack at the
# stash's cap, 99, or more carried than its stack has room for, actloop.py CARRIED_COUNT), of these two acts only
# (actloop.py `extra_acts`: "no other shards" still holds for the Western, Southern and another Eastern). Each is used
# as the other kinds' overflow shards are (a carried one first, else one from its stack; at the shard step, a town
# visit, the game's end) once act 2 is terrorized, and its act played after act 2's steps, act 4 before act 5 (the
# overflow's order: the acts after act 2 first), then Save and Exit. "Full" is WHOLE (TZ+, every room toured, as the
# kind's "full arcane sanctuary"), not the Full clear TZ kind's every hostile
CHAOS_SANCTUARY, WORLDSTONE_KEEP_2, WORLDSTONE_KEEP_3 = 108, 129, 130
TZ_LEVELING_EXTRAS: tuple[ActScript, ...] = (
    # Act 4: the River of Flame's waypoint (107), the River only crossed to the Sanctuary (no trip of its own: no River
    # rest, no City of the Damned, no Steppes or Plains), the Chaos Sanctuary toured whole, the seals and Diablo
    ActScript(
        4, alone=(Trip('Diablo', CHAOS_SANCTUARY, waypoint=107, crossed=ONLY),), whole=frozenset((CHAOS_SANCTUARY,))
    ),
    # Act 5: the Worldstone Keep 2 waypoint (129), the Keep 2 and 3 toured whole, the Throne's waves
    # (macros/hunting/throne.py), the portal, Baal in the Worldstone Chamber (132). No Keep 1, halls, Nihlathak or rest
    ActScript(
        5,
        alone=(Trip('Baal', 132, waypoint=WORLDSTONE_KEEP_2, crossed=WORKED),),
        whole=frozenset((WORLDSTONE_KEEP_2, WORLDSTONE_KEEP_3)),
    ),
)

SCRIPT = script()
