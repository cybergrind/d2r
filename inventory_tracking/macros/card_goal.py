"""The level card's goal: the route's next undone goal, the one the macro goes to.

rca/2026-10-14/run-1916-hud-findings.md §1.

The player, 2026-10-14: "probably we need to remove the arrow when the goal is reached/interacted/killed"; the arrow
follows the route's next undone goal, shared with the macros' goal model (goals are separate from navigation, no
level code here), and is hidden when none is left. So the card asks `goals.route_goal`, the function the macro's
`goal_of` asks for the route's part, with what the service knows between presses: the routes' progress, the card's
first mark (the teleport step's, levels/guide.py `target`) and the monster tracker's hostiles (terror/tracker.py
`hostiles`, `remembered`, `supers`). A fight's goal is its boss where the tracker has him; nothing known of him is a
goal not seen (no arrow); `loot`, `leave` and an ended script have no place on the card (no arrow).

What the card no longer shows (`done`): the marks of the stages done (routes/progress.py `done_marks`). Done is seen
whoever acted (`note`, at each guide poll): a level entered (the runner's `Progress.note`), a boss killed (the
tracker), an object of a `use` stage whose mode is no longer 0 (a seal opened by hand counts: R4), and a `stand`
mark with the character within STAND_NEAR of it.
"""

import math
from collections.abc import Callable, Iterable, Sequence

from inventory_tracking.levels.guide import place
from inventory_tracking.levels.model import Poi, Target
from inventory_tracking.macros.goals import STAND_NEAR, Goal, route_goal
from inventory_tracking.macros.route import staged
from inventory_tracking.macros.teleport import USES
from inventory_tracking.macros.travel import STANDING
from inventory_tracking.macros.world import Monster, Thing
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import LEAVE, LOOT, STAND, USE
from inventory_tracking.routes.progress import Place, Progress


Point = tuple[float, float]
NOT_SEEN = 'not seen'  # what a goal with no known place is "toward" on the card: no arrow
# World units: a `use` mark's object is read only with the character this near it. The client holds the objects of
# the rooms loaded around the character, a room (40 units) or two past its own: further off there is none to read,
# and the read is the service's (the macro's process, rca/2026-10-13/latency-findings.md).
OBJECT_NEAR = 120.0


def world_point(mark: Poi) -> Point:
    """A mark's place in world units."""
    x, y = place(mark)
    return x * TILE_UNITS, y * TILE_UNITS


class CardGoals:
    """The route's goal and done marks for the level card (levels/guide.py `goals`). `hostiles(area)`: (unit id,
    txt id, type flags, x, y) of the hostiles the tracker holds alive; `remembered(area)`, `supers(area)`: its
    memory of the level, as the hunt is given them (macros/hunt.py)."""

    def __init__(
        self,
        progress: Progress,
        *,
        hostiles: Callable[[int], Sequence[tuple[int, int, int, float, float]]] | None = None,
        remembered: Callable[[int], Sequence[tuple[int, float, float, bool]]] | None = None,
        supers: Callable[[int], Sequence[Point]] | None = None,
    ) -> None:
        self.progress, self.hostiles, self.remembered, self.supers = progress, hostiles, remembered, supers

    def goal(self, area: int, here: Point, first: Target | None) -> Goal | None:
        """The route's goal on level `area` now, from where the character is (`here`, world units) and the card's
        first mark (`first`); None: nothing to point at (a `loot` or `leave` stage's goal is where the character
        stands: no place to show)."""
        if self.progress.chosen(area) is not None and self.progress.step(area) is None:
            return None  # the level's script is over: no goal left (a level with no script has its card's mark)
        found = staged(self.progress, area)
        foes = [
            Monster(unit, txt, 1, x, y, 0, flags)
            for unit, txt, flags, x, y in (self.hostiles(area) if self.hostiles is not None else ())
        ]
        goal = route_goal(
            here,
            spend=STANDING,
            reach=0.0,
            stage=found[1] if found is not None else None,
            route=found[0] if found is not None else '',
            card=first if first is not None and first.area == area else None,
            foes=foes,
            remembered=self.remembered(area) if self.remembered is not None else (),
            supers=self.supers(area) if self.supers is not None else (),
            # Nothing known of a boss: the card says so, with no arrow (the macro's seek looks for him itself).
            elsewhere=lambda: (here, NOT_SEEN),
        )
        return None if goal is None or goal.do in (LOOT, LEAVE) else goal

    def done(self, area: int) -> tuple[frozenset[str], frozenset[tuple[str, Place]]]:
        """(labels, (label, place)) of the marks done with on level `area` (routes/progress.py `done_marks`)."""
        return self.progress.done_marks(area)

    def wanted(self, area: int, here: Point, marks: Iterable[Poi]) -> frozenset[int]:
        """The object classes whose modes say a `use` stage's mark is done, among `marks` not seen used yet within
        OBJECT_NEAR of the character (`here`): the guide reads those objects at its poll (nothing: no read)."""
        labels, places = self.done(area)
        stages = self._marks(area, USE)
        return frozenset(
            mark.use
            for mark in marks
            if mark.use in USES
            and not USES[mark.use].leaves
            and mark.label in stages
            and mark.label not in labels
            and (mark.label, place(mark)) not in places
            and math.dist(here, world_point(mark)) <= OBJECT_NEAR
        )

    def note(self, area: int, here: Point, marks: Sequence[Poi], things: Sequence[Thing]) -> bool:
        """Tell the progress what the guide's poll sees done, whoever did it: a stage's object operated (`things`,
        the objects of the classes `wanted` asked for) and a `stand` stage's mark stood at. True: progress changed."""
        before = self.progress.facts
        uses, stands = self._marks(area, USE), self._marks(area, STAND)
        for mark in marks:
            spot = world_point(mark)
            stood = (area, mark.label) in self.progress.facts.stood
            if mark.label in stands and not stood and math.dist(here, spot) <= STAND_NEAR:
                self.progress.stood(area, mark.label)
            use = USES.get(mark.use)
            if use is None or use.leaves or mark.label not in uses:
                continue
            if (area, mark.label, place(mark)) in self.progress.facts.used:
                continue
            if any(t.txt_id == mark.use and t.mode and math.dist((t.x, t.y), spot) <= use.near for t in things):
                same = tuple(place(other) for other in marks if other.label == mark.label)
                self.progress.used(area, mark.label, place(mark), same)
        return self.progress.facts is not before

    def _marks(self, area: int, kind: str) -> frozenset[str]:
        """The marks the stages of `kind` of level `area`'s script name."""
        found = self.progress.chosen(area)
        stages = found[1].stages if found is not None else ()
        return frozenset(stage.mark for stage in stages if stage.kind == kind and stage.mark)
