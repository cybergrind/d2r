"""The Warlock's buff plan (macros/build.py `Buff`, run by macros/buffs.py): which buffs, when and on what.

At a game's start (prebuff): Consume cast anew on a Defiler with one Defiler left out, then Hex: Purge
and Psychic Ward. Outside a fight (upkeep): Hex: Purge and Psychic Ward kept up, Consume cast again
when it has run out. Under the held strike (fight): Hex: Purge and Psychic Ward kept up, Death Mark on
a pack worth it, Sigil: Lethargy under an elite, Engorge on a corpse for the demons. The casts that
are more than one aim and one key are in casters.py.
"""

import math

from inventory_tracking.builds.warlock.echoing_strike.attack import BLADES_A_CAST, ECHOING_STRIKE_ATTACK
from inventory_tracking.builds.warlock.skills import (
    CONSUME,
    DEATH_MARK,
    ENGORGE,
    HEX_PURGE,
    PSYCHIC_WARD,
    SIGIL_LETHARGY,
    SUMMON_DEFILER,
)
from inventory_tracking.combat.policy import observe
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import Buff, BuffFacts, whenever
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.rotation import ELITE_LIFE
from inventory_tracking.macros.routines import DEAD
from inventory_tracking.macros.world import DEFILER_CLASS, Monster, World
from inventory_tracking.native.layout import HIRELING_CLASS_ID


# Engorge (skills.txt 379, cast on a corpse): heals the demons 30% of their life and more, and cuts the damage
# they take for 125 + 75 per level frames; cast under the held strike when a demon is hurt, and for the buff
ENGORGE_SECONDS = 15.0  # between two Engorges for the buff
ENGORGE_HURT_SECONDS = 4.0  # between two while a demon is under ENGORGE_BELOW of its life
ENGORGE_BELOW = 0.7
ENGORGE_REACH = 20.0  # world units: a corpse further off is not looked for
ENGORGE_RETRY = 2.0  # seconds before another look when no corpse lay in reach
ENGORGE_LOOKS = 2  # corpses the pointer is put on for one cast at most
# Hex: Purge (skills.txt 389, a buff of 3600 + 300 per level frames): the strikes do their damage through it,
# so attack mode casts it whenever the state does not show it; unseen casts retry after HEX_RETRY, then every
# HEX_DISTRUST seconds (the executor's rule for a buff whose state reads: macros/buffs.py STATE_RETRY,
# STATE_DISTRUST, STATE_TRIES)
# Psychic Ward (skills.txt 387): a shield that takes the next damage, 15 + 10 per level points and 15 per level of
# Cleave and Levitate (185 for CybergrindAA on 2026-10-12, stats 361 and 362), with no end but being used up.
# Kept up like Hex: Purge (user, 2026-10-12: "we should keep psychic ward buff: probably it will save us
# sometimes"); under the strike not more often than WARD_SECONDS, as a pack breaks it faster than it is cast.
WARD_SECONDS = 5.0
# Death Mark: one monster takes more damage for 125 + 13 per level frames (skills.txt); the strike waits out its cast.
# Only a monster that outlives MARK_CASTS casts is marked; the strike is pressed again under the mark's cast.
MARK_CASTS = 4
DEATH_MARK_SECONDS = 8.0  # between two Death Marks; the debuff lasts 125 + 13/level frames (skills.txt)
SIGIL_SECONDS = 10.0  # between two sigils under the same monster
# Consume (skills.txt 381: 15% more life and a faster run for 300 s at CybergrindAA's level) is cast again by
# attack mode when the character's state reads without it and no hostile is within CONSUME_CLEAR: a Defiler is
# summoned and the pointer put on it, about two seconds in which nothing is struck. After a try that failed
# (no ground for a summon, something beside the Defiler) the next comes CONSUME_RETRY later.
CONSUME_CLEAR = 30.0  # world units
CONSUME_SOON = 3.0  # seconds to the next try after one the player's own key stopped
CONSUME_RETRY = 20.0  # seconds


def purge_shown(world: World) -> bool | None:
    """What the character's state shows of Hex: Purge; None too while it is on no key: not kept up then."""
    player = world.player
    if player is None or HEX_PURGE not in world.slots:
        return None
    return player.hex_purge


def ward_shown(world: World) -> bool | None:
    """What the character's state shows of Psychic Ward; None too while it is on no key: not kept up then."""
    player = world.player
    if player is None or PSYCHIC_WARD not in world.slots:
        return None
    return player.ward


def ward_in_a_fight(facts: BuffFacts) -> bool:
    """Psychic Ward under the strike: the last cast is WARD_SECONDS old."""
    return facts.since(PSYCHIC_WARD) > WARD_SECONDS


