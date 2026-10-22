"""The Warlock's buff plan (macros/build.py `Buff`, run by macros/buffs.py): which buffs, when and on what.

Prebuff: Consume on a Defiler with one Defiler left out, Hex: Purge, Psychic Ward. Upkeep: Battle Command and
Battle Orders from a Call to Arms (macros/cta.py), Hex: Purge and Psychic Ward kept up, Consume again when run out,
a Defiler when none is alive. Fight: Engorge first for a pet in danger or among a dangerous pack (pets.py watches the
pets' life), Hex: Purge and Psychic Ward, a Defiler where it pays (defiler.py `price`),
Death Mark (mark.py), Bind Demon again in a tier 4-5 Herald pack fight (bind.py), Sigil: Lethargy under an elite or
at a tier 4-5 Herald pack's densest disc, Engorge on a corpse. Multi-step casts are in casters.py.
"""

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

from inventory_tracking.builds.warlock import pets
from inventory_tracking.builds.warlock.bind import bind_due, bind_said, bind_target
from inventory_tracking.builds.warlock.defiler import defiler_missing, worth_a_defiler
from inventory_tracking.builds.warlock.mark import (
    MARK_LEADERS,
    MARK_RECASTS,
    MARK_SHOWS,
    herald,
    mark_due,
    mark_passed,
    mark_refusal,
    mark_said,
    mark_shows,
    mark_told,
    state_on,
    target,
    worth_a_mark,
)
from inventory_tracking.builds.warlock.skills import (
    BIND_DEMON,
    CONSUME,
    DEATH_MARK,
    ENGORGE,
    HEX_PURGE,
    PSYCHIC_WARD,
    SIGIL_LETHARGY,
    SUMMON_DEFILER,
)
from inventory_tracking.combat import pack as herald_pack
from inventory_tracking.game.layout import DEFILER_CLASS
from inventory_tracking.game.records import Monster, World
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import Buff, BuffFacts, whenever
from inventory_tracking.macros.cta import ROWS as CTA_ROWS
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.goals import is_boss
from inventory_tracking.macros.routines import DEAD
from inventory_tracking.native.layout import DEAD_MODES, HIRELING_CLASS_ID
from inventory_tracking.terror.danger import DANGER, Unit, table as threat_table, threat


