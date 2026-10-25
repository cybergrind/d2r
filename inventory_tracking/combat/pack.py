"""A tier 4-5 Herald's pack: keep range, hop out with the demons between, mark a member that can be clicked
(rca/2026-10-21/herald-fight-findings.md §3, Stage B).

The player, 2026-10-21 ~10:00, answering the findings' questions:
- Q1 "mark target": the nearest pack member that can be clicked; the Herald when it can be; no lock-out after a key
  that took nowhere (builds/warlock/mark.py `pack_target`);
- Q2/Q3 "range": 14-18 units; a Teleport back when anything is within 10; the omen stand at 24; surrounded, a Teleport
  out with the demon between, the mark laid again, the pack engaged again, up to 3 times a pack (the T1 question of
  rca/2026-10-21/arena-failures-findings.md, for Herald packs only) (macros/safety.py `Safety.pack_back`);
- Q4/Q6 "which packs, which demon": tier 4-5 Heralds; the bound demon holds the pack as the Defiler does; a missing
  Defiler is summoned even under attack, from range (builds/warlock/defiler.py `worth_a_defiler`).

The player's tactic of ~09:40 ("death mark nearest mob in group in direct sight / sigil of lethargy to slow whole
group / keep them busy with a daemon"), the parts built after Stage B (findings §7):
- the sigil at the disc that covers the most of the pack, on the demon once it holds the pack (`sigil_spot`,
  builds/warlock/casters.py `pack_sigil`);
- the bound demon bound again when it is gone (builds/warlock/bind.py), the Defiler summoned between the character
  and the pack (`between_spot`, builds/warlock/defiler.py `pack_spot`).

The tiers are the Herald's stat 367, which its minions carry too (game/records.py `Monster.tier`). The demons are the
companions the build's draw sends (macros/build.py `Draw.sends`): the Defiler, the bound demon, never the mercenary.
Pure geometry over points: the safety, the mark and the omen ask it with what they have.
"""

import math
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass

from inventory_tracking.combat.mechanics.life import leader
from inventory_tracking.game.layout import LEADER_FLAGS, MINION_FLAG
from inventory_tracking.levels.geometry import Point


# The whole tactic. True: the rulings above. False: a Herald pack is fought as any other (before 2026-10-21).
PACK_TACTIC = True
# Its parts, each on its own: the keep-range and surrounded hops (`why_back`, `hop_spots`), the mark on any member
# that can be clicked with no lock-out, the Defiler summoned from range whatever its price, the omen stand at 24.
PACK_KEEP_RANGE = True
MARK_ANY_MEMBER = True
DEMON_GATE = True
PACK_OMEN = True
# Sigil: Lethargy laid at the disc that covers the most of the pack (the Herald weighted HERALD_WEIGHT), and on the
# demon that holds it once one does (the player, 2026-10-21 ~09:40: "sigil of lethargy to slow whole group"; H-A's
# sigil under the Herald held 6-7 of 15, H-B's among the pack bunched on the demons 10-11 of 12: findings §2 step 3);
# laid again when the one that lies covers under SIGIL_HALF of the pack and a disc covers more, or as it runs out (the
# player, 2026-10-20 ~23:05: "keep them under sigil's effect all the time"). False: under the Herald, kept in it, as
# for any dangerous monster (builds/warlock/buffs.py SIGIL_KEEPS).
SIGIL_COVER = True
SIGIL_HALF = 0.5  # of the pack within the sigil's radius: under it, the sigil is laid again (findings §3.1 HOLD)
HERALD_WEIGHT = 2.0  # the Herald counts as this many members for the disc (findings §3.1 ENGAGE 3)
# Bind Demon again when the bound demon is gone in a tier 4-5 pack fight (the player, 2026-10-21 ~09:40: "keep them
# busy with a daemon"; Q6 ~10:00: "the bound demon holds the pack as the Defiler does", "from range"): on a demon in
# reach, none of the pack on the character within PACK_BACK (builds/warlock/bind.py). False: the bound demon is the
# player's to bind, as before.
REBIND_DEMON = True
# The Defiler summoned under the strike with a pack about stands between the character and the pack, PET_SPOT toward
# the pack's centre (the player, ~09:40: "keep group on our daemon, not ourselves or merc"; Summon Defiler lands where
# the pointer is, skills.txt 377 LineOfSight). Death Mark's jump and the hop's "demons between" are the other places
# the skills allow (`hop_spots`). False: at the first open summon spot, as before (builds/warlock/casters.py).
PETS_BETWEEN = True
PET_SPOT = 6.0  # units from the character
PACK_TIER_MIN = 4  # Q4: tier 4-5 (the scan of 41 fights: 11 of the T4-T5 ones lost over 1000 life)
PACK_RANGE = (14.0, 18.0)  # Q2: units from the pack's centre the character fights from (H-B stood 12-14: 0 lost)
PACK_STAND = 16.0  # the hop's first ring, the middle of PACK_RANGE
PACK_BACK = 10.0  # Q2: a member nearer the character than this (and on it, `on_character`) brings the hop back
SURROUND_COUNT = 3  # Q3: this many members within SURROUND_RADIUS of the character: out (H-A's at 2.9-4.2)
SURROUND_RADIUS = 5.0
PACK_HOPS = 3  # Q3: hops out a pack at most; then the plain safety alone (no loop)
PACK_OMEN_STAND = 24.0  # Q2: units from the omen's spot the full clear waits at (macros/hunting/base.py OMEN_STAND 20)
PACK_SEEN = 30.0  # units from the character within which members count for the pack's centre
# A demon nearer the character than this stands with it, not between it and the pack: it holds nobody (H-A: the
# bound Urdar at 0.0, the Defiler at 3.2, the pack on the character; H-B: both at 8.7-9.1, the pack on them).
DEMON_APART = 3.0
# A member's body covers one it is drawn in front of within this many units: the pointer on the one behind names the
# one in front (the 63 marks that went on a neighbour, 2026-10-20: the neighbour a median 3.2 units off, quartiles
# 2.8-3.6, 93% within 4, 62% drawn in front; rca/2026-10-20/mark-recast-leaders-findings.md §2).
COVER = 4.0
HOP_TURNS = (0.0, 30.0, -30.0, 60.0, -60.0, 90.0, -90.0)  # degrees off the way from the pack through the demons
HOP_RINGS = (PACK_STAND, PACK_RANGE[1], PACK_RANGE[0])
BACK_SAID = 'pack: keeping range'  # the hop's Move reason (macros/pursuit.py `arbitrate` takes it first)