def mark_due(facts: BuffFacts) -> bool:
    """Whether a Death Mark is looked for now: the last is DEATH_MARK_SECONDS old and the skill is on a key."""
    return facts.since(DEATH_MARK) > DEATH_MARK_SECONDS and DEATH_MARK in facts.world.slots


def strongest(facts: BuffFacts) -> Monster | None:
    """Whom Death Mark is for: the strongest monster in reach, a pack's leader first, the nearer of two alike."""
    player = facts.world.player
    if player is None or not facts.reachable:
        return None
    here = (player.x, player.y)
    return max(facts.reachable, key=lambda m: (m.leader, m.max_life, -math.dist(here, (m.x, m.y))))


def worth_a_mark(facts: BuffFacts, target: Monster | None) -> bool:
    """Whether `target` outlives MARK_CASTS casts on its line: else the mark costs more casting
    than the damage it adds."""
    world = facts.world
    if world.player is None or target is None:
        return False
    foe = observe(world.player, [target], ()).foes[target.unit_id]
    full = foe.left * (ELITE_LIFE if foe.elite else 1.0)
    return full > MARK_CASTS * BLADES_A_CAST * ECHOING_STRIKE_ATTACK.damage_of(foe.txt)


def sigil_due(facts: BuffFacts) -> bool:
    """Whether a sigil is due under the monster the strike is aimed through: an elite, and the last
    one under it SIGIL_SECONDS old."""
    prey = facts.prey
    return prey is not None and prey.leader and facts.since(SIGIL_LETHARGY, prey.unit_id) > SIGIL_SECONDS


def prey(facts: BuffFacts) -> Monster | None:
    """Whom the sigil is laid under: the monster the strike is aimed through."""
    return facts.prey


def engorge_due(facts: BuffFacts) -> bool:
    """Whether Engorge is worth a cast now: a demon of the character's is out, and it is hurt or
    the last cast is ENGORGE_SECONDS old."""
    world = facts.world
    player = world.player
    if facts.corpses is None or player is None:
        return False
    demons = [
        m
        for m in world.monsters
        if (m.ally or m.owner == player.unit_id or m.txt_id == DEFILER_CLASS) and m.txt_id != HIRELING_CLASS_ID
    ]
    if not demons:
        return False
    hurt = any(m.max_life and m.life < ENGORGE_BELOW * m.max_life for m in demons)
    return facts.since(ENGORGE) > (ENGORGE_HURT_SECONDS if hurt else ENGORGE_SECONDS)


def engorge_on_a_key(facts: BuffFacts) -> bool:
    """Engorge under the strike: on a key, and due."""
    return ENGORGE in facts.world.slots and engorge_due(facts)


def consume_due(facts: BuffFacts) -> bool:
    """Whether attack mode casts Consume again now: the state reads without it, its two skills are on
    keys, no hostile is within CONSUME_CLEAR and the last try is CONSUME_RETRY old."""
    world = facts.world
    player = world.player
    if player is None or player.consume is not False or player.mode in DEAD:
        return False
    if not {CONSUME, SUMMON_DEFILER} <= set(world.slots):
        return False
    if not facts.focused():
        # The game in the background: eleven tries in four minutes, each said and stopped by the lost
        # focus (09:45 to 09:49 on 2026-10-12, the player in another window).
        return False
    if facts.since(CONSUME) <= CONSUME_RETRY:
        return False
    return all(math.dist((player.x, player.y), (m.x, m.y)) > CONSUME_CLEAR for m in facts.foes)


# The plan, each phase in the order it is cast in. The upkeep and the fight keep Hex: Purge and Psychic
# Ward up by what the character's state shows (`state`: the executor's rule for a cast the state does not
# show); the ward's floor of WARD_SECONDS holds only under the strike. Consume has no `state`: it is tried
# every CONSUME_RETRY seconds while it reads missing, by its own `due`. The prebuff casts all three whatever
# the state shows (Consume: how long it has left is not known).
BUFFS: tuple[Buff, ...] = (
    Buff(CONSUME, 'prebuff', whenever, needs='prebuff', caster='defiler dance', also=(SUMMON_DEFILER,)),
    Buff(HEX_PURGE, 'prebuff', whenever, needs='prebuff'),
    Buff(PSYCHIC_WARD, 'prebuff', whenever, needs='prebuff'),
    Buff(HEX_PURGE, 'upkeep', whenever, state=purge_shown),
    Buff(PSYCHIC_WARD, 'upkeep', whenever, state=ward_shown),
    Buff(CONSUME, 'upkeep', consume_due, needs='prebuff', caster='consume', also=(SUMMON_DEFILER,)),
    Buff(HEX_PURGE, 'fight', whenever, state=purge_shown),
    Buff(PSYCHIC_WARD, 'fight', ward_in_a_fight, state=ward_shown),
    Buff(DEATH_MARK, 'fight', mark_due, on='monster', target=strongest, worth=worth_a_mark),
    Buff(SIGIL_LETHARGY, 'fight', sigil_due, on='ground', target=prey, caster='sigil'),
    Buff(ENGORGE, 'fight', engorge_on_a_key, on='corpse', caster='engorge'),
)