# Engorge (skills.txt 379, on a corpse): heals the demons and cuts the damage they take; cast when a demon is hurt
# and for the buff
ENGORGE_SECONDS = 15.0  # between two Engorges for the buff
ENGORGE_HURT_SECONDS = 4.0  # between two while a demon is under ENGORGE_BELOW of its life
ENGORGE_BELOW = 0.7
ENGORGE_REACH = 20.0  # world units: a corpse further off is not looked for
ENGORGE_RETRY = 2.0  # seconds before another look when no corpse lay in reach
ENGORGE_LOOKS = 2  # corpses the pointer is put on for one cast at most
# Engorge only where it does some good and can land (the player, 2026-10-20 ~23:20, of the batch identify: "we're not
# wasting time identifying individually every separate item but doing batch when we actually need it", "I like how it
# feels in time and fast", "I'd like to see more this kind of mindset in other areas"; rca/2026-10-20/
# lazy-work-findings.md §2). Engorge gives the character nothing (skills.txt 379: pettype demon, requirespettype): it
# heals the demon (calc1 ln34: 30% of its life, 1% more a level) and buffs it (aurastate engorge for ln56 frames:
# damage resist, life drain, attack rate, Blood Oath's armour and regeneration), for mana.
#
# A monster's life reads in 128ths of its maximum (stat 6 >> 8, the client's, "79/128" in the logs) and a pet's
# maximum in whole points: CybergrindAA's Defiler read 128 of 230 at full life (86% of its frames in the takes
# 20261020T2*, its life never over 128), so by `life < ENGORGE_BELOW * max_life` it was always hurt and Engorge came
# every ENGORGE_HURT_SECONDS instead of ENGORGE_SECONDS: 276 casts and 165 tries that missed an hour (probe.log of
# 22:00-23:57). True: hurt by its life against the client's LIFE_SHARE (`demon_hurt`): 14 of the takes' 447 tries
# had one hurt, and a replay of them leaves 155 of 340 casts. False: against max_life, as before.
ENGORGE_LIFE_SHARE = True
LIFE_SHARE = 128  # a monster's life as the client holds it: 128ths of its maximum
# No Engorge for the buff alone (a demon hurt still gets one) while a fight ends: ENGORGE_ENDING_FOES hostiles or
# fewer left, none a leader or a boss. 28-31% of the casts of 2026-10-20 came in the last 1.5 s before "Nothing left
# in reach"; the buff runs out on the way to the next fight. The replay of the takes (with ENGORGE_LIFE_SHARE): 155
# casts become 139, those in a fight's last 1.5 s 34 become 16. To be judged by kills/h and Summon Defiler casts/h.
# False: the buff cast whatever is left.
ENGORGE_SPARE_ENDS = False
ENGORGE_ENDING_FOES = 2
# A pet in danger gets Engorge first and fast (the player, 2026-10-21 ~15:45, of the bound Urdar lost to a tier 5 Dark
# Archer Herald pack: "heavy hitting enemies, several engagements without healing him and monitoring of his health /
# could be very easily avoided if we just have use engorge"; rca/2026-10-21/demon-lost-findings.md). The Urdar went
# 128 -> 0 in 12 s, 94/128 in 4 s, with one Engorge landed: ENGORGE_HURT_SECONDS gave one heal a life bar. True: a pet
# under ENGORGE_BELOW or falling (pets.py PET_FALL in PET_FALL_SECONDS) has Engorge due before the fight's other casts
# (`engorge_first`, the first fight row) every ENGORGE_DANGER_SECONDS, and a dead pet asks for none (`engorged`).
# The buff alone stays lazy (ENGORGE_SECONDS, ENGORGE_SPARE_ENDS, the batch reasoning above): over today's 142 takes a
# pet is in danger ~21 s an hour, ~35 casts. False: ENGORGE_HURT_SECONDS for a hurt pet, last in the fight, as before.
PET_ENGORGE = True
# Seconds between two Engorges while a pet is in danger: about one cast (0.32 s, the sigil's median from a free
# character) and a look either side; its heal shows 0.1-0.3 s after the key (the take's one heal), so the look before
# the next knows whether the last took.
ENGORGE_DANGER_SECONDS = 0.6
# After PET_UNHEALED Engorges in a row that brought no heal (pets.py `judge`), ENGORGE_UNHEALED_SECONDS between two: a
# life read wrong, or no corpse the cast can take, is not cast at every 0.6 s.
PET_UNHEALED = 4
ENGORGE_UNHEALED_SECONDS = 2.0
# Engorge for its buff first where the pack is dangerous (the player, 2026-10-21 ~15:45: "herald was a t5 dark archier
# - these especially dangerous"): with a tier 4-5 Herald's pack among the foes (combat/pack.py `in_pack`), or heavy
# hitters near a pet (`heavy`: terror/danger.py's threat of the hostiles within PET_HEAVY_REACH of one at the deadly
# packs' caution line, DANGER.caution), Engorge is due first at the fight's start and again every ENGORGE_PACK_SECONDS
# while it lasts. Its buff (skills.txt 379 aurastate engorge for ln56 frames: Param5 125 + Param6 75 a level, 5 s at
# level 1; damage resist, life drain, attack rate) and its heal (30%+, 38/128) every 5 s cover the take's pack's rate
# on their own (94/128 in 4 s). Over today's takes heavy hitters stood within 20 of a pet 1.1% of the pet-time (Blood
# Lords, dolls, Horrors, Dark Archers, the Council): ~19 casts in 2.3 h. False: the buff by ENGORGE_SECONDS alone.
ENGORGE_PACK_FIRST = True
ENGORGE_PACK_SECONDS = 5.0
PET_HEAVY_REACH = 20.0  # world units from a pet within which a hostile's threat counts
PET_HEAVY = DANGER.caution
# Hex: Purge (skills.txt 389): the strikes deal their damage through it, so it is cast whenever the state lacks it
# (macros/buffs.py STATE_RETRY). Psychic Ward (skills.txt 387, a pool used up by damage) is kept up the same way
# (user, 2026-10-12: "we should keep psychic ward buff: probably it will save us sometimes"), under the strike no
# more often than WARD_SECONDS: a pack breaks it faster than it is cast.
WARD_SECONDS = 5.0
# Death Mark: mark.py (what it buys, when it is cast, its numbers).
SIGIL_SECONDS = 10.0  # between two sigils under the same monster
# Under a Herald (macros/hunt.py HERALD_OMEN) a sigil goes first and again this often: the Herald moves off it (the
# player, 2026-10-18: "prioritizing keeping herald on sigil lethargy + death mark")
HERALD_SIGIL_SECONDS = 6.0
# Sigil: Lethargy's ground (pricing/raw/game-excel, read 2026-10-20). skills.txt 393: srvmissilea/b/c
# sigillethargysmall, medium and large by level (prgcalc1: 1 below 10, 2 below 20, 3 after), calc3 "Missile Limit" 1
# (each new sigil ends the last: seen in every take), auratargetstate sigillethargy on the monsters within
# aurarangecalc (4, 6 at level 10, 8 at 20).
SIGIL_MISSILES = {699: 4.0, 686: 6.0, 702: 8.0}  # missiles.txt *ID -> its Radius in world units: small, medium, large
SIGIL_STATE = 192  # states.txt sigillethargy: set on a monster that stands in the sigil
# CybergrindAA's: the medium missile in every take of 2026-10-20 (level 10-19), so radius 6 (its state is on 84% of
# the live monsters under 6 units from it in the state words of 2026-10-20's last 60 takes, 26% of those 6-7 away, 2%
# of those 7-15 away), and its time:
# missiles.txt Range 100 + 25 a level frames, 475 at level 15 (18.94-18.98 s in the takes).
SIGIL_RADIUS = 6.0
SIGIL_LASTS = 19.0  # seconds
# Kept in its sigil (the player, 2026-10-20 ~23:05, of Diablo's fight at 23:01:55, whose one sigil lay 11 units off him
# from its start: "for hard/dangerous enemies - we want to keep them under sigil's effect all the time"). A dangerous
# monster (`dangerous`) gets a sigil again as soon as it stands outside the one that lies (its state words lack
# SIGIL_STATE, or it stands further than the sigil's radius from it) or that one runs out (SIGIL_LASTS),
# never sooner than SIGIL_GAP after the last; a Herald also HERALD_SIGIL_SECONDS after the last under it, as before.
# Others are left as they were: a leader that is not dangerous by SIGIL_SECONDS, trash none (casters.py `sigil`).
# False: SIGIL_SECONDS and HERALD_SIGIL_SECONDS alone, as before.
SIGIL_KEEPS = True
# The player, 2026-10-21 ~20:42: "we can put sigil in advance before herald's packa spawning. then we could reposition
# in if required". A Herald's pack shows 5.0 s after its omen (macros/hunt.py HERALD_OMEN; 4.95-5.35 s over the 81
# tier 4-5 spawns of 2026-10-21's takes) and first acts a median 0.5 s after; 61% of it stands within 6 of the spot in
# its first second, 43% at 2-4 s (rca/2026-10-21/arachnid-herald-2-findings.md, "sigil before the spawn"). True: with an
# omen pending within OMEN_SIGIL_REACH and no member of a tier 4-5 pack in reach, the sigil goes at the omen's spot,
# once an omen (`omen_anchor`, casters.py `omen_sigil`); it lasts SIGIL_LASTS, the pack shows within 5 s. False: the
# sigil waits for the pack, as before.
OMEN_SIGIL = False
OMEN_SIGIL_REACH = 22.0  # units: the strike's reach (hunting/base.py OMEN_STAND 20 + a margin): the spot on screen
OMEN_TXT = -1  # the txt id of the stand-in a pending omen is laid under (no monster stands there yet)
OMEN_UNIT = 0xFFFF0000  # the stand-ins' unit ids from here up, one a spot
SIGIL_LOOK = 0.5  # seconds between two looks whether a dangerous monster still stands in its sigil
# Seconds between two sigils at least. One cast is 0.32 s (the median of 48 from a free character in the takes of
# 2026-10-20), its missile shows 0.37 s after the key (the median of 1,957; p95 0.48 s) and its state on a monster
# 0.48 s after (the median of 1,719; p95 0.67 s).
SIGIL_GAP = 1.0
SIGIL_SHOWS = 0.8  # seconds after the key before the sigil's state or missile is looked for
# Seconds before the sigil runs out that the next is cast: a look comes within SIGIL_LOOK, the new missile shows a
# median 0.37 s after its key (p95 0.48 s), so the new one lies before the last one ends.
SIGIL_EARLY = 1.0
SIGIL_EDGE = 0.5  # world units inside the radius that count as out: a walking monster is out within the next look
SIGIL_UNSHOWN = 2  # sigils under a monster in a row whose state it never showed: then it is judged by place alone
UNSHOWN = 'its state words show no sigil'  # `keep_reason`'s words for that
TICK = 0.01  # seconds past a clock that a test of "older than" holds at
# Consume (skills.txt 381) is cast again when the state lacks it and no hostile is within CONSUME_CLEAR: about two
# seconds of summon and aim in which nothing is struck.
CONSUME_CLEAR = 30.0  # world units
CONSUME_SECONDS = 300.0  # one cast's time (skills.txt 381 at CybergrindAA's level): its row's `lasts`
CONSUME_SOON = 3.0  # seconds to the next try after one the player's own key stopped, or a fight (casters.py)
CONSUME_RETRY = 20.0  # seconds
# The player, 2026-10-21 ~21:02: "also, T5 herald fight - we stood and do NOTHING under the fire, not damaging anything
# for solid 15 seconds" (rca/2026-10-21/consume-in-fight-findings.md). At 20:59:03.66 Consume ran out 17 units from a
# Herald's pending omen (read at 20:58:59.68: the pack 5 s on) with nothing within CONSUME_CLEAR; the renewal began,
# the tier 5 pack (15 Flayers) showed within 30 0.07 s later and the Herald was first struck 8.5 s after. True: no
# renewal while a Herald omen is pending within CONSUME_OMEN_REACH (combat/pack.py `omens`): its pack is the fight
# coming, and the renewal waits for the quiet after it (the max life 8.5% lower meanwhile: 2661 for 2907 in the take).
# False: the omen is not looked at, as before.
CONSUME_OMEN_DEFER = True
# Units: the run waits at the omen stand, 24 from its spot (combat/pack.py PACK_OMEN_STAND), and an omen is read on the
# screen (hunt.py `omens_now`), so one this near is the fight coming here.
CONSUME_OMEN_REACH = 60.0


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