@dataclass
class Pull:
    """A build's ask that the fight be pulled off its demon (builds/warlock/pets.py PET_PULL): why, and the clock it
    lapses at. The safety's pack hop takes it as one more reason to hop back (macros/safety.py `Safety.pack_back`)."""

    why: str | None = None
    until: float = -math.inf


PULL = Pull()


def ask_pull(why: str, until: float) -> None:
    """Ask the pack's hop for the demon's sake until `until` (a clock of the run's)."""
    PULL.why, PULL.until = why, until


def pulled(now: float) -> str | None:
    """Why the fight is pulled off the demon now, None with no ask standing (a clock that went back drops it)."""
    if PULL.why is None or not PULL.until - 10.0 <= now <= PULL.until:
        return None
    return PULL.why


# A Herald's coming read before its pack shows (macros/hunt.py `omens_now`: the heraldspawner missile, HERALD_OMEN):
# its spot and the clock it is read until. The build's sigil asks it (builds/warlock/buffs.py OMEN_SIGIL).
OMENS: dict[Point, float] = {}


def saw_omens(spots: Iterable[tuple[Point, float]]) -> None:
    """The omens pending now, (spot, the clock it is read until), in place of the last ones (macros/hunt.py)."""
    OMENS.clear()
    OMENS.update(dict(spots))


def omens(now: float) -> list[Point]:
    """The spots a Herald's pack is coming to at clock `now`."""
    return [spot for spot, until in OMENS.items() if now <= until]


@dataclass
class Hop:
    """The character's last jump that landed (macros/travel.py `Travel.jump`): the clock it landed at, its length."""

    at: float = -math.inf
    units: float = 0.0


HOP = Hop()


def hopped(at: float, units: float) -> None:
    """A Teleport or Blade Warp landed at clock `at`, `units` from where it was keyed (the demons within 10 come
    along and stop striking: builds/warlock/mark.py DESIGNATED_MARK `aggro_lost`; every one with ALONG_ALL)."""
    HOP.at, HOP.units = at, units


def since_hop(now: float) -> float:
    """Seconds since the last jump landed at clock `now`; inf with none (or a clock that went back)."""
    gap = now - HOP.at
    return gap if gap >= 0.0 else math.inf


# Retired 2026-10-25 (rca/2026-10-25/tactics/apply-1.md): MARK_AT_LANDING / LANDING_IN_PACK (`landing_ahead`, the
# before-strike rows before the press under LANDING_AHEAD s after any landing): never called by macros/hunt.py, and
# its arena gate of 2026-10-24 ~12:20 failed (T5 Bramble Hulk least life 0.98 -> 0.59, Herald 7/10 -> 5/10);
# HERALD_MARK_FIRST below (on) and R1's landing mark (DM_AFTER_EVERY_MOVE) are the mark at a landing.
LANDING_AHEAD = 1.5  # seconds after a landing the before-strike rows go before the press (HERALD_MARK_FIRST)


# The mark first at a tier 5 Herald fight's landing (2026-10-24, rca/2026-10-24/dm-latency-findings.md; the player,
# ~17:39: "when we're repositioning for re-aggro against T5 heralds, the first things we need to do - drop off aggro
# from us == DM"). Live (the takes of 2026-10-24, 1224 fight landings marked again within 3 s): the strike went first
# in all of them, and the mark's cast can only follow the strike's own cast (0.32 s): the Herald pack's marks were
# cast 0.80 s (p50; p90 1.72) after the Teleport's cast end. True: under LANDING_AHEAD s after a jump landed (`HOP`),
# with a member of a tier HERALD_MARK_TIER Herald pack in reach, the fight's first look casts the build's FIRST skills
# (builds/warlock/mark.py: Death Mark) its rows say are due before the strike (`Buff.before_strike`: the designated
# member's mark, mark.py `mark_ahead`, the target the mark rules pick), and the strike is pressed at the next look,
# under the mark's cast (the game starts the held strike at its end). The strike stays first everywhere else and under
# the fight casts' hold (macros/hunt.py FIGHT_CAST_REACH). False: the strike first, as before. On live from the restart
# after 18:42 on 2026-10-24 (the player: "go ahead and test this tactics"; gate A: herald 40 seeds deaths 1/0, T5 cuts
# 0/0, all within noise; gate C with the arena's aggro drop still running).
HERALD_MARK_FIRST = True
HERALD_MARK_TIER = 5
FIRST: set[int] = set()  # the skills a build casts first at such a landing
# The ruling's scope (2026-10-24 ~19:10, the coordinator after the arena's manaburn seed 3, where the mark first died
# at 30.56 s and the strike first lived): False, only a fight with the tier HERALD_MARK_TIER Herald itself in the read
# (a leader of the tier: game/records.py `Monster.leader`), not its minions alone (the Herald dead or out of the read);
# True: any member in reach, as from 18:49. HERALD_MARK_NO_BURN: not while the fight is a mana-burn one (the caller's
# `burning`: a drainer about or the safety's burn leave, macros/hunt.py `burning`), where the mark's cast costs the
# strike's first leech and the leave's Teleport mana. False: burn or not. Both left wide (ANY_MEMBER True, NO_BURN
# False) at ~19:30 (the coordinator: the player still sees the Teleport -> mark delay, narrowing it fires less often,
# and the burn skip departs from the ruling, so it waits for the player's word).
HERALD_MARK_ANY_MEMBER = True
HERALD_MARK_NO_BURN = False


def herald_mark_first(now: float, hostiles: Iterable = (), read: Iterable = (), burning: bool = False) -> bool:
    """Whether the fight's first look casts the FIRST skills before the strike (HERALD_MARK_FIRST): a jump landed under
    LANDING_AHEAD s ago, a member of a tier HERALD_MARK_TIER Herald pack is among `hostiles` (those in reach), the
    Herald itself among `read` (all the look's hostiles; HERALD_MARK_ANY_MEMBER: not asked) and, with
    HERALD_MARK_NO_BURN, the fight no mana-burn one (`burning`)."""
    if not HERALD_MARK_FIRST or not PACK_TACTIC or since_hop(now) > LANDING_AHEAD:
        return False
    if HERALD_MARK_NO_BURN and burning:
        return False
    if not any(getattr(m, 'tier', 0) >= HERALD_MARK_TIER for m in hostiles):
        return False
    return HERALD_MARK_ANY_MEMBER or any(
        getattr(m, 'tier', 0) >= HERALD_MARK_TIER and getattr(m, 'leader', False) for m in read
    )