class Under:
    """The clock times one skill was last cast under each unit, as a mapping by unit id over the
    executor's memory (`Rotation.sigiled`)."""

    def __init__(self, cast_at: dict[tuple[int, int | None], float], skill: int) -> None:
        self.cast_at, self.skill = cast_at, skill

    def __getitem__(self, unit: int) -> float:
        return self.cast_at[self.skill, unit]

    def __setitem__(self, unit: int, at: float) -> None:
        self.cast_at[self.skill, unit] = at

    def get(self, unit: int, default: float = -math.inf) -> float:
        return self.cast_at.get((self.skill, unit), default)


class Rotation:
    """The executor's memory and the due-tests under the names they had in macros/rotation.py
    (`hunter.rotation` then), for the tests, the replays and the golden adapter written against those:
    each makes it of the hunt's executor (`Rotation(hunter.buffs)`). Nothing in the hunt asks it."""

    def __init__(self, buffs: Buffs) -> None:
        self.buffs = buffs
        self.sigiled = Under(buffs.cast_at, SIGIL_LETHARGY)  # unit id -> clock time of the last sigil under it

    def at(self, skill: int) -> float:
        return self.buffs.cast_at.get((skill, None), -math.inf)

    marked_at = property(lambda self: self.at(DEATH_MARK))  # clock time of the last Death Mark
    # clock time of the last Engorge (or of the last look for a corpse)
    engorged_at = property(
        lambda self: self.at(ENGORGE), lambda self, at: self.buffs.cast_at.__setitem__((ENGORGE, None), at)
    )
    # clock time of the last Hex: Purge cast
    purged_at = property(
        lambda self: self.at(HEX_PURGE), lambda self, at: self.buffs.cast_at.__setitem__((HEX_PURGE, None), at)
    )
    # casts of it in a row that the character's state did not show after
    purges_unseen = property(
        lambda self: self.buffs.unseen.get(HEX_PURGE, 0),
        lambda self, count: self.buffs.unseen.__setitem__(HEX_PURGE, count),
    )
    # the same two of Psychic Ward
    warded_at = property(
        lambda self: self.at(PSYCHIC_WARD), lambda self, at: self.buffs.cast_at.__setitem__((PSYCHIC_WARD, None), at)
    )
    wards_unseen = property(
        lambda self: self.buffs.unseen.get(PSYCHIC_WARD, 0),
        lambda self, count: self.buffs.unseen.__setitem__(PSYCHIC_WARD, count),
    )
    # clock time of attack mode's last try at Consume
    consumed_at = property(
        lambda self: self.at(CONSUME), lambda self, at: self.buffs.cast_at.__setitem__((CONSUME, None), at)
    )

    def row(self, skill: int, phase: str) -> Buff:
        return next(row for row in self.buffs.rows(phase) if row.skill == skill)

    def purge_due(self, run: Run, world: World) -> bool:
        """Whether Hex: Purge is to be cast now: the character's state reads without it."""
        return self.buffs.due(run, self.row(HEX_PURGE, 'upkeep'), self.buffs.facts(run, world)) is not None

    def ward_due(self, run: Run, world: World, *, fighting: bool = False) -> bool:
        """Whether Psychic Ward is to be cast now: the character's state reads without it, and in a
        fight the last cast is WARD_SECONDS old."""
        row = self.row(PSYCHIC_WARD, 'fight' if fighting else 'upkeep')
        return self.buffs.due(run, row, self.buffs.facts(run, world)) is not None

    def sigil_due(self, run: Run, prey: Monster) -> bool:
        nowhere = World(in_game=True, open_panels=(), game_name='', slots=())
        return sigil_due(self.buffs.facts(run, nowhere, prey=prey))

    def engorge_due(self, run: Run, world: World) -> bool:
        return engorge_due(self.buffs.facts(run, world))

    def consume_due(self, run: Run, world: World, foes: list[Monster]) -> bool:
        return consume_due(self.buffs.facts(run, world, foes))

    def worth_a_mark(self, world: World, target: Monster) -> bool:
        return worth_a_mark(BuffFacts(world, 0.0), target)