def herald_in_reach(facts: BuffFacts) -> Monster | None:
    """The nearest Herald in the attack's reach (mark.py `herald`), None with none."""
    player = facts.world.player
    found = [m for m in facts.reachable if herald(m)]
    if player is None or not found:
        return None
    return min(found, key=lambda m: math.dist((player.x, player.y), (m.x, m.y)))


def dangerous(monster: Monster) -> bool:
    """A monster kept in its sigil (SIGIL_KEEPS): a Herald, an act boss or super unique (Izual, the Countess, ...), or a
    pack's leader while Death Mark goes on leaders (mark.py MARK_LEADERS)."""
    return herald(monster) or is_boss(monster) or (MARK_LEADERS and monster.leader)


def kept(monster: Monster) -> bool:
    """Whether `monster` is kept in its sigil: SIGIL_KEEPS on and it is `dangerous`."""
    return SIGIL_KEEPS and dangerous(monster)


def pack_anchor(facts: BuffFacts) -> Monster | None:
    """The member of a tier 4-5 Herald pack in reach the pack's sigil row is asked with (combat/pack.py SIGIL_COVER;
    casters.py `pack_sigil` finds where it goes): the Herald, else the nearest; None with none or the switch off."""
    player = facts.world.player
    if not herald_pack.SIGIL_COVER or player is None:
        return None
    found = [m for m in facts.reachable if herald_pack.in_pack(m.tier)]
    if not found:
        return None
    here = (player.x, player.y)
    return min(found, key=lambda m: (not herald(m), math.dist(here, (m.x, m.y))))


