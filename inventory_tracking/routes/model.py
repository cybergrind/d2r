"""What a farming route is: plain data (levels/routes.md, the catalogue layer); no memory reads, no input.

A route is a chain of level scripts, a script the ordered stages of one level. Stages name marks by the
handler's label (levels/handlers/), so the catalogue holds no coordinates: `enter(mark, to)` into level `to`;
`use(mark)` an object (with `to`, a portal; a label on several objects means each); `stand(mark, by)` with skill
`by`; `fight(boss, at, opener)`; `clear()` the seek step; `loot()` the pickup request; `leave()` the next game.
`pending` says why a stage cannot be acted on yet; routes/check.py refuses one whose mark has come to exist.
"""

from dataclasses import dataclass


ENTER, USE, STAND, FIGHT, CLEAR, LOOT, LEAVE = 'enter', 'use', 'stand', 'fight', 'clear', 'loot', 'leave'

# skills.txt ids of the skills a stage may name (the same as macros/skills.py; a test holds them equal).
BLADE_WARP = 390
DEATH_MARK = 375
SIGIL_LETHARGY = 393


@dataclass(frozen=True)
class Stage:
    kind: str
    mark: str = ''  # the handler's label of the mark gone to
    to: int = 0  # the level this stage leads into (enter; use of a portal)
    boss: str = ''  # fight: the boss as the elite table names it (terror/data/elites.json), or an act boss
    by: int = 0  # stand: the skill that makes the move
    opener: tuple[int, ...] = ()  # fight: skills cast once before attack mode
    pending: str = ''  # why the stage cannot be acted on yet
    # enter: the levels a tour of this label's marks leads into one by one (the Canyon's seven tombs); done once
    # each was entered
    tours: tuple[int, ...] = ()
    back: bool = False  # enter: a way back the level's run takes at its end; never done while on the level

    def text(self) -> str:
        """The stage as the route table prints it."""
        words = {
            ENTER: f'tour {self.mark}' if self.tours else f'back to {self.mark}' if self.back else f'enter {self.mark}',
            USE: f'use {self.mark}',
            STAND: f'stand at {self.mark}',
            FIGHT: f'fight {self.boss}',
            CLEAR: 'clear',
            LOOT: 'loot',
            LEAVE: 'leave',
        }[self.kind]
        return f'{words} (pending)' if self.pending else words


def enter(mark: str, to: int, pending: str = '') -> Stage:
    return Stage(ENTER, mark, to, pending=pending)


def tour(mark: str, areas: tuple[int, ...]) -> Stage:
    """Every mark labelled `mark` gone through, one by one, the nearest not yet taken first: done once each level of
    `areas` was entered."""
    return Stage(ENTER, mark, tours=areas)


def back(mark: str, to: int) -> Stage:
    """The way back to level `to` at mark `mark`, taken when the level is done (its full clear first)."""
    return Stage(ENTER, mark, to, back=True)


def use(mark: str, to: int = 0, pending: str = '') -> Stage:
    return Stage(USE, mark, to, pending=pending)


def stand(mark: str, by: int = 0, pending: str = '') -> Stage:
    return Stage(STAND, mark, by=by, pending=pending)


def fight(boss: str, at: str = '', opener: tuple[int, ...] = (), pending: str = '') -> Stage:
    return Stage(FIGHT, at, boss=boss, opener=opener, pending=pending)


def clear() -> Stage:
    return Stage(CLEAR)


def loot() -> Stage:
    return Stage(LOOT)


def leave() -> Stage:
    return Stage(LEAVE)


@dataclass(frozen=True)
class Script:
    """One level's stages. `alternate`: another route's way through a level whose main script goes elsewhere."""

    area: int
    stages: tuple[Stage, ...]
    alternate: bool = False

    @property
    def way_on(self) -> Stage | None:
        """The stage that leaves for another level, if the script has one."""
        return next((stage for stage in self.stages if stage.to), None)


def level(area: int, *stages: Stage, alternate: bool = False) -> Script:
    return Script(area, stages, alternate)


@dataclass(frozen=True)
class Route:
    """`starts`: the waypoint levels the route may be begun at: levels of its own, or the town next to its first."""

    name: str
    starts: tuple[int, ...]
    scripts: tuple[Script, ...]
