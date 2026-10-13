"""The buff executor: how a build's buff plan is run (architecture.md 4.2). Which buffs, when and on
what is the build's (`Build.buffs`, rows of macros/build.py `Buff`); this module names no skill.

`Buffs` keeps when each skill was last cast, on anything and on each unit, and how many casts in a row
a state the game shows did not show after; it answers which row is due now and on what (`due`,
`first`), and makes the cast (`cast`): one key for a row on the character, the pointer on a monster's
body or on the ground under it and then the key, or the caster the row names (`Build.casters`), which
answers with a `Tried`. Under a held strike the key is pressed through (`key`) and the strike taken
up again after (`resume`); the loop that holds the strike decides the order and when to ask.

The prebuff phase (`prebuff`, a game's start) is a routine of its own: every row of it is cast in the
plan's order with the weapon set it needs in hand, each cast waited for; none is asked whether it is
due, and no world is looked at before the first.
"""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace

from inventory_tracking.common import LOG
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.build import Buff, BuffFacts, Build, Casting, Tried
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.pad import MONSTER_UNIT
from inventory_tracking.macros.routines import (
    ACTING,
    LOAD_LIMIT,
    LoadTrace,
    cast as cast_free,
    on_screen,
    press_through,
    screen_fraction,
    take_battle_weapons,
    take_prebuff_weapons,
)
from inventory_tracking.macros.skills import SWAP_WEAPONS, skill_name
from inventory_tracking.macros.teleport import ground_fraction
from inventory_tracking.macros.travel import label, life
from inventory_tracking.macros.world import Monster, World


# The rule for a buff whose state the game shows on the character (`Buff.state`): it is cast whenever the
# state reads without it; a cast the state does not show after is made again after STATE_RETRY seconds, and
# once STATE_TRIES casts in a row were not shown, only every STATE_DISTRUST seconds.
STATE_RETRY = 3.0
STATE_DISTRUST = 60.0
STATE_TRIES = 2
RESUME_WAIT = 0.25  # seconds for the macro's own cast to show before the strike is pressed again


@dataclass(frozen=True)
class Due:
    """A row that is due now: the facts it was asked with, and whom it is cast on."""

    row: Buff
    facts: BuffFacts
    target: Monster | None = None


def keys_of(row: Buff) -> tuple[int, ...]:
    """The skills whose keys a row's cast needs, in the order they are asked for: what its caster
    presses before it, the row's own, and Swap Weapons when it wants a weapon set."""
    return (*row.also, row.skill, *((SWAP_WEAPONS,) if row.needs is not None else ()))


def phase_keys(rows: Iterable[Buff], phase: str) -> tuple[int, ...]:
    """The skills whose keys the rows of one phase need, each once, in the plan's order; Swap Weapons
    last, when a row wants a weapon set."""
    found: list[int] = []
    for row in rows:
        if row.phase == phase:
            found += [skill for skill in keys_of(row) if skill not in found and skill != SWAP_WEAPONS]
    swaps = any(row.phase == phase and row.needs is not None for row in rows)
    return (*found, *((SWAP_WEAPONS,) if swaps else ()))