def omen_anchor(facts: BuffFacts) -> Monster | None:
    """A stand-in at the spot of a pending Herald omen within OMEN_SIGIL_REACH (combat/pack.py `omens`), its sigil
    not laid yet, with no member of a tier 4-5 pack in reach (OMEN_SIGIL); None else."""
    player = facts.world.player
    if not OMEN_SIGIL or player is None or any(herald_pack.in_pack(m.tier) for m in facts.reachable):
        return None
    here = (player.x, player.y)
    for spot in herald_pack.omens(facts.now):
        if math.dist(here, spot) > OMEN_SIGIL_REACH:
            continue
        unit = OMEN_UNIT + (int(spot[0]) * 7919 + int(spot[1])) % 0xFFFF
        if facts.since(SIGIL_LETHARGY, unit) == math.inf:
            return Monster(unit, OMEN_TXT, 1, spot[0], spot[1])
    return None


def sigil_due(facts: BuffFacts) -> bool:
    """Whether the sigil's caster is asked now: with a tier 4-5 Herald pack in reach every SIGIL_LOOK s (the caster
    judges the cover, `pack_anchor`); else under a Herald in reach, else under the monster the strike is aimed
    through, an elite or boss. One kept in its sigil (`kept`) is looked at every SIGIL_LOOK s (casters.py `sigil` asks
    whether it still stands in one); else its last one is SIGIL_SECONDS old (a Herald's HERALD_SIGIL_SECONDS)."""
    if pack_anchor(facts) is not None:
        return facts.since(SIGIL_LETHARGY) > SIGIL_LOOK
    if omen_anchor(facts) is not None:
        return facts.since(SIGIL_LETHARGY) > SIGIL_GAP
    first = herald_in_reach(facts)
    if first is not None:
        every = SIGIL_LOOK if kept(first) else HERALD_SIGIL_SECONDS
        return facts.since(SIGIL_LETHARGY, first.unit_id) > every
    prey = facts.prey
    if prey is None or not (prey.leader or (SIGIL_KEEPS and is_boss(prey))):
        return False
    return facts.since(SIGIL_LETHARGY, prey.unit_id) > (SIGIL_LOOK if kept(prey) else SIGIL_SECONDS)


