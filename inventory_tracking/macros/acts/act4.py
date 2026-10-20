"""Act 4 terrorized by a Deep Worldstone Shard (the kind `act4`, "Shard: Act 4"). The player, 2026-10-20 ~21:27: "for
full act TZ we must start with act boss first. In our case: we must go river of flame -> CS -> kill diablo -> do rest
of flame river -> city of damned/planes of despair and etc".

The plan (live since 21:42 on 2026-10-20; pinned by tests/inventory_tracking/macros/acts/test_act4.py): Diablo from the
River of Flame's waypoint (the River crossed), the River's rest, the City of the Damned, then the Steppes and the
Plains (Izual, walked out of the Fortress), then the rotation.
"""

from inventory_tracking.macros.acts.engine import AFTER, ActScript, Rest, Trip


SCRIPT = ActScript(
    4,
    (
        Trip('Diablo', 108, crossed=AFTER),  # the River of Flame's waypoint (107), the seals, Diablo; the River after
        Rest(route='Diablo'),  # the City of the Damned (106)
        # then the act's rest: the Outer Steppes and the Plains of Despair, Izual (the route `Izual` from 103)
    ),
    ready=True,
)
