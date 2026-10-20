"""Act 3 terrorized by a Southern Worldstone Shard (the kind `act3`, "Shard: Act 3"). The player, 2026-10-20 ~22:50:
"act3: act3 shard -> durance -> mephisto -> rest of zones"; ~21:27: "for full act TZ we must start with act boss
first".

The plan (pinned by tests/inventory_tracking/macros/acts/test_act3.py): the Durance from its waypoint (Level 2) to
Level 3 and Mephisto, worked on the way (as act 1's "catacombs 2 -> 3 -> 4 -> andariel"); then the rest of the act one
zone at a time, the nearest the Durance first, down the act: Travincal and Durance Level 1 (Travincal's waypoint), the
Causeway's temples (Upper Kurast and the Causeway worked on the first), Upper Kurast's temples, the Bazaar with the
Sewers and its temples, Lower Kurast, the Flayer Jungle with its two dungeons, the Great Marsh, the Spider Forest with
its two caves; then the rotation. Every level of the act is covered: 15 trips, one per waypoint trip, none twice.

Ready 2026-10-20 ~23:40: loop.py REPEATS' TZ_PORTAL raised over the act's 15 trips (it was 13), the Causeway's second
temple by tzloop.py `reenter`.
"""

from inventory_tracking.macros.acts.engine import WORKED, ActScript, Rest, Trip


SCRIPT = ActScript(
    3,
    (
        Trip('Mephisto', 102, waypoint=101, crossed=WORKED),  # Durance 2 -> 3 -> Mephisto (his Red portal home)
        Rest(levels=(83, 100)),  # Travincal (the Council) and Durance 1, from Travincal's waypoint
        Rest(levels=(81, 82, 98, 99)),  # Upper Kurast, the Causeway, the Ruined Fane; then the Disused Reliquary
        Rest(levels=(96, 97)),  # Upper Kurast's temples: the Forgotten Reliquary, the Forgotten Temple
        Rest(levels=(80, 92, 93, 94, 95)),  # the Bazaar and the Sewers, then the Ruined Temple, the Disused Fane
        Rest(levels=(79,)),  # Lower Kurast
        Rest(zone='Act3-FlayerJungle'),  # the Flayer Dungeon (Endugu), then the Swampy Pit
        Rest(zone='Act3-GreatMarsh'),
        Rest(zone='Act3-SpiderForest'),  # the Arachnid Lair, then the Spider Cavern (Sszark)
    ),
    ready=True,
)