Place = tuple[float, float]


@dataclass
class SigilWatch:
    """The executor's memory of the one sigil of the character's that lies (skills.txt calc3: each new sigil ends the
    last), for the monsters kept in it (casters.py `sigil`)."""

    at: float | None = None  # clock of its key
    place: Place | None = None  # where it was aimed, world units
    unit: int | None = None  # the monster it was laid under
    area: int | None = None  # its level: one left behind lies no more
    under: dict[int, float] = field(default_factory=dict)  # unit -> clock of the last sigil laid under it
    unshown: dict[int, int] = field(default_factory=dict)  # unit -> its sigils in a row its state did not show

    def lay(self, unit: int, place: Place, area: int | None, at: float) -> None:
        if len(self.under) > 400:
            self.under.clear()
            self.unshown.clear()
        self.at, self.place, self.unit, self.area = at, place, unit, area
        self.under[unit] = at

    def lies(self, now: float, area: int | None) -> bool:
        """Whether the last sigil may lie still: laid in this level within SIGIL_LASTS (a clock that went back is
        another game's)."""
        return self.at is not None and area == self.area and 0.0 <= now - self.at <= SIGIL_LASTS

    def age(self, now: float) -> float:
        return now - self.at if self.at is not None else math.inf

    def next_due(self, monster: Monster) -> float:
        """The clock `keep_reason` holds a sigil due by its time alone: the last one about to run out (SIGIL_EARLY),
        a Herald's last HERALD_SIGIL_SECONDS old; inf with none laid."""
        if self.at is None:
            return math.inf
        due = self.at + SIGIL_LASTS - SIGIL_EARLY
        if herald(monster):
            due = min(due, self.under.get(monster.unit_id, -math.inf) + HERALD_SIGIL_SECONDS)
        return due + TICK


