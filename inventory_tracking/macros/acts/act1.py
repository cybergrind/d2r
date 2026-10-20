"""Act 1 terrorized by a Western Worldstone Shard (the kind `act1`, "Shard: Act 1"). The player, 2026-10-20 ~22:50:
"act1: act1 shard -> catacombs 2 -> 3 -> 4 -> andariel -> marsh -> tower -> countess -> rest of zones one
by one".

The plan (pinned by tests/inventory_tracking/macros/acts/test_act1.py): Andariel from the Catacombs 2 waypoint (35),
Catacombs 2-4 worked on the way; the Countess from the Black Marsh waypoint (6), the Marsh, the Forgotten Tower (20:
no handler, its stairs are the DS1 warp's generic mark 'Tower Cellar 1') and Tower Cellar 1-5 worked on the way; then
the act's other zones one by one, each finished before the next, nearest Andariel first: the rest of the Tower (the
Hole), of the Catacombs (Inner Cloister, Cathedral, Catacombs 1), the Jail (Barracks, Jail 1-3), the Monastery (Outer
Cloister, Gate, Tamoe Highland, the Pit), the Dark Wood (Underground Passage), Tristram (Stony Field), the Burial
Grounds (Crypt, Mausoleum, Blood Raven), the Cold Plains (the Cave) and the Blood Moor (Den of Evil, walked out of the
Rogue Encampment). Every one of the act's 37 levels has a trip.

Ready 2026-10-20 ~23:30: the Burial Grounds' second trip from the Cold Plains (the Mausoleum's, after the Crypt's)
had no way on, the stage `enter Burial Grounds` judged done by the first entry (routes/progress.py `done`); macros/
tzloop.py `reenter` makes it the way on again, and the walk test passes.
"""

from inventory_tracking.macros.acts.engine import WORKED, ActScript, Rest, Trip


SCRIPT = ActScript(
    1,
    (
        Trip('Andariel', 37, waypoint=35, crossed=WORKED),  # "catacombs 2 -> 3 -> 4 -> andariel"
        Trip('Countess', 25, waypoint=6, crossed=WORKED),  # "marsh -> tower -> countess"
        # "rest of zones one by one": each zone finished before the next, nearest Andariel first
        Rest(zone='Act1-Tower'),  # the Hole (11, 15), from the Black Marsh again
        Rest(zone='Act1-Catacombs'),  # Inner Cloister, Cathedral, Catacombs 1 (32-34), from the Inner Cloister
        Rest(zone='Act1-Jail'),  # Barracks, Jail 1-3 (28-31), from the Outer Cloister
        Rest(zone='Act1-Monastery'),  # Monastery Gate, Tamoe Highland, Pit 1-2 (26, 7, 12, 16)
        Rest(zone='Act1-DarkWood'),  # Dark Wood, Underground Passage 1-2 (5, 10, 14)
        Rest(zone='Act1-Tristram'),  # Stony Field, Tristram (4, 38)
        Rest(zone='Act1-BurialGrounds'),  # Cold Plains, Burial Grounds, Crypt, Mausoleum (3, 17, 18, 19)
        Rest(zone='Act1-ColdPlains'),  # the Cave 1-2 (9, 13)
        Rest(zone='Act1-BloodMoor'),  # Blood Moor, Den of Evil (2, 8), walked out of the Rogue Encampment
    ),
    ready=True,
)