class Buffs:
    """A build's buff plan as it is run: when each cast was last made, and the casts."""

    def __init__(self, build: Build) -> None:
        self.plan = build.buffs
        self.casters = build.casters
        # (skill, the unit it was cast on or under; None: on anything) -> clock time of the last cast, or
        # of a try a caster had counted as one (`Tried.at`)
        self.cast_at: dict[tuple[int, int | None], float] = {}
        self.unseen: dict[int, int] = {}  # skill -> casts of it in a row that the character's state did not show after
        self.let_go: Callable[[], None] | None = None  # releases the held strike (actuator.hold), while one is held

    def rows(self, phase: str) -> tuple[Buff, ...]:
        """The rows of one phase, in the order they are cast."""
        return tuple(row for row in self.plan if row.phase == phase)

    def facts(
        self,
        run: Run,
        world: World,
        foes: Sequence[Monster] = (),
        reachable: Sequence[Monster] = (),
        prey: Monster | None = None,
    ) -> BuffFacts:
        """What the rows are asked with, from what the caller has read."""
        return BuffFacts(
            world,
            run.clock(),
            tuple(foes),
            tuple(reachable),
            prey,
            self.cast_at,
            focused=run.actuator.focused,
            corpses=run.corpses,
        )

    def missing(self, row: Buff, facts: BuffFacts) -> bool:
        """Whether a row with a state is to be cast by the rule for one: the state reads without it,
        and the last cast is old enough for the casts the state did not show."""
        assert row.state is not None
        shown = row.state(facts.world)
        if shown is not False:
            if shown:
                self.unseen[row.skill] = 0
            return False
        wait = STATE_RETRY if self.unseen.get(row.skill, 0) < STATE_TRIES else STATE_DISTRUST
        return facts.since(row.skill) > wait

    def due(self, run: Run, row: Buff, facts: BuffFacts) -> Due | None:
        """The row with its target if it is to be cast now, by the clock as it reads at this asking:
        its state missing (`missing`), its own `due`, a target where it names one, and `worth`."""
        facts = replace(facts, now=run.clock())
        if row.state is not None and not self.missing(row, facts):
            return None
        if not row.due(facts):
            return None
        target = None
        if row.target is not None:
            target = row.target(facts)
            if target is None:
                return None
        if not row.worth(facts, target):
            return None
        return Due(row, facts, target)

    def first(self, run: Run, phase: str, facts: BuffFacts) -> Due | None:
        """The first row of the phase that is due now, in the plan's order."""
        for row in self.plan:
            if row.phase == phase:
                found = self.due(run, row, facts)
                if found is not None:
                    return found
        return None

    def remember(self, row: Buff, at: float, unit: int | None = None) -> None:
        """The row's skill counted as cast at `at`: on anything, and on `unit` when it had one."""
        self.cast_at[row.skill, None] = at
        if unit is not None:
            self.cast_at[row.skill, unit] = at

    def cast(
        self,
        run: Run,
        due: Due,
        key_names: Callable[..., dict[int, str]],
        aspect: float | None = None,
    ) -> Tried:
        """The cast of a row that is due, by the caster it names or the shared one for what it is cast
        on; what the caster answers is remembered (`Tried`)."""
        row, target = due.row, due.target
        asked = Casting(run, row, self, due.facts.world, target, aspect, key_names)
        tried = self.casters[row.caster](asked) if row.caster is not None else self.shared(asked)
        if tried.at is not None:
            self.remember(row, tried.at, target.unit_id if target is not None else None)
        if tried.cast and row.state is not None:
            self.unseen[row.skill] = self.unseen.get(row.skill, 0) + 1
        return tried

    def shared(self, cast: Casting) -> Tried:
        """The cast that is one aim and one key, by what the row is cast on."""
        if cast.row.on == 'self':
            return self.on_self(cast)
        if cast.row.on == 'monster':
            return self.on_monster(cast)
        if cast.row.on == 'ground':
            return self.on_ground(cast)
        raise ValueError(f'no shared cast on a {cast.row.on}: the row of {skill_name(cast.row.skill)} needs a caster')

    def on_self(self, cast: Casting) -> Tried:
        """A cast on the character itself: one key."""
        run, skill = cast.run, cast.row.skill
        assert cast.world is not None
        assert cast.key_names is not None
        if cast.row.state is not None and self.unseen.get(skill, 0) == STATE_TRIES:
            LOG.warning('Macro: %s cast %d times and the state does not show it', skill_name(skill), STATE_TRIES)
        run.keys.update(cast.key_names(cast.world, (skill,)))
        self.key(run, skill)
        return Tried(run.clock(), cast=True)

    def on_monster(self, cast: Casting) -> Tried:
        """A cast on a monster: the pointer on its body, then the key (Quick Cast)."""
        run, skill, target = cast.run, cast.row.skill, cast.target
        assert target is not None
        assert cast.aspect is not None
        assert cast.key_names is not None
        world = run.world()
        if world.player is None:
            raise Abort('not in a game')
        run.keys.update(cast.key_names(world, (skill,)))
        if run.pad is not None:
            # Controller mode: the client's own target has to name it, else nothing is cast (macros/pad.py).
            here, there = (world.player.x, world.player.y), (target.x, target.y)
            if not run.pad.aim_unit(MONSTER_UNIT, target.unit_id, here, there, label(target)):
                return Tried()
        else:
            point = screen_fraction(world.player, target.x, target.y, cast.aspect)
            if not on_screen(point):
                return Tried()
            run.actuator.aim(*point, scatter=(3, 3))
        if all(m.unit_id != target.unit_id for m in run.world().monsters):
            return Tried()  # it died under the strike while the pointer went over: no mark on a corpse
        self.key(run, skill)
        at = run.clock()
        run.say(f'{skill_name(skill)} on {label(target)}, {life(target)}')
        return Tried(at, cast=True)

    def on_ground(self, cast: Casting) -> Tried:
        """A cast on the ground under a monster: the pointer at its feet, then the key."""
        run, skill, target, world = cast.run, cast.row.skill, cast.target, cast.world
        assert target is not None
        assert cast.aspect is not None
        assert cast.key_names is not None
        assert world is not None
        assert world.player is not None
        run.keys.update(cast.key_names(world, (skill,)))
        if run.pad is not None:
            # Controller mode: a heading; the cast lands at its skill's own distance that way (macros/pad.py).
            run.pad.aim_place((world.player.x, world.player.y), (target.x, target.y))
            self.key(run, skill)
            return Tried(run.clock(), cast=True)
        where = ground_fraction(world.player, target.x, target.y, cast.aspect)
        if not on_screen(where):
            return Tried()
        run.actuator.aim(*where, scatter=(4, 3))
        self.key(run, skill)
        return Tried(run.clock(), cast=True)

    def key(self, run: Run, skill: int) -> None:
        """A cast of the macro's own under the strike: the strike is let go (`let_go`, the fight's) and
        the key pressed at once (routines.press_through); `resume` presses the strike again."""
        if self.let_go is not None:
            self.let_go()
        press_through(run, skill)

    def resume(self, run: Run, again: Callable[[], None] | None) -> None:
        """The held strike pressed again under a cast of the macro's own (a mark, a sigil, Engorge,
        Hex: Purge, Psychic Ward), so the game has it waiting when that cast ends: left alone it stood idle 0.37 s
        at the median after a Death Mark before the hold's own press-again came."""
        if again is None:
            return
        run.seen(lambda w: w.player is not None and w.player.mode in ACTING, RESUME_WAIT)
        again()

    def prebuff(self, run: Run, *, fresh: LoadTrace | None = None) -> None:
        """The prebuff phase: every row of it cast, in the plan's order. The weapon set a row needs is
        taken before it, once for the rows in a row that need the same; after a new game (`fresh`) the
        swap is tried until the game takes input. A row on the character is one key, its cast waited
        for (routines.cast); a row with a caster is the caster's."""
        until = None if fresh is None else fresh.started + LOAD_LIMIT
        held: str | None = None
        for row in self.rows('prebuff'):
            if row.needs is not None and row.needs != held:
                if row.needs == 'prebuff':
                    take_prebuff_weapons(run, until=until)
                else:
                    take_battle_weapons(run)
                held = row.needs
            if row.caster is not None:
                self.casters[row.caster](Casting(run, row, self, fresh=fresh))
            elif row.on == 'self':
                cast_free(run, row.skill)
            else:
                raise ValueError(f'no prebuff cast on a {row.on}: the row of {skill_name(row.skill)} needs a caster')
