"""What a farming route is: plain data (levels/routes.md, the catalogue layer).

A route is a chain of level scripts; a script is the ordered stages of one level. The stage that is
not done yet is the one a press performs (routes/progress.py, macros/route.py: later phases). A
stage names a mark by the label the level's handler gives it (levels/handlers/), so the catalogue
holds no coordinates. Nothing here reads memory or sends input.

Stages:
- `enter(mark, to)`: go to the door, gap or border the mark is on and into level `to`.
- `use(mark)`: go to the object the mark sits on and click it; with `to`, it is a portal to that
  level. A label that marks several objects (a hell pit's chests) means each of them.
- `stand(mark, by)`: move onto the mark, with skill `by` when one is given.
- `fight(boss, at, opener)`: go to mark `at` (none: fight from where the character stands), cast
  the opener once, then attack mode until the boss is dead.
- `clear()`: the seek step, until no elite is known and no room is unexplored.
- `loot()`: the pickup request, until nothing valuable is left in reach.
- `leave()`: the macro request: save, leave the game, make the next one.

`pending` says why a stage cannot be acted on yet (no mark for it, an object not read); the check
(routes/check.py) refuses a pending stage whose mark has come to exist, so the list only shrinks.
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

    def text(self) -> str:
        """The stage as the route table prints it."""
        words = {
            ENTER: f'enter {self.mark}',
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
