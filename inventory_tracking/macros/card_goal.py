"""The level card's goal (the route's next undone goal, the one the macro goes to) and its done marks.

The player, 2026-10-14: "probably we need to remove the arrow when the goal is reached/interacted/killed"
(rca/2026-10-14/run-1916-hud-findings.md §1). The card asks `goals.route_goal`, as the macro's `goal_of` does, with
what the service knows between presses: route progress, the card's first mark and the tracker's hostiles. No known
place, `loot`, `leave` or an ended script: no arrow.

Done is noted whoever acted (`note`, each guide poll): a level entered, a boss killed, a `use` object whose mode left
0 (a seal opened by hand counts), a `stand` mark within STAND_NEAR.
"""

import math
from collections.abc import Callable, Iterable, Sequence

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Monster, Thing
from inventory_tracking.levels.geometry import Point
from inventory_tracking.levels.guide import place
from inventory_tracking.levels.model import Poi, Target
from inventory_tracking.macros.goals import STAND_NEAR, Goal, route_goal
from inventory_tracking.macros.route import staged
from inventory_tracking.macros.teleport import USES, classes
from inventory_tracking.macros.travel import STANDING
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import LEAVE, LOOT, STAND, USE
from inventory_tracking.routes.progress import Place, Progress


NOT_SEEN = 'not seen'  # what a goal with no known place is "toward" on the card: no arrow
# World units: a `use` mark's object is read only this near; the client holds objects a room (40) or two around.
OBJECT_NEAR = 120.0


def world_point(mark: Poi) -> Point:
    """A mark's place in world units."""
    x, y = place(mark)
    return x * TILE_UNITS, y * TILE_UNITS


class CardGoals:
    """The route's goal and done marks for the level card (levels/guide.py `goals`). `hostiles(area)`: (unit, txt,
    flags, x, y) alive in the tracker; `remembered`, `supers`: its memory of the level, as the hunt gets them."""

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
        """The route's goal on `area` from `here` (world units) and the card's first mark; None: nothing to point at."""
        if self.progress.chosen(area) is not None and self.progress.step(area) is None:
            return None  # script over (a level with no script keeps its card's mark)
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
            elsewhere=lambda: (here, NOT_SEEN),
        )
        return None if goal is None or goal.do in (LOOT, LEAVE) else goal

    def done(self, area: int) -> tuple[frozenset[str], frozenset[tuple[str, Place]]]:
        """(labels, (label, place)) of the marks done on `area`."""
        return self.progress.done_marks(area)

    def wanted(self, area: int, here: Point, marks: Iterable[Poi]) -> frozenset[int]:
        """Object classes the guide's poll should read: those of `use` marks not yet done within OBJECT_NEAR."""
        labels, places = self.done(area)
        stages = self._marks(area, USE)
        return frozenset(
            kind
            for mark in marks
            if mark.use in USES
            and not USES[mark.use].leaves
            and mark.label in stages
            and mark.label not in labels
            and (mark.label, place(mark)) not in places
            and math.dist(here, world_point(mark)) <= OBJECT_NEAR
            for kind in classes(mark.use)
        )

    def note(self, area: int, here: Point, marks: Sequence[Poi], things: Sequence[Thing]) -> bool:
        """Note what the poll sees done: a `use` object operated (`things`, of the `wanted` classes), a `stand` mark
        stood at. True: progress changed."""
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
            # The nearest of its classes, as `marked_thing`: a jar opened beside the chest is not the chest.
            near = [t for t in things if t.txt_id in classes(mark.use) and math.dist((t.x, t.y), spot) <= use.near]
            nearest = min(near, key=lambda t: math.dist((t.x, t.y), spot)) if near else None
            if nearest is not None and nearest.mode:
                same = tuple(place(other) for other in marks if other.label == mark.label)
                self.progress.used(area, mark.label, place(mark), same)
        return self.progress.facts is not before

    def absent(self, area: int, labels: frozenset[str]) -> bool:
        """Mark `use` stages absent whose label the level lacks (`Guidance.absent`: Lower Kurast without a camp), so
        the run ends at the loot. True: progress changed."""
        found = self.progress.chosen(area)
        changed = False
        for label in sorted(labels & self._marks(area, USE)):
            if (area, label) in self.progress.facts.finished:
                continue
            self.progress.absent(area, label)
            LOG.info('Macro: route %s: no %s on this level', found[0] if found is not None else area, label)
            changed = True
        return changed

    def _marks(self, area: int, kind: str) -> frozenset[str]:
        """Marks named by the `kind` stages of `area`'s script."""
        found = self.progress.chosen(area)
        stages = found[1].stages if found is not None else ()
        return frozenset(stage.mark for stage in stages if stage.kind == kind and stage.mark)
