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
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from inventory_tracking.combat.mechanics.life import leader
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
    along and stop striking: builds/warlock/mark.py REMARK_AFTER_HOP)."""
    HOP.at, HOP.units = at, units


def since_hop(now: float) -> float:
    """Seconds since the last jump landed at clock `now`; inf with none (or a clock that went back)."""
    gap = now - HOP.at
    return gap if gap >= 0.0 else math.inf


# Re-aggro by the mark, not a hop (the player, 2026-10-21 ~21:05: "when we're teleporting - our minions are teleporting
# with us and stop attacking. so, if we want to re-aggro - use death mark and do not teleport"): with the demons idle
# by the character (`idle_by`: all within TAKEN_ALONG of it, the distance a Teleport takes allies along, none within
# DEMON_HOLDS of a hostile, one in the fight within PACK_SEEN), Death Mark goes again (builds/warlock/mark.py
# `remark_target`) and the safety bars a Teleport toward the fight for up to REAGGRO_WAIT s (macros/safety.py, named
# REAGGRO_SAID): the hop would take the demons along, the mark sends them. False: as before.
REAGGRO_BY_MARK = False
REAGGRO_WAIT = 1.2  # seconds a stretch of idle demons bars the hop at most (the mark's delay 0.8 s and its 0.37 s cast)
TAKEN_ALONG = 10.0
DEMON_HOLDS = 5.8  # units: a demon this near a hostile strikes it (mark.py MARK_BESIDE 2.8 + HELD 3.0)
REAGGRO_SAID = 'the demons idle by the character: re-aggro by Death Mark, not a hop'


def idle_by(here: Point, demons: Sequence[Point], hostiles: Iterable[Point]) -> bool:
    """Whether the demons stand idle by the character (REAGGRO_BY_MARK): one at least, all within TAKEN_ALONG of
    `here`, none within DEMON_HOLDS of a hostile, a hostile within PACK_SEEN of `here`. Off: False."""
    if not REAGGRO_BY_MARK or not demons or any(math.dist(here, d) > TAKEN_ALONG for d in demons):
        return False
    foes = [h for h in hostiles if math.dist(here, h) <= PACK_SEEN]
    return bool(foes) and not any(math.dist(d, h) <= DEMON_HOLDS for d in demons for h in foes)


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


def why_back(here: Point, pack: Sequence[Member], demons: Iterable[Point]) -> str | None:
    """Why the character hops back from the pack now, or None: surrounded (Q3), else a member on it within PACK_BACK
    (Q2)."""
    if not PACK_KEEP_RANGE or not pack:
        return None
    close = surrounding(here, pack)
    if len(close) >= SURROUND_COUNT:
        return f'surrounded: {len(close)} of the pack within {SURROUND_RADIUS:.0f}'
    near = pressing(here, pack, demons)
    if near:
        nearest = min(math.dist(here, m.at) for m in near)
        return f'{len(near)} of the pack on the character within {PACK_BACK:.0f} (the nearest at {nearest:.1f})'
    return None


def centre(here: Point, pack: Sequence[Member]) -> Point:
    """The middle of the members within PACK_SEEN of the character (all of them when none is)."""
    near = [m.at for m in pack if math.dist(here, m.at) <= PACK_SEEN] or [m.at for m in pack]
    return (sum(p[0] for p in near) / len(near), sum(p[1] for p in near) / len(near))


def hop_spots(here: Point, pack: Sequence[Member], demons: Sequence[Point]) -> list[Point]:
    """Where to hop to, best first: on rings PACK_RANGE from the pack's centre, along the way from the centre through
    the demons (the character where none is out), so the demons stand between the pack and the landing; turned off it
    by HOP_TURNS when walls or members stand there. Every spot is PACK_BACK or more from each member."""
    if not pack:
        return []
    middle = centre(here, pack)
    through = demons or [here]
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