def keep_reason(
    watch: SigilWatch,
    monster: Monster,
    now: float,
    area: int | None,
    words: bytes | None = None,
    lying: tuple[float, float, float] | None = None,
    seen: bool = False,
) -> str | None:
    """Why a monster kept in its sigil gets one now; None while it stands in the one that lies. `words`: its state words
    (None: unread); `lying`: the sigil's missile as read, (x, y, radius), with `seen` that the missiles were read at
    all (none of the character's lying then is no sigil). Neither is asked within SIGIL_SHOWS of the key."""
    if not watch.lies(now, area):
        return 'no sigil of the character lies'
    age = watch.age(now)
    if herald(monster) and now - watch.under.get(monster.unit_id, -math.inf) > HERALD_SIGIL_SECONDS:
        return f'the last under the Herald is over {HERALD_SIGIL_SECONDS:.0f} s old'
    if age > SIGIL_LASTS - SIGIL_EARLY:
        return f'the sigil runs out in {max(0.0, SIGIL_LASTS - age):.1f} s'
    judged = age >= SIGIL_SHOWS
    if judged and words is not None and watch.unshown.get(monster.unit_id, 0) < SIGIL_UNSHOWN:
        if state_on(words, SIGIL_STATE):
            watch.unshown.pop(monster.unit_id, None)
            return None
        return f'{UNSHOWN} (state {SIGIL_STATE})'
    if judged and seen and lying is None:
        return 'no sigil of the character is in flight'
    if judged and lying is not None:
        x, y, radius = lying
    elif watch.place is not None:
        (x, y), radius = watch.place, SIGIL_RADIUS
    else:
        return 'the sigil lies nowhere known'
    away = math.dist((monster.x, monster.y), (x, y))
    if away > radius - SIGIL_EDGE:
        return f'it stands {away:.1f} from the sigil at ({x:.1f}, {y:.1f}), radius {radius:.0f}'
    return None


def prey(facts: BuffFacts) -> Monster | None:
    """Whom the sigil is laid under: a tier 4-5 Herald pack's anchor (`pack_anchor`: the caster lays it at the pack's
    disc), else a Herald in reach, else the monster the strike is aimed through."""
    return pack_anchor(facts) or omen_anchor(facts) or herald_in_reach(facts) or facts.prey


def engorged(world: World) -> list[Monster]:
    """The units Engorge is for: the character's own and the Defilers, not the mercenary; with PET_ENGORGE not a dead
    one (the Urdar's corpse counted as a hurt demon for four tries after its death, 15:41:43-50)."""
    player = world.player
    if player is None:
        return []
    return [
        m
        for m in world.monsters
        if (m.ally or m.owner == player.unit_id or m.txt_id == DEFILER_CLASS)
        and m.txt_id != HIRELING_CLASS_ID
        and not (PET_ENGORGE and pets.dead(m))
    ]


def hurt(monster: Monster) -> bool:
    """Whether a demon is under ENGORGE_BELOW of its life: by the client's 128ths (ENGORGE_LIFE_SHARE), else by its
    max_life as read."""
    if not monster.max_life:
        return False
    whole = min(monster.max_life, LIFE_SHARE) if ENGORGE_LIFE_SHARE else monster.max_life
    return monster.life < ENGORGE_BELOW * whole


def demon_hurt(world: World) -> bool:
    """Whether a demon Engorge is for is hurt (`hurt`)."""
    return any(hurt(m) for m in engorged(world))


def engorge_every(world: World) -> float:
    """Seconds between two Engorges now: ENGORGE_HURT_SECONDS while a demon is hurt, else ENGORGE_SECONDS. Without
    ENGORGE_LIFE_SHARE always the first, as the casters counted before."""
    if not ENGORGE_LIFE_SHARE:
        return ENGORGE_HURT_SECONDS
    return ENGORGE_HURT_SECONDS if demon_hurt(world) else ENGORGE_SECONDS


def fight_ending(facts: BuffFacts) -> bool:
    """Whether the fight the look is of ends soon (ENGORGE_SPARE_ENDS): a prey struck, ENGORGE_ENDING_FOES hostiles or
    fewer left, none a leader or a boss. Outside a fight (no prey) never."""
    if facts.prey is None or len(facts.foes) > ENGORGE_ENDING_FOES:
        return False
    return not any(m.leader or is_boss(m) for m in facts.foes)