# The hard fight (2026-10-24 ~20:30, rca/2026-10-24/dm-latency-findings.md §10; the player, ~20:27: "we don't need to
# cast DM like every second for regular enemies, but it is a great way to handle hard situations"): the one test the
# mark-after-every-move (DM_AFTER_EVERY_MOVE, builds/warlock/mark.py `move_reason`) and the mark-then-walk
# (MARK_THEN_WALK below) act under; a regular fight keeps the mark's own rules. Hard, within HARD_SEEN of
# the character: a tier HERALD_MARK_TIER Herald pack's member; a boss or super unique (terror/bosses.py); the safety's
# price of holding over its life budget (the caller's `pressed`: a `DrawPrice.pressed` of its last look); a hostile
# that drains mana (Mana Burn, or its type's own mana element: combat/threats/drain_escape.py `threat`); or HARD_PACK
# or more of an elite pack's (a leader's or its minions). Proposed: 8, two packs together or one unique's full pack
# (Hell: a unique with up to 8 minions); a plain group of any size (Hell cows) is regular.
HARD_SEEN = PACK_SEEN
HARD_PACK = 8
# DM_AFTER_EVERY_MOVE (R1, 2026-10-24 ~20:24, the player: "you need not only apply debuff itself, you need to cast DM
# after the TP, so daemon is forced to attack (it gets teleported to the location of where we cast DM)"; take
# 20261024T171736Z-71 at 20:18:41.53-43.06: a Blade Warp of 15 put both demons 0.1 off the character, idle, 1.5 s with
# no Death Mark key, a marked member within 14). True: in a hard fight (`hard_fight`), after every Teleport or Blade
# Warp landing (`HOP`, a jump of REMARK_HOP or more) the mark goes out first on a hostile in its reach, whatever its
# state on the old target and whatever builds/warlock/mark.py `aggro_lost` says; with no move, whenever a demon idles
# within PETS_WITH_US of the character (mark.py `pets_with_us`). False: the mark's own rules, as before.
# Held off 2026-10-24 22:52: the live tree's test_manaburn_death dies with it on (seeds 1, 3) and passes off;
# test_canyon_death adds seed 13
DM_AFTER_EVERY_MOVE = False
# DM_MOVE_NO_BURN (2026-10-24 ~21:45, dm-latency-findings.md §10, gate R2 on tree7, AGGRO + PETS + GLUED + WARP_ALONG):
# R1 in the arena's manaburn scene, seeds 21-60: deaths 3 -> 6 (5 new, 2 saved), lowest life -0.142 +- 0.062, kills a
# minute -6.4 +- 2.7, Death Mark keys a play 4.1 -> 8.2, Mana Burn hits 22.7 -> 38.6; herald 40 and the T5 cuts showed
# no new death. True: no mark after a move while a hostile that drains mana stands within HARD_SEEN (`burning`): the
# safety's mana leave and the marks' mana go first. False: R1 in those fights too. Gate R3 (tree7, with
# JUMP_LANDING_UNPRICED, paired against off): manaburn 40 deaths 3 -> 1 (none new), low +0.060 +- 0.037, kills a minute
# -0.8 +- 2.1; herald 40 deaths 2 -> 1 (none new), low +0.102 +- 0.062, kills a minute +0.46 +- 0.55, the pet stand's
# p90 3.68 -> 1.80 s; T5 cuts 3 x 20 no death (dolls: kills a minute -5.0 +- 3.4, low +0.032 +- 0.018).
DM_MOVE_NO_BURN = False  # 2026-10-24 22:52: held off with R1


def burning(here: Point, hostiles: Iterable) -> bool:
    """Whether a hostile that drains mana (Mana Burn, or its type's own mana element: combat/threats/drain_escape.py
    `threat`) stands within HARD_SEEN of `here`."""
    from inventory_tracking.combat.threats import drain_escape, manaburn  # late: they build on this module

    escape = drain_escape.MANA_ESCAPE
    return any(
        (manaburn.drains(tuple(m.modifiers)) or (escape and drain_escape.threat(m.txt_id)))
        and math.dist(here, (m.x, m.y)) <= HARD_SEEN
        for m in hostiles
    )


def hard_fight(here: Point, hostiles: Iterable, pressed: bool = False) -> str | None:
    """Why the fight is a hard one (HARD_SEEN, the module's notes), or None: a regular fight. `hostiles`: the look's
    (Monster-like: x, y, tier, flags, txt_id, modifiers); `pressed`: the safety prices holding over its life budget."""
    from inventory_tracking.combat.threats import drain_escape, manaburn  # late: they build on this module
    from inventory_tracking.terror.bosses import BOSSES, SUPER_UNIQUE_FLAG

    near = [m for m in hostiles if math.dist(here, (m.x, m.y)) <= HARD_SEEN]
    if any(getattr(m, 'tier', 0) >= HERALD_MARK_TIER for m in near):
        return f'a tier {HERALD_MARK_TIER} Herald pack'
    boss = next((m for m in near if m.txt_id in BOSSES or m.flags & SUPER_UNIQUE_FLAG), None)
    if boss is not None:
        return 'a boss'
    if pressed:
        return "holding is over the safety's life budget"
    escape = drain_escape.MANA_ESCAPE
    if any(manaburn.drains(tuple(m.modifiers)) or (escape and drain_escape.threat(m.txt_id)) for m in near):
        return 'a hostile that drains mana'
    elite = sum(1 for m in near if m.flags & (LEADER_FLAGS | MINION_FLAG))
    if elite >= HARD_PACK:
        return f'{elite} of an elite pack'
    return None


# MARK_THEN_WALK (R2, 2026-10-24 ~20:24, the player: "this is a good tactics to engage with larger groups, we just cast
# DM from safe distance => daemon gets teleported and gets aggro => we just close distance walking (tp brings dameon
# back to us, we want to aoid it in this case) => apply full damage"; scope ~20:27: hard situations only). True: a
# pursuit's progress jump (no retreat or dodge: macros/hunting/moves.py `danger_act`) toward a big group (`big_group`:
# a hard fight with BIG_GROUP or more hostiles within HARD_SEEN) with none in the strike's reach is made a walk while
# the demons hold it (a FIRST skill keyed under WALK_HOLD s ago); with none keyed, the mark goes first from where the
# character stands (`ask_mark`, builds/warlock/mark.py `move_reason`) when the safety's look prices standing within its
# life budget (the Hold's worst harm). A retreat still jumps. False: the jump, as before.
MARK_THEN_WALK = True  # on 2026-10-25 ~17:15: g0b3 gate passed (apply-0b.md)
BIG_GROUP = 6  # hostiles: a T5 Herald pack is 6-15; a champion pack 3-5 alone is no big group
WALK_HOLD = 6.0  # seconds after the mark's key the approach is walked (the demons' jump 0.28 s, a 15-unit walk ~2.5 s)
WALK_SAID = 'the mark from here before walking in (MARK_THEN_WALK)'


