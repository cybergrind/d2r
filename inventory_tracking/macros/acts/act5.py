"""Act 5 terrorized by a Northern Worldstone Shard (the kind `act5`, "Shard: Act 5"). The player, 2026-10-20 ~22:50:
"act5: act5 shard -> throne -> baal -> halls -> nihiltak -> rest of zones".

The plan (pinned by tests/inventory_tracking/macros/acts/test_act5.py):
1. Baal from the Worldstone Keep 2 waypoint (129): the Keep 2 and 3 crossed, the Throne's waves, the portal, Baal in
   the Worldstone Chamber. The levels crossed are "rest of zones": their trips come after the halls (`Boss`), not
   right after Baal as act 4's River of Flame.
2. Nihlathak from the Halls of Pain waypoint (123): the Halls of Pain worked on the way, then the Halls of Vaught.
3. The halls above it: up from the Halls of Pain waypoint to the Halls of Anguish and Nihlathak's Temple (Pindleskin).
4. The rest of zones: the Worldstone Keep 2 and 1, then 3; the Frigid Highlands and the Bloody Foothills; then the
   act's other levels (the Arreat Plateau, the Crystalline Passage and the Frozen River, the Glacial Trail and the
   Drifter Cavern, the Frozen Tundra, the Ancients' Way and the Icy Cellar), then the rotation.

Skipped, said in the plan's line: the three red-portal pits (Abaddon 125, the Pit of Acheron 126, the Infernal Pit 127:
their portal object is not read yet, routes/catalog/act5.py UNREAD). Not in the act's zone: the Arreat Summit (120)
and the Worldstone Keep's way down from it.

Live for the first time with this script (2026-10-20): the walks up (123 -> 122 -> 121, 129 -> 128, 111 -> 110) and the
Throne in the shard loop: the waves' wait, the portal's click and Baal (macros/hunting/throne.py, built 2026-10-20
~10:00 and live since 11:02 for any Throne zone; no Throne zone has been played since).
"""

from dataclasses import dataclass

from inventory_tracking.macros.acts.engine import AFTER, WORKED, ActPlan, ActScript, Rest, Trip
from inventory_tracking.macros.tzroutine import crossed_levels


@dataclass(frozen=True)
class Boss(Trip):
    """A boss's trip (`Trip` with AFTER) whose crossed levels wait for "rest of zones" (the player's order puts the
    halls right after Baal): no trip of theirs right after it; a later step or the act's rest takes them."""

    def plan(self, act: ActPlan) -> None:
        if self.missing:
            act.skip(self, self.missing)
            return
        trip = act.route_trip(self.route, self.target, self.waypoint)
        if trip is None:
            return  # said by `route_trip`
        if trip.blockers:
            act.skip(self, trip.blockers[0])
            act.add(trip)
            return
        act.add(trip, frozenset(crossed_levels(trip, self.target, act.zone)))


SCRIPT = ActScript(
    5,
    (
        Boss('Baal', 132, crossed=AFTER),  # the Keep 2 and 3 crossed; the Throne (stand, waves, Lister, portal), Baal
        Trip('Nihlathak', 124, crossed=WORKED),  # the Halls of Pain (123), then Nihlathak in the Halls of Vaught
        Trip('Halls of Anguish', 121, waypoint=123, crossed=WORKED),  # up: 122, then Pindleskin in the Temple (121)
        Trip('Worldstone Keep 1', 128, waypoint=129, crossed=WORKED),  # the Keep 2 crossed to Baal, then up to 1
        # the Keep 3 crossed to Baal, down again from 129 (its way on taken in this game: tzloop.py `reenter`)
        Rest(route='Baal'),
        Trip('Bloody Foothills', 110, waypoint=111, crossed=WORKED),  # the Frigid Highlands, then back to the Foothills
        # then the act's rest (the engine): 112, 113-114, 115-116, 117, 118-119
    ),
    ready=True,
)
