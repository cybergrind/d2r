"""The buff executor: runs a build's buff plan (architecture.md 4.2). Which buffs, when and on what is the build's
(`Build.buffs`, macros/build.py `Buff`); this module names no skill.

`Buffs` keeps the last cast of each skill (on anything and per unit) and the casts a shown state did not follow; it
answers which row is due (`due`, `first`) and casts it (`cast`): a key on the character, the pointer on a monster or
the ground then the key, or the row's caster (`Build.casters`). Under a held strike the key is pressed through (`key`)
and the strike resumed (`resume`). `prebuff` casts every prebuff row in order, each waited for, none asked if due.

A buff that ends by itself (`Buff.lasts`) is renewed when it would lapse inside the fight ahead (`BuffFacts.ahead`):
Consume ran out in Diablo's fight (rca/2026-10-14/run-1214-findings.md §3.4).
"""

import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace

from inventory_tracking.common import LOG
from inventory_tracking.game.layout import MONSTER_UNIT
from inventory_tracking.game.records import Monster, World
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.build import Buff, BuffFacts, Build, Casting, DrawPrice, Tried
from inventory_tracking.macros.engine import Run
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


# A buff with a shown state (`Buff.state`) is cast while the state is off; an unshown cast is retried after
# STATE_RETRY s, and after STATE_TRIES unshown casts only every STATE_DISTRUST s.
STATE_RETRY = 3.0
STATE_DISTRUST = 60.0
STATE_TRIES = 2
RESUME_WAIT = 0.25  # seconds for the macro's own cast to show before the strike is pressed again
# Defer side drops (not potions) while the run's boss is in reach (rca/2026-10-18/andariel-cadence-findings.md §2.4).
# No sigil skip: the player wants Sigil on all strong enemies (2026-10-18, the F3 trial ended).
QUIET_BY_THE_BOSS = True
HURT_SECONDS = 2.0  # life lost this recently hurts: macros/hunt.py HURT_SECONDS (a test holds them equal)
LIFE_LOOK = 0.25  # seconds between two reads of the life for `Buffs.hurt` (`Run.loot` reads the drops with it)


@dataclass(frozen=True)
class Due:
    """A row that is due now: the facts it was asked with, and whom it is cast on."""

    row: Buff
    facts: BuffFacts
    target: Monster | None = None


def lapsing(row: Buff, facts: BuffFacts) -> bool:
    """Whether `row`'s self-ending buff would end inside the fight ahead; False with no fight or no known cast."""
    if row.lasts is None or facts.ahead <= 0:
        return False
    left = facts.left(row.skill, row.lasts)
    return left is not None and left < facts.ahead


def keys_of(row: Buff) -> tuple[int, ...]:
    """The skills a row's cast needs keys for: its caster's, its own, then Swap Weapons if it wants a set."""
    return (*row.also, row.skill, *((SWAP_WEAPONS,) if row.needs is not None else ()))


def phase_keys(rows: Iterable[Buff], phase: str) -> tuple[int, ...]:
    """The skills one phase's rows need keys for, each once, in plan order; Swap Weapons last."""
    found: list[int] = []
    for row in rows:
        if row.phase == phase:
            found += [skill for skill in keys_of(row) if skill not in found and skill != SWAP_WEAPONS]
    swaps = any(row.phase == phase and row.needs is not None for row in rows)
    return (*found, *((SWAP_WEAPONS,) if swaps else ()))


def worn_cta(run: Run) -> bool | None:
    """Whether the run's character wears a Call to Arms (`Run.cta`); None: not known."""
    found = getattr(run, 'cta', None)
    return found() if found is not None else None