def big_group(here: Point, hostiles: Iterable, pressed: bool = False) -> str | None:
    """Why the fight is a big group for MARK_THEN_WALK (a hard one, `hard_fight`, with BIG_GROUP or more hostiles
    within HARD_SEEN), or None."""
    found = list(hostiles)
    why = hard_fight(here, found, pressed)
    if why is None and any(in_pack(getattr(m, 'tier', 0)) and math.dist(here, (m.x, m.y)) <= HARD_SEEN for m in found):
        # A tier 4 pack too (2026-10-25, the coordinator: "hard fights (T4-5 Herald packs, big groups)"), for the walk
        # in alone: DM_AFTER_EVERY_MOVE's `hard_fight` keeps tier 5
        why = f'a tier {PACK_TIER_MIN}-5 Herald pack'
    if why is None:
        return None
    near = sum(1 for m in found if math.dist(here, (m.x, m.y)) <= HARD_SEEN)
    return f'{why}, {near} near' if near >= BIG_GROUP else None


@dataclass
class Asked:
    """The clock the mark from where the character stands was last asked at (MARK_THEN_WALK)."""

    at: float = -math.inf


ASKED = Asked()
ASK_LASTS = 0.5  # seconds an ask stands: the look it is cast in


def ask_mark(now: float) -> None:
    ASKED.at = now


def mark_asked(now: float) -> bool:
    return MARK_THEN_WALK and 0.0 <= now - ASKED.at <= ASK_LASTS


@dataclass
class LandingAsk:
    """Whether the FIRST rows are asked at a landing for R1 (DM_AFTER_EVERY_MOVE, macros/hunt.py `landing_mark`)."""

    on: bool = False


# While on, the mark answers for R1's own reasons alone (builds/warlock/mark.py `target`, `mark_ahead`): the landing's
# hook counts every hostile on the screen as in the mark's reach, so the mark's other rules are not asked with them
LANDING_ASK = LandingAsk()


@contextmanager
def landing_ask() -> Iterator[None]:
    LANDING_ASK.on = True
    try:
        yield
    finally:
        LANDING_ASK.on = False


# Retired 2026-10-25 (rca/2026-10-25/tactics/apply-1.md): HOP_DRAG_PRICE (`drag_seconds`, DRAG_SECONDS 1.1 s more on
# a forgoable hop that drags striking demons) was never read by macros/safety.py `move_price` and gated neutral on
# 2026-10-24 ~12:20; MARK_HOLDS_JUMPS, NO_SHORT_HOPS_T5 and REAGGRO_BY_MARK bar those hops instead of pricing them.
# LEAVE_PACK_PRICE (the clear time of what is in reach on a move to a goal that is no fight) had no reader at all.
# The Death Mark through the fight casts' hold (2026-10-24, rca/2026-10-24/aggro-findings.md §2: take
# 20261024T084322Z-86, the doll Herald, 11:44:23.7-39: no mark in 15 s and 18 hops, "fight casts held: blows of 2702
# of 2625 can come within 1.0 s"): the mark's cast (0.32 s, the takes' median) is as long as a strike's (0.40), which
# the bout makes under the same blows, and it is the one cast that takes the blows off the character. True: the skills
# a build names here (builds/warlock/mark.py: Death Mark) are cast through macros/hunt.py FIGHT_CAST_REACH's hold
# (`through_hold`). False: every fight cast held, as before.
MARK_THROUGH_HOLD = False
THROUGH: set[int] = set()  # the skills a build lets through the hold


def through_hold(skill: int) -> bool:
    """Whether a fight cast of `skill` goes through the fight casts' hold (MARK_THROUGH_HOLD, THROUGH)."""
    return MARK_THROUGH_HOLD and skill in THROUGH


# Re-aggro by the mark, not a hop (the player, 2026-10-21 ~21:05: "when we're teleporting - our minions are teleporting
# with us and stop attacking. so, if we want to re-aggro - use death mark and do not teleport"; 2026-10-24 ~13:30:
# "teleporting - takes aggro from our minions ... => no re-aggro => we take multiple heavy hits => teleport => no
# re-aggro => ... => loop"; rca/2026-10-25/tactics/near-death.md P3, teleports.md §4.3, apply-1.md). The takes of
# 10-21 to 10-25: the keep range's hop "on the character" was the last move before 11 of 28 T5 first hits; it fires
# with the demons idle by the character and lands with them still there (every jump brings them, ALONG_ALL), so the
# pack is on the character again. True (rewritten 2026-10-25): while the demons idle by the character (`idle_by`: all
# within TAKEN_ALONG of it, none within DEMON_HOLDS of a hostile) with REAGGRO_ON or more hostiles on it within
# PACK_BACK (`reaggro_due`), the keep range's hop and a voluntary Teleport are not made (macros/safety.py, named
# REAGGRO_SAID) for up to REAGGRO_WAIT s, or until the mark has been keyed and landed (MARK_LANDS): the mark sends the
# demons (builds/warlock/mark.py REAGGRO_PACK designates the pack's member, its mark due at once), the hop would only
# bring the pack along. A real threat (`JumpHold.exempt`) and a retreat stay. False: as before (until 2026-10-25 it
# barred only a Teleport toward the fight under REAGGRO_WAIT s after a hop).
REAGGRO_BY_MARK = False
REAGGRO_WAIT = 1.2  # seconds a stretch of idle demons bars the hop at most (the mark's delay 0.8 s and its 0.37 s cast)
TAKEN_ALONG = 10.0
# ALONG_ALL (2026-10-25, rca/2026-10-25/tactics/teleports.md §3.1, apply-0a.md; the player, 2026-10-24 ~20:24: "tp
# brings dameon back to us, we want to aoid it in this case"): every Teleport and Blade Warp of the takes of 10-21 to
# 10-25 brought every demon and the mercenary to within 4.5 of the character, whatever their distance at the key (about
# 170,000 pet sightings, 0-3 to 30-60 units, none left behind); TAKEN_ALONG's 10 was measured on allies within 10
# only. True: a jump takes every companion along (`along`), so a landing by a jump is judged with no demon holding
# anything there (`breaks_range`, `range_kept`, macros/safety.py PACK_RANGE_LANDING) and a hop's spots are not
# aimed "through the demons" (`hop_spots`, manaburn.py `hop_spots`): the hop brings them. A walk leaves them where
# they stand. False: the allies within TAKEN_ALONG alone, as before.
ALONG_ALL = False


