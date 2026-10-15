"""What is done in this game, and the stage each level is at (levels/routes.md, the progress layer).

`current` is the pure part: a script and the facts of this game in, the stage to do next out. The facts:
- the levels entered: a way on (`enter`, or a `use` of a portal) is done once its level was;
- the objects the step saw operated: a `use` of a chest or a seal is done once each mark with its
  label was;
- the bosses dead (the monster tracker's word, terror/tracker.py `killed`): a `fight` is done once
  its boss is; without that word a fight is not judged;
- where the character stood (`stand`) and the levels whose ground a press found clean (`loot`).
`clear` is not judged, and `leave` is never done: the game ends.

A stage that is not judged or not performed yet holds the script, with one exception: a later
`use` of an object of the same level is gone on to (the next seal with the seal boss alive, the
chest past Snapchip Shatter). Nothing else is: not the way out, and not the loot or the leaving.

`Progress` keeps the facts between presses, as `macros/journey.py` keeps the level come from: the
service notes the game and the level about once a second, the step what it used. The level card and
the teleport step both ask it, so the arrow and the hop agree. A card leads with a stage's mark only
when the step performs that kind of stage (`performed`) and the stage is not `pending`; at any other
stage the card keeps the order its handler gives.
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
        """`dead`: the bosses killed this game by name (terror/tracker.py `killed`). Without it a fight
        cannot be seen to end, so it is not performed: the card keeps its own order there.
        `wanted`: whether a level is terrorized now (terror/tracker.py `terrorized`): it chooses
        between a level's scripts (`chosen`)."""
        # Level -> (route, its main script): the first, should the catalogue hold two (routes/check.py refuses that).
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

    def note(self, game: str | None, area: int | None) -> None:
        """`game` is None out of a game; `area` is None when the level could not be read."""
        if game != self.game:  # another game, or the menu: nothing of the last one counts
            self.game, self.facts = game, Facts()
        if game is not None and area is not None and area not in self.facts.entered:
            self.facts = replace(self.facts, entered=self.facts.entered | {area})

    def chosen(self, area: int) -> tuple[str, Script] | None:
        """(route, script) the level follows: its main script, unless none of the levels the main
        route goes on to is terrorized and those of another route through this level are (the
        Barracks from the Outer Cloister with the Jail terrorized, the Burial Grounds from the Cold
        Plains). The level itself says nothing: every script of it starts there."""
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
        """Whether the route is at its end on level `area`: what is left of its script is the loot and
        the leaving (every way on taken, every object used, every boss dead). The macro request leaves
        the game from there, and the pickup key seeks nothing more."""
        step = self.step(area)
        return step is not None and step.stage.kind in (LOOT, LEAVE)

    def used(self, area: int, label: str, place: Place, places: Iterable[Place]) -> None:
        """The step saw the object at mark `label`, at `place`, operated; `places`: every mark the
        level's card holds with that label. With each of them used the stage is done."""
        used = self.facts.used | {(area, label, place)}
        finished = self.facts.finished
        if all((area, label, each) in used for each in places):
            finished = finished | {(area, label)}
        self.facts = replace(self.facts, used=used, finished=finished)

    def absent(self, area: int, label: str) -> None:
        """Level `area` has no object with mark `label` (its card knows: levels/model.py `Guidance.absent`): the
        stage is done with, as with each of them used."""
        self.facts = replace(self.facts, finished=self.facts.finished | {(area, label)})

    def stood(self, area: int, label: str) -> None:
        """The character stood at mark `label` of level `area`."""
        self.facts = replace(self.facts, stood=self.facts.stood | {(area, label)})

    def looted(self, area: int) -> None:
        """A press found nothing left to pick up on level `area`."""
        self.facts = replace(self.facts, looted=self.facts.looted | {area})

    def done_marks(self, area: int) -> tuple[frozenset[str], frozenset[tuple[str, Place]]]:
        """(labels, (label, place) pairs) of level `area`'s card marks that are done with in this game: the marks
        of its script's stages that are done (`done`; a label a stage still to do names stays), and the objects
        seen used (a hell pit's chest of several). The level card drops their rows (levels/guide.py)."""
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
