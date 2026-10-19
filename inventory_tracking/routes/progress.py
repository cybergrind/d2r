"""What is done in this game, and the stage each level is at (levels/routes.md, the progress layer).

`current` is pure: a script and this game's facts in (levels entered, objects seen used, bosses dead per
terror/tracker.py `killed`, marks stood at, levels found looted), the next stage out. `clear` is not judged;
`leave` is never done. A stage not judged or not performed yet holds the script, except that a later `use` in
the same level is gone on to (the next seal with the seal boss alive).

`Progress` keeps the facts between presses (the service notes game and level about once a second, the step what
it used). The level card and the teleport step both ask it, so the arrow and the hop agree.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace

from inventory_tracking.levels.model import Lead
from inventory_tracking.routes.model import ENTER, FIGHT, LEAVE, LOOT, STAND, USE, Route, Script, Stage


Place = tuple[float, float]  # where a mark is, in tiles (`Target.point`)


@dataclass(frozen=True)
class Facts:
    entered: frozenset[int] = frozenset()  # the levels the character has been on in this game
    used: frozenset[tuple[int, str, Place]] = frozenset()  # (level, mark, place) of the objects seen operated
    finished: frozenset[tuple[int, str]] = frozenset()  # (level, mark) with each of its objects used
    dead: frozenset[str] | None = None  # the bosses killed, as the routes name them; None: not known
    stood: frozenset[tuple[int, str]] = frozenset()  # (level, mark) the character stood at
    looted: frozenset[int] = frozenset()  # the levels a press found nothing left to pick up on


@dataclass(frozen=True)
class Step:
    """The stage a level is at, with the route and the script it belongs to."""

    route: str
    script: Script
    stage: Stage


def done(area: int, stage: Stage, facts: Facts) -> bool | None:
    """Whether the stage of level `area` is done in this game; None for a stage the facts do not judge yet."""
    if stage.back:
        return False  # the level's way back: the level left, its own script is over
    if stage.tours:
        return set(stage.tours) <= facts.entered
    if stage.to:
        return stage.to in facts.entered
    if stage.kind == USE:
        return (area, stage.mark) in facts.finished
    if stage.kind == FIGHT:
        return None if facts.dead is None else stage.boss in facts.dead
    if stage.kind == STAND:
        return (area, stage.mark) in facts.stood
    if stage.kind == LOOT:
        return area in facts.looted
    return None


def current(script: Script, facts: Facts, performed: frozenset[str] = frozenset()) -> Stage | None:
    """The stage to do next: the first that is not done (one done out of order stays done), or, when
    that one is not performed yet, a later performed `use` of an object of the level. None: the
    script is over."""
    left = [stage for stage in script.stages if not done(script.area, stage, facts)]
    if not left or left[0].kind in performed:
        return left[0] if left else None
    return next((stage for stage in left if stage.kind == USE in performed and not stage.to), left[0])


class Progress:
    def __init__(
        self,
        routes: Iterable[Route],
        performed: frozenset[str] = frozenset((ENTER,)),
        dead: Callable[[], frozenset[str]] | None = None,
        wanted: Callable[[int], bool | None] | None = None,
    ) -> None:
        """`dead`: bosses killed this game (terror/tracker.py `killed`); without it fights are not performed.
        `wanted`: whether a level is terrorized now (terror/tracker.py `terrorized`), for `chosen`."""
        # Level -> (route, main script); the first if the catalogue holds two (routes/check.py refuses that).
        self.scripts: dict[int, tuple[str, Script]] = {}
        # Level -> every script it has, the main one first, each with the levels its route goes on to.
        self.ways: dict[int, list[tuple[str, Script, tuple[int, ...]]]] = {}
        for route in routes:
            for index, script in enumerate(route.scripts):
                ahead = tuple(after.area for after in route.scripts[index + 1 :])
                if not script.alternate and script.area not in self.scripts:
                    self.scripts[script.area] = (route.name, script)
                    self.ways.setdefault(script.area, []).insert(0, (route.name, script, ahead))
                elif script.alternate:
                    self.ways.setdefault(script.area, []).append((route.name, script, ahead))
        self.wanted = wanted
        self.dead = dead
        self.performed = performed if dead is not None else performed - {FIGHT}
        self.game: str | None = None
        self.facts = Facts()  # replaced whole, never changed: read from the macro's thread
        self.selected: dict[int, tuple[str, Script]] = {}

    def note(self, game: str | None, area: int | None) -> None:
        """`game` is None out of a game; `area` is None when the level could not be read."""
        if game != self.game:  # another game, or the menu: nothing of the last one counts
            self.game, self.facts = game, Facts()
            self.selected.clear()
        if game is not None and area is not None and area not in self.facts.entered:
            self.facts = replace(self.facts, entered=self.facts.entered | {area})

    def select_route(self, game: str, area: int, route: str) -> bool:
        """Choose a registered script for an observed area in this game, overriding automatic route selection."""
        if game != self.game or area not in self.facts.entered:
            return False
        matches = [(name, script) for name, script, _ in self.ways.get(area, ()) if name == route]
        if len(matches) != 1:
            return False
        self.selected[area] = matches[0]
        return True

    def chosen(self, area: int) -> tuple[str, Script] | None:
        """(route, script) the level follows: the main one, unless only another route through it goes on to a
        terrorized level (the Barracks from the Outer Cloister with the Jail terrorized)."""
        if area in self.selected:
            return self.selected[area]
        ways = self.ways.get(area)
        if not ways or self.wanted is None or ways[0][1].alternate:
            return self.scripts.get(area)
        wanted = self.wanted
        for name, script, ahead in ways:
            if any(wanted(level) for level in ahead):
                return name, script
        return self.scripts.get(area)

    def step(self, area: int) -> Step | None:
        """The stage level `area` is at; None for a level without a script or with its script over."""
        found = self.chosen(area)
        if found is None:
            return None
        route, script = found
        facts = self.facts if self.dead is None else replace(self.facts, dead=self.dead())
        stage = current(script, facts, self.performed)
        return None if stage is None else Step(route, script, stage)

    def ending(self, area: int) -> bool:
        """Whether only the loot and the leaving are left of level `area`'s script: the macro request leaves the
        game from there, and the pickup key seeks nothing more."""
        step = self.step(area)
        return step is not None and step.stage.kind in (LOOT, LEAVE)

    def used(self, area: int, label: str, place: Place, places: Iterable[Place]) -> None:
        """The object at mark `label`, `place`, was seen operated; the stage is done once all `places` (the
        card's marks with that label) were."""
        used = self.facts.used | {(area, label, place)}
        finished = self.facts.finished
        if all((area, label, each) in used for each in places):
            finished = finished | {(area, label)}
        self.facts = replace(self.facts, used=used, finished=finished)

    def absent(self, area: int, label: str) -> None:
        """Level `area` has no object with mark `label` (levels/model.py `Guidance.absent`): the stage is done."""
        self.facts = replace(self.facts, finished=self.facts.finished | {(area, label)})

    def stood(self, area: int, label: str) -> None:
        """The character stood at mark `label` of level `area`."""
        self.facts = replace(self.facts, stood=self.facts.stood | {(area, label)})

    def looted(self, area: int) -> None:
        """A press found nothing left to pick up on level `area`."""
        self.facts = replace(self.facts, looted=self.facts.looted | {area})

    def done_marks(self, area: int) -> tuple[frozenset[str], frozenset[tuple[str, Place]]]:
        """(labels, (label, place) pairs) of level `area`'s marks done with this game: done stages' marks (a label
        a stage still to do names stays) and objects seen used. The level card drops their rows (levels/guide.py)."""
        found = self.chosen(area)
        if found is None:
            return frozenset(), frozenset()
        _, script = found
        facts = self.facts if self.dead is None else replace(self.facts, dead=self.dead())
        marked = [stage for stage in script.stages if stage.mark]
        left = {stage.mark for stage in marked if not done(area, stage, facts)}
        labels = frozenset(stage.mark for stage in marked if stage.mark not in left)
        places = frozenset((label, place) for level, label, place in facts.used if level == area)
        return labels, places

    def lead(self, area: int) -> Lead | None:
        """The mark the level's card leads with: that of the stage it is at, when the step performs it."""
        step = self.step(area)
        if step is None or step.stage.kind not in self.performed or not step.stage.mark or step.stage.pending:
            return None
        label = step.stage.mark
        skip = frozenset(place for level, mark, place in self.facts.used if (level, mark) == (area, label))
        return Lead(label, step.stage.to or None, skip)