def along(start: Point, ally: Point) -> bool:
    """Whether a jump keyed at `start` takes the companion at `ally` along (ALONG_ALL: every one; else within
    TAKEN_ALONG)."""
    return ALONG_ALL or math.dist(start, ally) <= TAKEN_ALONG


def left_holding(demons: Iterable[Point], jumped: bool) -> list[Point]:
    """The demons that still stand where they are once the character has moved: none after a jump with ALONG_ALL
    (they come along), else all of them."""
    return [] if ALONG_ALL and jumped else list(demons)


DEMON_HOLDS = 5.8  # units: a demon this near a hostile strikes it (mark.py MARK_BESIDE 2.8 + HELD 3.0)
REAGGRO_SAID = 'the demons idle by the character: re-aggro by Death Mark, not a hop (REAGGRO_BY_MARK)'


REAGGRO_ON = 2  # hostiles on the character (builds/warlock/mark.py REAGGRO_PRESS, the pack's re-aggro mark)


def idle_by(here: Point, demons: Sequence[Point], hostiles: Iterable[Point]) -> bool:
    """Whether the demons stand idle by the character (REAGGRO_BY_MARK): one at least, all within TAKEN_ALONG of
    `here`, none within DEMON_HOLDS of a hostile, a hostile within PACK_SEEN of `here`. Off: False."""
    if not REAGGRO_BY_MARK or not demons or any(math.dist(here, d) > TAKEN_ALONG for d in demons):
        return False
    foes = [h for h in hostiles if math.dist(here, h) <= PACK_SEEN]
    return bool(foes) and not any(math.dist(d, h) <= DEMON_HOLDS for d in demons for h in foes)


def reaggro_due(here: Point, demons: Sequence[Point], hostiles: Iterable[Point]) -> bool:
    """Whether the mark re-aggroes the pack instead of a hop (REAGGRO_BY_MARK): the demons idle by the character
    (`idle_by`) and REAGGRO_ON or more hostiles within PACK_BACK of it."""
    found = list(hostiles)
    if not idle_by(here, demons, found):
        return False
    return sum(1 for h in found if math.dist(here, h) < PACK_BACK) >= REAGGRO_ON


def reaggro_holds(now: float, since: float | None) -> bool:
    """Whether the re-aggro's bar holds at clock `now` for a stretch of `reaggro_due` begun at `since`: under
    REAGGRO_WAIT s into it, and the mark not keyed in it MARK_LANDS s ago or more."""
    if since is None or not 0.0 <= now - since <= REAGGRO_WAIT:
        return False
    return not (MARK.at >= since and since_mark(now) >= MARK_LANDS)


# MARK_HOLDS_JUMPS (2026-10-25, rca/2026-10-25/tactics/teleports.md §3.4 and §4.1-4.4, apply-0b.md; the player,
# 2026-10-24 ~19:58: "Retreat = safety tp out. tp = we move with merc and daemons. So, what is the logical reason to do
# DM and then immediately call it off with tp?", ~20:24: "cast DM from safe distance => daemon gets teleported and gets
# aggro => we just close distance walking (tp brings dameon back to us, we want to aoid it in this case)"). The takes
# since 10-24 18:49: 198 fight Teleports an hour keyed within 1.5 s after a Death Mark key, 152 of them pulling the
# sent demon back (better place 106, pursuit 15, keep range 14, retreats 9); the keep range's hop fired ~0.3 s after
# the key, before the demons had landed (the mark's jump 0.28 s). True: under MARK_LANDS s after the mark's key
# (`keyed`, macros/buffs.py) no jump is made (the keep range's hop and a retreat are judged again once the demons have
# landed, with them as holders); under MARK_WALKS s a voluntary jump (a better place, a firing spot, the pursuit's
# move) is not made either: walked (macros/hunting/moves.py `better_stand`) or the strike from here. A real threat
# (`JumpHold.exempt`: surrounded, a hit of HOLD_BURST of the life within 1 s, the life budget spent, a rejuvenation's
# alarm, a drainer, a live doll close) lifts it. False: as before.
MARK_HOLDS_JUMPS = True  # on 2026-10-25 ~13:58: g0b2 arena 24 fights x 20 seeds, no new death (apply-0b.md)
MARK_LANDS = 0.45  # s after the key: the mark's jump 0.28 s (p50) and a look's margin
MARK_WALKS = 1.8  # s after the key: the demons on the pack (re-engaged p90 1.16-1.53 s with a mark)
# NO_SHORT_HOPS_T5 (2026-10-25 ~11:08, the player: "from what I can see, we often try to move for short distances in
# battle with T5 heralds => teleporting aggroed minions to us. sometimes that makes sense, but in most cases we just
# bring aggro to our positions instead"; teleports.md §3.2: in T4-5 fights 93% of the demons engaged at a hop's key
# were stripped by it, the keep range 526 of 595, the better place 547 of 595). True: in a fight with a tier
# HERALD_MARK_TIER Herald pack's member within HARD_SEEN, while a companion holds the pack (one DEMON_APART or more
# off the character within DEMON_HOLDS of a member: `pack_held`), a jump that is short (under SHORT_HOP units) or lands
# within PACK_REACH of a member is not made: the better place and the firing spot (voluntary jumps, PLACE); walked, or
# the strike from here. The keep range's hop and the retreats go (the arena, apply-short.md: herald seed 8 died with
# the keep range's hops held), and the exemptions of MARK_HOLDS_JUMPS stay. False: as before.
NO_SHORT_HOPS_T5 = False
SHORT_HOP = 15.0  # units: the player's "short distances"
PACK_REACH = 18.0  # units from a member a landing is still inside the pack's reach (PACK_RANGE's far end, FAST_KEEP)
HOLD_BURST = 0.15  # the share of the life lost within 1 s that is a real threat (a T5 blow is 400-900 of ~2900)
# Ranged hostiles (combat/bolts.py threat table `ranged`) within the shot's reach (sim/monsters.py SHOT_REACH) that are
# a real threat: the walk in is for a pack the demons hold; a ranged pack throws at the walker, and a jump leaves the
# throws aimed at its place (2026-10-25, apply-0b.md: the Canyon's 15 Hell Slingers, 4 javelins of 770-860 in two
# frames from full life on the 12-unit walk the hold gave, every one of seeds 2-5 dead by 8 s; the jump lived)
HOLD_SHOOTERS = 3
HELD_SAID = 'a jump held'
PLACE, KEEP, RETREAT = 'place', 'keep', 'retreat'  # the kinds of jump (`held`)