def engorge_due(facts: BuffFacts) -> bool:
    """Whether Engorge is worth a cast now: a demon of the character's is out, and it is hurt (`hurt`) or the last
    cast is ENGORGE_SECONDS old and the fight does not end (`fight_ending`, ENGORGE_SPARE_ENDS)."""
    world = facts.world
    if facts.corpses is None or world.player is None:
        return False
    demons = engorged(world)
    if not demons:
        return False
    if any(hurt(m) for m in demons):
        return facts.since(ENGORGE) > ENGORGE_HURT_SECONDS
    if ENGORGE_SPARE_ENDS and fight_ending(facts):
        return False
    return facts.since(ENGORGE) > ENGORGE_SECONDS


def engorge_on_a_key(facts: BuffFacts) -> bool:
    """Engorge under the strike: on a key, and due."""
    return ENGORGE in facts.world.slots and engorge_due(facts)


def danger_every(watch: pets.PetWatch) -> float:
    """Seconds between two Engorges while a pet is in danger: ENGORGE_DANGER_SECONDS, ENGORGE_UNHEALED_SECONDS after
    PET_UNHEALED that brought no heal."""
    return ENGORGE_DANGER_SECONDS if watch.unhealed < PET_UNHEALED else ENGORGE_UNHEALED_SECONDS


def named(found: Sequence[Monster]) -> str:
    """'15 Dark Archer': the count and the most common kind of `found`."""
    txt = Counter(m.txt_id for m in found).most_common(1)[0][0]
    row = threat_table().monsters.get(txt)
    return f'{len(found)} {row.name if row is not None else f"monster {txt}"}'


def heavy(hostiles: Sequence[Monster]) -> float:
    """What `hostiles` threaten together by terror/danger.py's table (hit x rate x reach, raised by rank, a Herald's
    tier, modifiers and auras); 0 for kinds it has no row for."""
    units = [Unit(m.unit_id, m.txt_id, m.x, m.y, m.modifiers, flags=m.flags, tier=m.tier) for m in hostiles]
    return sum(threat(unit, units, threat_table(), DANGER)[0] for unit in units)


def pack_danger(facts: BuffFacts) -> str | None:
    """Why the fight is dangerous to the pets alive, in words (ENGORGE_PACK_FIRST): a tier 4-5 Herald's pack among
    the foes, else heavy hitters near a pet (`heavy` at PET_HEAVY within PET_HEAVY_REACH); None else."""
    live = pets.alive(facts.world)
    if not live:
        return None
    foes = [m for m in facts.foes if m.mode not in DEAD_MODES]
    pack = [m for m in foes if herald_pack.in_pack(m.tier)]
    if pack:
        return f'a tier {max(m.tier for m in pack)} Herald pack ({named(pack)})'
    near = [m for m in foes if any(math.dist((m.x, m.y), (p.x, p.y)) <= PET_HEAVY_REACH for p in live)]
    score = heavy(near) if near else 0.0
    if score < PET_HEAVY:
        return None
    return f'heavy hitters ({named(near)}, threat {score:.1f} within {PET_HEAVY_REACH:.0f})'


def engorge_first(facts: BuffFacts) -> bool:
    """Engorge before the fight's other casts (the first fight row; the pets watched at every look, pets.py): a pet in
    danger (PET_ENGORGE: under ENGORGE_BELOW of its life or falling) every `danger_every` s, else a dangerous pack
    (ENGORGE_PACK_FIRST, `pack_danger`) every ENGORGE_PACK_SECONDS. Its lines (pets.py PET_LINES) say the pet's life."""
    world = facts.world
    if world.player is None:
        return False
    watch = pets.watch_of(facts.cast_at)
    perils = watch.look(world, facts.now, ENGORGE_BELOW)
    pets.pull(watch, facts.now, world)  # the fight pulled off the bound demon while no Engorge lands (pets.py PET_PULL)
    able = ENGORGE in world.slots and facts.corpses is not None
    if perils:
        watch.tell(perils, facts.now, 'Engorge now' if able and PET_ENGORGE else 'no Engorge now')
        if PET_ENGORGE:
            return able and facts.since(ENGORGE) > danger_every(watch)
    if not (ENGORGE_PACK_FIRST and able) or facts.since(ENGORGE) <= ENGORGE_PACK_SECONDS:
        return False
    why = pack_danger(facts)
    if why is None:
        return False
    watch.tell_pack(world, why, facts.now)
    watch.pack_at = facts.now
    return True