class Buffs:
    """A build's buff plan as it is run: when each cast was last made, and the casts."""

    def __init__(self, build: Build) -> None:
        self.plan = build.buffs
        self.casters = build.casters
        # (skill, unit or None for anything) -> clock of the last cast (or a caster's counted try, `Tried.at`)
        self.cast_at: dict[tuple[int, int | None], float] = {}
        self.unseen: dict[int, int] = {}  # skill -> casts of it in a row that the character's state did not show after
        self.let_go: Callable[[], None] | None = None  # releases the held strike (actuator.hold), while one is held
        self.refusals: set[tuple[int, int]] = set()  # (skill, unit) a refusal of `Buff.worth` was said for
        self.told: set[tuple[int, int]] = set()  # (skill, unit) a row's `Buff.told` line was said for
        # skill -> clock of its last cast that took: a self-ending buff's age; shared via `Run.lasting` (`took_of`)
        self.took: dict[int, float] = {}
        # `hurt`'s last life read, its clock, and when life last went down
        self.life_seen: int | None = None
        self.life_read_at = -math.inf
        self.hurt_at = -math.inf

    def took_of(self, run: Run) -> dict[int, float]:
        """The casts that took, merged into the runner's cross-run record (`Run.lasting`) once a run brings it."""
        lasting = getattr(run, 'lasting', None)
        if lasting is not None and lasting is not self.took:
            for skill, at in self.took.items():
                if at > lasting.get(skill, -math.inf):
                    lasting[skill] = at
            self.took = lasting
        return self.took

    @property
    def quiet_by_the_boss(self) -> bool:
        """Whether the hunt defers side drops while its boss is in reach (macros/hunting/choice.py `side_drop`)."""
        return QUIET_BY_THE_BOSS

    def hurt(self, run: Run) -> bool:
        """Whether life went down within HURT_SECONDS (hunting/judging.py `safety_priced`'s rule), read at most every
        LIFE_LOOK s. Unknown counts as hurt: no read, or below full with no recent read to compare."""
        now = run.clock()
        if now - self.life_read_at >= LIFE_LOOK:
            loot = run.reads.loot()
            seen = None
            if loot is None or loot.max_life <= 0 or loot.life <= 0:
                self.hurt_at = now
            else:
                before = self.life_seen if now - self.life_read_at <= HURT_SECONDS else None
                if loot.life < (before if before is not None else loot.max_life):
                    self.hurt_at = now
                seen = loot.life
            self.life_seen, self.life_read_at = seen, now
        return now - self.hurt_at <= HURT_SECONDS

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
        draws: Mapping[int, DrawPrice] | None = None,
        ahead: float = 0.0,
    ) -> BuffFacts:
        """The facts rows are asked with. `draws`: the safety pricing's fresh draw prices (macros/safety.py);
        `ahead`: seconds of fight expected ahead, which a self-ending buff must last through."""
        return BuffFacts(
            world,
            run.clock(),
            tuple(foes),
            tuple(reachable),
            prey,
            self.cast_at,
            focused=run.actuator.focused,
            corpses=run.corpses,
            cta=worn_cta(run),
            draws=draws,
            ahead=ahead,
            took=self.took_of(run),
            hurt=lambda: self.hurt(run),
        )

    def missing(self, row: Buff, facts: BuffFacts) -> bool:
        """Whether a stated row is due by the state rule (STATE_RETRY / STATE_DISTRUST)."""
        assert row.state is not None
        shown = row.state(facts.world)
        if shown is not False:
            if shown:
                self.unseen[row.skill] = 0
            return False
        wait = STATE_RETRY if self.unseen.get(row.skill, 0) < STATE_TRIES else STATE_DISTRUST
        return facts.since(row.skill) > wait

    def due(self, run: Run, row: Buff, facts: BuffFacts) -> Due | None:
        """The row with its target if due now: state missing, its own `due`, a target if it names one, `worth`."""
        facts = replace(facts, now=run.clock())
        facts = replace(facts, lapsing=lapsing(row, facts))
        if row.state is not None and not self.missing(row, facts):
            return None
        if not row.due(facts):
            return None
        if row.passed is not None:
            for monster, said in row.passed(facts):
                self.say_once(row, monster, said)
        target = None
        if row.target is not None:
            target = row.target(facts)
            if target is None:
                return None
        if not row.worth(facts, target):
            self.say_refused(row, facts, target)
            return None
        return Due(row, facts, target)

    def say_refused(self, row: Buff, facts: BuffFacts, target: Monster | None) -> None:
        """Log a `worth` refusal once per target (`Buff.refused`)."""
        if row.refused is None or target is None or (row.skill, target.unit_id) in self.refusals:
            return
        said = row.refused(facts, target)
        if said is not None:
            self.say_once(row, target, said)

    def say_once(self, row: Buff, monster: Monster, said: str) -> None:
        """Log a row's line about `monster` once per monster and row."""
        if (row.skill, monster.unit_id) in self.refusals:
            return
        if len(self.refusals) > 400:
            self.refusals.clear()
        self.refusals.add((row.skill, monster.unit_id))
        LOG.info('%s', said)

    def tell_once(self, row: Buff, monster: Monster, told: str | None) -> None:
        """Log a cast's `Buff.told` line once per monster and row."""
        if told is None or (row.skill, monster.unit_id) in self.told:
            return
        if len(self.told) > 400:
            self.told.clear()
        self.told.add((row.skill, monster.unit_id))
        LOG.info('%s', told)

    def first(self, run: Run, phase: str, facts: BuffFacts, *, renewing: bool = False) -> Due | None:
        """The first due row of the phase, in plan order. `renewing`: only `lapsing` rows."""
        for row in self.plan:
            if renewing and not lapsing(row, replace(facts, now=run.clock())):
                continue
            if row.phase == phase:
                found = self.due(run, row, facts)
                if found is not None:
                    return found
        return None

    def remember(self, row: Buff, at: float, unit: int | None = None) -> None:
        """Count the row's skill cast at `at`, on anything and on `unit`."""
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
        """Cast a due row by its caster or the shared one; the answer (`Tried`) is remembered."""
        row, target = due.row, due.target
        if due.facts.lapsing:
            left = due.facts.left(row.skill, row.lasts) if row.lasts is not None else None
            LOG.info(
                'Macro: buff: %s has %.0f s left of %.0f, under the %.0f s fight ahead: cast again now',
                skill_name(row.skill), left if left is not None else 0.0, row.lasts or 0.0, due.facts.ahead,
            )  # fmt: skip
        asked = Casting(run, row, self, due.facts.world, target, aspect, key_names)
        tried = self.casters[row.caster](asked) if row.caster is not None else self.shared(asked)
        if tried.at is not None:
            self.remember(row, tried.at, target.unit_id if target is not None else None)
        if tried.cast and tried.at is not None:
            self.took[row.skill] = tried.at
        if tried.cast and target is not None and row.said is not None:
            said = row.said(due.facts, target)
            if said is not None:
                LOG.info('%s', said)
        if tried.cast and target is not None and row.told is not None:
            self.tell_once(row, target, row.told(due.facts, target))
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
        if self.by_key(run, skill):
            return Tried(run.clock(), cast=True)
        self.key(run, skill)
        return Tried(run.clock(), cast=True)

    def state_of(self, skill: int) -> Callable[[World], bool | None] | None:
        """The first plan row's state reader for `skill`; None if no row has one."""
        return next((row.state for row in self.plan if row.skill == skill and row.state is not None), None)

    def by_key(self, run: Run, skill: int) -> bool:
        """In controller mode, cast a self buff as the key route's due probe (pad.py `PadActs.probe_key`); whether
        it was."""
        state = self.state_of(skill)
        if run.pad is None or state is None or not run.pad.route.due(run.world().game_name):
            return False
        if self.let_go is not None:
            self.let_go()
        run.expect('character ready', lambda w: w.player is not None and w.player.mode not in ACTING, 2.5)
        return run.pad.probe_key(skill, lambda: state(run.world()))

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
            # Controller mode: the client's own target must name it, else nothing is cast.
            here, there = (world.player.x, world.player.y), (target.x, target.y)
            if not run.pad.aim_unit(MONSTER_UNIT, target.unit_id, here, there, label(target)):
                return Tried()
        else:
            point = screen_fraction(world.player, target.x, target.y, cast.aspect)
            if not on_screen(point):
                # Once a target: a due cast not made is never silent (the player, 2026-10-20: "never death marked
                # the leader"; rca/2026-10-20/leader-not-marked-findings.md)
                self.say_once(
                    cast.row, target,
                    f'Macro: buff: no {skill_name(skill)} on {label(target)}, {life(target)}: its body is off the '
                    f'screen at ({point[0]:.2f}, {point[1]:.2f})',
                )  # fmt: skip
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
            # Controller mode: a heading; the cast lands at the skill's own distance.
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
        """Press `skill` through a held strike: let it go, press the key (routines.press_through)."""
        if self.let_go is not None:
            self.let_go()
        press_through(run, skill)

    def resume(self, run: Run, again: Callable[[], None] | None) -> None:
        """Press the held strike again during the macro's own cast, so it is waiting when the cast ends (else a
        median 0.37 s idle after a Death Mark)."""
        if again is None:
            return
        run.seen(lambda w: w.player is not None and w.player.mode in ACTING, RESUME_WAIT)
        again()

    def prebuff(self, run: Run, *, fresh: LoadTrace | None = None) -> None:
        """Cast every prebuff row in plan order, swapping weapon sets as rows need them (after a new game, `fresh`,
        until the game takes input). Self rows wait for their cast; caster rows are the caster's."""
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
                tried = self.casters[row.caster](Casting(run, row, self, fresh=fresh))
                took = tried.at if tried.cast else None
            elif row.on == 'self':
                if not self.by_key(run, row.skill):
                    cast_free(run, row.skill)
                took = run.clock()
            else:
                raise ValueError(f'no prebuff cast on a {row.on}: the row of {skill_name(row.skill)} needs a caster')
            if took is not None:
                self.took_of(run)[row.skill] = took  # its age: a renewal of a buff that ends (`lapsing`)