@dataclass
class Keyed:
    """The clock the build's FIRST skill (Death Mark) was last keyed at (MARK_HOLDS_JUMPS)."""

    at: float = -math.inf


MARK = Keyed()


def keyed(skill: int, at: float) -> None:
    """A skill keyed at clock `at` (macros/buffs.py `Buffs.remember`): the mark's (a FIRST skill) is kept."""
    if skill in FIRST:
        MARK.at = at


def since_mark(now: float) -> float:
    """Seconds since the mark's key at clock `now`; inf with none (or a clock that went back)."""
    gap = now - MARK.at
    return gap if gap >= 0.0 else math.inf


@dataclass(frozen=True)
class JumpHold:
    """What one look holds jumps by (`jump_hold`): where the character stands, the seconds since the mark's key, the
    tier 5 pack's members while a companion holds it (() else), and the real threat that lifts the hold (None: none)."""

    here: Point
    marked: float = math.inf
    held: tuple[Point, ...] = ()
    exempt: str | None = None


def pack_held(here: Point, members: Sequence[Point], companions: Iterable[Point]) -> bool:
    """Whether a companion holds the pack: one DEMON_APART or more off the character within DEMON_HOLDS of a member."""
    return any(math.dist(c, m) <= DEMON_HOLDS for c in holders(here, companions) for m in members)


def jump_hold(
    now: float, here: Point, hostiles: Iterable, companions: Iterable[Point], exempt: str | None = None
) -> JumpHold | None:
    """The look's hold on jumps (MARK_HOLDS_JUMPS, NO_SHORT_HOPS_T5), or None with neither on. `hostiles`: the look's
    (`at` or `x`, `y`, and `tier`); `companions`: where they stand; `exempt`: the real threat seen, if any."""
    if not (MARK_HOLDS_JUMPS or NO_SHORT_HOPS_T5):
        return None
    held: tuple[Point, ...] = ()
    if NO_SHORT_HOPS_T5:
        members = []
        for m in hostiles:
            at = m.at if hasattr(m, 'at') else (m.x, m.y)
            if getattr(m, 'tier', 0) >= HERALD_MARK_TIER and math.dist(here, at) <= HARD_SEEN:
                members.append(at)
        if members and pack_held(here, members, companions):
            held = tuple(members)
    return JumpHold(here, since_mark(now) if MARK_HOLDS_JUMPS else math.inf, held, exempt)


def held(hold: JumpHold | None, spot: Point, kind: str) -> str | None:
    """Why a jump of `kind` (PLACE: a voluntary one; KEEP: the keep range's hop; RETREAT) to `spot` is not made now
    (MARK_HOLDS_JUMPS, NO_SHORT_HOPS_T5), or None."""
    if hold is None or hold.exempt is not None:
        return None
    if hold.marked <= MARK_LANDS:
        return f'{HELD_SAID}: the demons land on the mark ({hold.marked:.2f} s after its key; MARK_HOLDS_JUMPS)'
    if kind == PLACE and hold.marked <= MARK_WALKS:
        return f'{HELD_SAID}: walked while the mark takes the pack ({hold.marked:.2f} s on; MARK_HOLDS_JUMPS)'
    if hold.held and kind == PLACE:
        # A voluntary jump alone: the keep range's hop goes (2026-10-25 arena, apply-short.md: herald seed 8, its hops
        # at 8.6-8.8 held, a tier 5 hulk walked in to 4.7 and one blow of 2233 took 1783 life while the staff's
        # Teleport swapped in; the safety priced the blow at 682)
        away = math.dist(hold.here, spot)
        inside = min(math.dist(spot, m) for m in hold.held)
        if away < SHORT_HOP or inside < PACK_REACH:
            return (
                f'{HELD_SAID}: the demons hold the tier 5 pack, a jump of {away:.0f} landing {inside:.0f} from it '
                'brings it onto the character (NO_SHORT_HOPS_T5)'
            )
    return None


def walks_now(hold: JumpHold | None) -> bool:
    """Whether the fight's better place is walked to now, not jumped (`held` for a PLACE jump anywhere near)."""
    if hold is None or hold.exempt is not None:
        return False
    return hold.marked <= MARK_WALKS or bool(hold.held)


@dataclass(frozen=True)
class Member:
    """One of a Herald pack's: its unit, place, and whether it is the Herald itself."""

    unit: int
    at: Point
    herald: bool = False


def in_pack(tier: int) -> bool:
    """Whether a hostile of this Herald tier is one the tactic applies to (PACK_TACTIC, PACK_TIER_MIN)."""
    return PACK_TACTIC and tier >= PACK_TIER_MIN


def members(hostiles: Iterable) -> list[Member]:
    """The pack's members among hostiles with `unit`, `at` (or `x`, `y`), `tier` and `flags`: those of a tier 4-5
    Herald's pack, the Herald its leader."""
    found = []
    for m in hostiles:
        if not in_pack(m.tier):
            continue
        at = m.at if hasattr(m, 'at') else (m.x, m.y)
        unit = m.unit if hasattr(m, 'unit') else m.unit_id
        found.append(Member(unit, at, leader(m.flags)))
    return found


def key_of(pack: Sequence[Member]) -> int | None:
    """The pack's name for the hop count: its Herald's unit, else its lowest unit."""
    if not pack:
        return None
    heralds = [m.unit for m in pack if m.herald]
    return heralds[0] if heralds else min(m.unit for m in pack)


def holders(here: Point, demons: Iterable[Point]) -> list[Point]:
    """The demons that may hold the pack: those DEMON_APART or more from the character."""
    return [d for d in demons if math.dist(d, here) >= DEMON_APART]