def consume_due(facts: BuffFacts) -> bool:
    """Whether attack mode casts Consume again now: the state lacks it, or it would end inside the boss's fight ahead
    (`BuffFacts.lapsing`, rca/2026-10-14/run-1214-findings.md §3.4); both skills on keys, no hostile within
    CONSUME_CLEAR, no Herald coming within CONSUME_OMEN_REACH (CONSUME_OMEN_DEFER), the last try CONSUME_RETRY old."""
    world = facts.world
    player = world.player
    if player is None or player.mode in DEAD:
        return False
    if not (player.consume is False or (player.consume is True and facts.lapsing)):
        return False
    if not {CONSUME, SUMMON_DEFILER} <= set(world.slots):
        return False
    if not facts.focused():
        # The game in the background: every try would be stopped by the lost focus.
        return False
    if facts.since(CONSUME) <= CONSUME_RETRY:
        return False
    here = (player.x, player.y)
    if CONSUME_OMEN_DEFER and any(math.dist(here, spot) <= CONSUME_OMEN_REACH for spot in herald_pack.omens(facts.now)):
        return False
    return all(math.dist(here, (m.x, m.y)) > CONSUME_CLEAR for m in facts.foes)


# The plan, each phase in casting order. Hex: Purge and Psychic Ward by the character's state (`state`); Consume by
# its own `due` and `lasts` (its time left is not read). The prebuff casts all three whatever the state shows.
BUFFS: tuple[Buff, ...] = (
    Buff(
        CONSUME,
        'prebuff',
        whenever,
        needs='prebuff',
        caster='defiler dance',
        also=(SUMMON_DEFILER,),
        lasts=CONSUME_SECONDS,
    ),
    Buff(HEX_PURGE, 'prebuff', whenever, needs='prebuff'),
    Buff(PSYCHIC_WARD, 'prebuff', whenever, needs='prebuff'),
    # Call to Arms, when one is worn: Battle Command and Battle Orders, out of town only (macros/cta.py)
    *CTA_ROWS,
    Buff(HEX_PURGE, 'upkeep', whenever, state=purge_shown),
    Buff(PSYCHIC_WARD, 'upkeep', whenever, state=ward_shown),
    Buff(
        CONSUME, 'upkeep', consume_due, needs='prebuff', caster='consume', also=(SUMMON_DEFILER,), lasts=CONSUME_SECONDS
    ),
    Buff(SUMMON_DEFILER, 'upkeep', defiler_missing, on='ground', caster='defiler'),
    # Engorge first for a pet in danger or among a dangerous pack (`engorge_first`, 2026-10-21); the pets watched here
    Buff(ENGORGE, 'fight', engorge_first, on='corpse', caster='engorge'),
    Buff(HEX_PURGE, 'fight', whenever, state=purge_shown),
    Buff(PSYCHIC_WARD, 'fight', ward_in_a_fight, state=ward_shown),
    Buff(SUMMON_DEFILER, 'fight', defiler_missing, on='ground', worth=worth_a_defiler, caster='defiler'),
    Buff(
        DEATH_MARK,
        'fight',
        mark_due,
        on='monster',
        target=target,
        worth=worth_a_mark,
        refused=mark_refusal,
        passed=mark_passed,
        said=mark_said,
        told=mark_told,
        shows=mark_shows,  # a mark that did not take is cast again (the player, 2026-10-20: "ok, recast")
        shows_within=MARK_SHOWS,
        recasts=MARK_RECASTS,
    ),
    # Bind Demon again with the bound demon gone in a tier 4-5 Herald pack fight (bind.py, combat/pack.py REBIND_DEMON)
    Buff(BIND_DEMON, 'fight', bind_due, on='monster', target=bind_target, said=bind_said, caster='bind'),
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
    """The executor's memory and due-tests under their old macros/rotation.py names, for the tests, replays and
    golden adapter written against those (`Rotation(hunter.buffs)`). Nothing in the hunt asks it."""

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
        return worth_a_mark(BuffFacts(world, 0.0, foes=(target,), reachable=(target,)), target)