def on_character(here: Point, at: Point, held_by: Sequence[Point]) -> bool:
    """Whether a member at `at` goes for the character: no holding demon is nearer it than the character."""
    away = math.dist(here, at)
    return all(away <= math.dist(d, at) for d in held_by)


def pressing(here: Point, pack: Sequence[Member], demons: Iterable[Point]) -> list[Member]:
    """The members within PACK_BACK of the character that are on it, not on a demon (Q2, the pack kept on the demon)."""
    held_by = holders(here, demons)
    return [m for m in pack if math.dist(here, m.at) < PACK_BACK and on_character(here, m.at, held_by)]


def surrounding(here: Point, pack: Sequence[Member]) -> list[Member]:
    """The members within SURROUND_RADIUS of the character, on a demon or not."""
    return [m for m in pack if math.dist(here, m.at) <= SURROUND_RADIUS]


def why_back(here: Point, pack: Sequence[Member], demons: Iterable[Point], lead: float = 0.0) -> str | None:
    """Why the character hops back from the pack now, or None: surrounded (Q3), else a member on it within PACK_BACK
    (Q2). `lead`: units the members on the character come on before the look that judges a landing there
    (RANGE_LEAD), added to PACK_BACK; 0 for the hop's own look. Those a demon holds do not come on: the surround
    radius stays."""
    if not PACK_KEEP_RANGE or not pack:
        return None
    close = surrounding(here, pack)
    if len(close) >= SURROUND_COUNT:
        return f'surrounded: {len(close)} of the pack within {SURROUND_RADIUS:.0f}'
    held_by = holders(here, demons)
    near = [m for m in pack if math.dist(here, m.at) < PACK_BACK + lead and on_character(here, m.at, held_by)]
    if near:
        nearest = min(math.dist(here, m.at) for m in near)
        return f'{len(near)} of the pack on the character within {PACK_BACK + lead:.0f} (the nearest at {nearest:.1f})'
    return None


# 2026-10-23 (the player: "try to push exp/hour more"; rca/2026-10-23/keep-range-findings.md): the fight's better place
# and the keep range's hop undid each other. Take 20261022T235532Z-51, 02:57:10-21: "a better place in the fight" at
# (10071.5, 5623.5), 6-7 units from three Horror Archers, then at once "pack: keeping range: 3 of the pack on the
# character within 10", hop 1 of 3 out, the better place offered again, back, hop 2, back, hop 3: 7 jumps, 0 kills in
# 10 s. True: a place the fight would go to is judged by `why_back` as if the character stood there (`breaks_range`,
# `range_kept`), the one model of the range both the hop (macros/safety.py `Safety.pack_back`) and the places use; a
# place the hop would leave at once is not offered. False: the places are judged without the pack's range, as before.
PLACES_KEEP_RANGE = True
# 2026-10-23 (the player: "your goal is to maximize exp/hour"; rca/2026-10-23/fight-yield-findings.md): the range was
# judged on the members where the look saw them, and they came on while the character went. Take
# 20261023T063700Z-19 (Mausoleum, a tier 5 Herald pack of 15 Hungry Dead, 09:37:15-38): the fight's better places
# stood 10.0-11.0 off the nearest member at the look (PLACES_KEEP_RANGE passed them), the members walked 2-4.3 units
# a second, the jump landed 0.6-0.9 s later 8.0-8.4 off, and the keep range's hop took the character out at once:
# 4 of the take's 10 offers, each a better place, a hop and a strike gap of ~1.5 s. True: a landing is judged with
# the members on the character LEAD_UNITS nearer (`why_back`'s `lead`: PACK_BACK 10 -> 14), the places and
# the safety's landing bar alike (`breaks_range`, `range_kept`; macros/safety.py PACK_RANGE_LANDING); the hop's own
# spots that clear every member by PACK_BACK + LEAD_UNITS come before the rest (`hop_spots`). The hop itself still
# fires at PACK_BACK. False: the members where the look saw them, as before.
RANGE_LEAD = True
LEAD_UNITS = 4.0  # 4.3 units a second over a jump's 0.6-0.9 s to the landing's look (take -19); manaburn HOP_CLEAR 4


def lead() -> float:
    """Units a landing's range is judged nearer the members by (RANGE_LEAD)."""
    return LEAD_UNITS if RANGE_LEAD else 0.0


def breaks_range(spot: Point, hostiles: Iterable, demons: Iterable[Point], jumped: bool = False) -> str | None:
    """Why standing at `spot` would have the keep range hop back at once: `why_back` there, of the tier 4-5 Herald pack
    among `hostiles` (`members`), the build's demons where they stand now (none when `jumped` there with ALONG_ALL:
    they come along), the members `lead()` nearer. None when it would not, or with PLACES_KEEP_RANGE off. For a move
    the safety prices (macros/safety.py `Pricing.move_price`)."""
    if not PLACES_KEEP_RANGE:
        return None
    return why_back(spot, members(hostiles), left_holding(demons, jumped), lead())


def range_kept(
    hostiles: Iterable, demons: Iterable[Point], here: Point | None = None, jumps_from: float = math.inf
) -> Callable[[Point], bool]:
    """`breaks_range` as a filter over many places of one look (combat/stance.py `camp`'s `shown`): True where the
    character could stand without the hop taking it out at once; every place with no pack or PLACES_KEEP_RANGE off.
    A place `jumps_from` units or more from `here` is one a jump goes to (stance.py `camp`: a jump that reaches a
    place is taken), judged with ALONG_ALL's demons along."""
    pack = members(hostiles) if PLACES_KEEP_RANGE else []
    if not pack:
        return lambda spot: True
    held, ahead = list(demons), lead()
    gone = left_holding(held, jumped=True)

    def kept(spot: Point) -> bool:
        jumped = here is not None and math.dist(here, spot) >= jumps_from
        return why_back(spot, pack, gone if jumped else held, ahead) is None

    return kept


def centre(here: Point, pack: Sequence[Member]) -> Point:
    """The middle of the members within PACK_SEEN of the character (all of them when none is)."""
    near = [m.at for m in pack if math.dist(here, m.at) <= PACK_SEEN] or [m.at for m in pack]
    return (sum(p[0] for p in near) / len(near), sum(p[1] for p in near) / len(near))


def hop_spots(here: Point, pack: Sequence[Member], demons: Sequence[Point]) -> list[Point]:
    """Where to hop to, best first: on rings PACK_RANGE from the pack's centre, along the way from the centre through
    the demons (the character where none is out, or with ALONG_ALL, which brings them along), so the demons stand
    between the pack and the landing; turned off it
    by HOP_TURNS when walls or members stand there. Every spot is PACK_BACK or more from each member."""
    if not pack:
        return []
    middle = centre(here, pack)
    through = left_holding(demons, jumped=True) or [here]  # ALONG_ALL: the hop brings the demons, none stays between
    via = (sum(p[0] for p in through) / len(through), sum(p[1] for p in through) / len(through))
    heading = math.atan2(via[1] - middle[1], via[0] - middle[0])
    if math.dist(via, middle) < 1e-6:
        heading = math.atan2(here[1] - middle[1], here[0] - middle[0])
    found = []
    for turn in HOP_TURNS:
        angle = heading + math.radians(turn)
        for ring in HOP_RINGS:
            spot = (middle[0] + ring * math.cos(angle), middle[1] + ring * math.sin(angle))
            if all(math.dist(spot, m.at) >= PACK_BACK for m in pack):
                found.append(spot)
    if RANGE_LEAD:
        # The spots the members do not reach by the landing's look first, each kind in its order (RANGE_LEAD)
        clear = [spot for spot in found if all(math.dist(spot, m.at) >= PACK_BACK + LEAD_UNITS for m in pack)]
        found = clear + [spot for spot in found if spot not in clear]
    return found


def between(spot: Point, pack: Sequence[Member], demon: Point, here: Point) -> bool:
    """Whether `demon` stands between the pack's centre and `spot`: nearer the centre than the spot is, and within 90
    degrees of the way to it."""
    middle = centre(here, pack)
    to_spot = (spot[0] - middle[0], spot[1] - middle[1])
    to_demon = (demon[0] - middle[0], demon[1] - middle[1])
    ahead = to_spot[0] * to_demon[0] + to_spot[1] * to_demon[1] > 0
    return math.dist(middle, demon) < math.dist(middle, spot) and ahead


def covered(at: Point, others: Iterable[Point]) -> bool:
    """Whether a body at `at` is covered for the pointer: another drawn in front of it (the larger x + y on the
    screen's isometric view) within COVER units."""
    return any(0 < math.dist(at, o) <= COVER and o[0] + o[1] > at[0] + at[1] for o in others)


def weight(member: Member) -> float:
    """What a member counts for the sigil's disc: HERALD_WEIGHT for the Herald, 1 for the rest."""
    return HERALD_WEIGHT if member.herald else 1.0


def nearby(here: Point, pack: Sequence[Member]) -> list[Member]:
    """The members within PACK_SEEN of the character (all of them when none is): the pack the tactic sees."""
    return [m for m in pack if math.dist(here, m.at) <= PACK_SEEN] or list(pack)


def covering(spot: Point, pack: Sequence[Member], radius: float) -> list[Member]:
    """The members within `radius` of `spot`."""
    return [m for m in pack if math.dist(spot, m.at) <= radius]


def cover_weight(spot: Point, pack: Sequence[Member], radius: float) -> float:
    """The members a disc of `radius` at `spot` covers, the Herald weighted (`weight`)."""
    return sum(weight(m) for m in covering(spot, pack, radius))


def cover_share(spot: Point, pack: Sequence[Member], radius: float) -> float:
    """The share of the pack within `radius` of `spot` (members, unweighted); 0 with no pack."""
    return len(covering(spot, pack, radius)) / len(pack) if pack else 0.0


def densest(pack: Sequence[Member], radius: float) -> Point:
    """The centre of the disc of `radius` that covers the most of the pack (`cover_weight`): among the members'
    places, the middle of each pair within two radii, and the middle of what each member's disc covers; the one nearer
    the pack's middle of two alike."""
    places = [m.at for m in pack]
    found = list(places)
    for i, a in enumerate(places):
        for b in places[i + 1 :]:
            if math.dist(a, b) <= 2 * radius:
                found.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
    for m in pack:
        inside = [o.at for o in covering(m.at, pack, radius)]
        found.append((sum(p[0] for p in inside) / len(inside), sum(p[1] for p in inside) / len(inside)))
    middle = (sum(p[0] for p in places) / len(places), sum(p[1] for p in places) / len(places))
    return max(found, key=lambda spot: (cover_weight(spot, pack, radius), -math.dist(spot, middle)))


def holding(here: Point, pack: Sequence[Member], demons: Iterable[Point], radius: float) -> tuple[Point, int] | None:
    """The demon that holds the pack and how many of it: of the holders (`holders`), the one whose disc of `radius`
    covers the most members (`cover_weight`), when that is at least SIGIL_HALF of the pack; None else."""
    held_by = holders(here, demons)
    if not held_by or not pack:
        return None
    best = max(held_by, key=lambda demon: cover_weight(demon, pack, radius))
    found = len(covering(best, pack, radius))
    return (best, found) if found >= SIGIL_HALF * len(pack) else None


def sigil_spot(here: Point, pack: Sequence[Member], demons: Iterable[Point], radius: float) -> tuple[Point, str]:
    """Where the pack's sigil goes, and why in words: on the demon that holds the pack (`holding`) unless a disc
    elsewhere covers more of it, else at the disc that covers the most (`densest`), of the members the tactic sees
    (`nearby`)."""
    seen = nearby(here, pack)
    spot = densest(seen, radius)
    held = holding(here, seen, demons, radius)
    if held is not None and cover_weight(held[0], seen, radius) >= cover_weight(spot, seen, radius):
        return held[0], f'on the demon holding {held[1]} of {len(seen)}'
    return spot, f'the disc covering {len(covering(spot, seen, radius))} of {len(seen)}'


def between_spot(here: Point, pack: Sequence[Member]) -> Point | None:
    """Where a demon summoned now stands between the character and the pack (PETS_BETWEEN): PET_SPOT toward the pack's
    centre (half the way when that is nearer), no nearer than SURROUND_RADIUS to a member; None with no pack or no
    such spot."""
    if not PETS_BETWEEN or not pack:
        return None
    middle = centre(here, pack)
    away = math.dist(here, middle)
    if away < 1e-6:
        return None
    for share in (min(PET_SPOT, away / 2) / away, PET_SPOT / 2 / away):
        spot = (here[0] + (middle[0] - here[0]) * share, here[1] + (middle[1] - here[1]) * share)
        if all(math.dist(spot, m.at) >= SURROUND_RADIUS for m in pack):
            return spot
    return None
