"""The way out of a mana-draining fight: the mana is the escape, and a draining blow takes more of it than any reserve
(rca/2026-10-23/death-manaburn-findings.md).

The death of 2026-10-23 18:57:45 (take 20261023T155650Z-88, Flayer Dungeon Level 1, a tier 5 Herald pack of Dark
Shapes, monstats 42 wraith5, with nine plain ones about): one blow of a plain Dark Shape took 468 of 745 mana (46.72 s
of the take), the next contact 1.3 s later took the rest; from then on no Teleport could be cast, four Rejuvenations
refilled the mana for 0.3-0.65 s each and none was followed by a Teleport, and the character died standing 6.6 s at
one spot. The player: "we must not die or we lose exp and our gear"; "re-create this in tests, find out the solution
that: will avoid death in this situation, will be good in other situations, won't hurt kill time for T5 heralds,
won't hurt exp/hour metric" (2026-10-23 ~19:05).

What combat/threats/manaburn.py did not see, and what this module adds under MANA_ESCAPE:

1. **The drain by type** (`drains`): wraith1-9 and willowisp1-8 burn mana with every A1 blow by their own row
   (monstats El1Type 'mana', 200-300 in Hell, 40-90 %), Mana Burn or not; manaburn.py's DRAINING knows the modifier
   (monumod 25) only. The take's plain Dark Shapes made the first burn and the burn to 0. The rows whose most is under
   BURN_LEAST (goatman6, foulcrow7: 10-33) are no threat to the pool and are left out.
2. **A drain fight is one fight** (`widened`): while any drainer is kept at range, or a burn is remembered, every
   drainer near is, so a hop out of the pack does not land beside a plain one (hop 6 of the take landed 2.0 from one).
   A plain drainer alone is not kept at range before it burns: the burn makes the leave (item 3), and keeping every
   plain Burning Soul or Ghost away cost the arena's fights their kills (danger-plains-0508: 3.7 against 14.2).
3. **The burn remembered** (`BurnWatch`): manaburn.py's floor is a fall within 1 s or the mana under a 64-point
   reserve; 1.1 s after the 468-point burn the floor was no longer crossed (277 > 64) and the look held, cast Psychic
   Ward and struck for 1.8 s with mana for a dozen Teleports. Once a burn is seen (a fall of BURN_SHARE of the pool
   between two looks with a drainer in reach) the leave stays priced first while a drainer's reach covers the character,
   for BURN_HOLD s, and after that while the mana is under RECOVERED of the pool (the life budget 0 meanwhile, as the
   floor's).
4. **The leave is out of reach** (`far_spots`): the floor's hops (16-24) were caught by an Extra Fast pack within a
   second; the leave lands FAR_LENGTHS (24-30) from the character, clear of every drainer by its keep range and
   LEAVE_CLEAR, before the shorter hops.
5. **A refill is an escape** (`RefillEscape`): with no mana for Teleport the leave is priced as a walk; the Teleport to
   the leave's place is kept, and a Rejuvenation drunk for the mana is followed by that Teleport at once, not by the
   next look (the take: a 249 ms look, its act dropped as stale, the mana gone 0.34 s after the drink).
6. **Every skill pays its mana** (`unpaid`): only Teleport was barred under its cost; Blade Warp (skills.txt 390,
   15 mana) was chosen at 0 mana and the game took no cast (18:57:41.4, 1.1 s lost waiting for it).

7. **Who a drainer goes for is read from its way** (`BurnWatch.closing_in`): the keep range's hop counts only the
   members no demon stands nearer (combat/pack.py `on_character`, the Herald tactic's "keep group on our daemon"); the
   take's Dark Shapes went for the character with the demons by them (the bound demon and the mercenary unhurt, 20
   within 3 of the character), and in the arena the pack came 15.7 -> 2.7 in 1.6 s while every look held. A drainer
   closing on the character is on it.

8. **No clear spot is no reason to stay** (`clearest`, `price_clearest`): the hop out of a draining pack and the
   leave take only landings clear of every keep range; among a pack spread round the character none is, and the look
   held (the arena's seed 12: 13 of the pack 15.7 -> 2.7 off in 1.6 s, "why" said and nothing priced). The clearest
   landings that gain room are priced then.

9. **The way back** (`BurnWatch.back`, `gains`): in the dungeon's corridors no landing round the character is clear
   (the arena's seed 12 had footing in two of eight ways, both toward the pack); the way the character came is, and
   the navigator's Teleport along it is taken while each landing gains room on the drainers.

10. **The hop budget does not bind a drainer coming in** (`closing_in`): BURN_HOPS (10 a pack) ends the hops, and the
   arena's seed 8 held from the 10th hop while the pack ran 20 -> 3 at it and burnt the pool in 0.04 s. A drainer
   closing within its keep range is hopped from however many hops were made; giving the pack up is the pursuit's
   (macros/hunting/judging.py REFUSED_PASS, SLOW_FIGHT).

11. **Cornered, past the pack** (`passing`): the pack follows the character's own way, so the way back runs through
   it; with no landing that gains room (the arena's seed 26 at 17 s before item 12: nothing priced while 7 of the pack
   came 17 -> 2.7), the Teleport goes past it, PASS_CLEAR from every drainer, and the next leave goes on with the pack
   behind.

12. **A landing with a way on** (`exits`, `opened`): the arena's seed 26 left by Teleport into a pocket of the
   dungeon (14.3 s), stood there while the pack lost it, and was cornered when it came back (no footing within 28 but
   toward the pack, death at 23.2 s); among the leave's landings those with a footed ring spot that gains room on the
   drainers come first.

Off: as before, exactly (no type drains, no memory, no far leave, no refill escape, Teleport's bar alone).
"""

import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

from inventory_tracking.combat.pack import HOP_TURNS, PACK_SEEN
from inventory_tracking.combat.threats import manaburn
from inventory_tracking.levels.geometry import Point


# 2026-10-23 (the death of 18:57:45 in Flayer Dungeon Level 1, take 20261023T155650Z-88; the player: "we must not die").
# True: items 1-12 of the module text. False: as before.
MANA_ESCAPE = True  # on 2026-10-24 ~09:50, the player: "Turn it on (Recommended)" (gate: death scene 10/20 -> 0/20)

# monstats.txt rows whose A1 carries the mana element in Hell (El1Type 'mana', El1Pct(H), El1MinD(H), El1MaxD(H); the
# installed game's, pricing/raw/d2data/monstats.json, read 2026-10-23; tests/.../combat/threats/test_drain_escape.py
# checks them against it when it is there): hcIdx -> (chance, least, most).
MANA_ELEMENT: dict[int, tuple[float, float, float]] = {
    38: (0.40, 200.0, 300.0),  # wraith1 Ghost
    39: (0.45, 200.0, 300.0),  # wraith2 Wraith
    40: (0.50, 200.0, 300.0),  # wraith3 Specter
    41: (0.60, 200.0, 300.0),  # wraith4 Apparition
    42: (0.70, 200.0, 300.0),  # wraith5 Dark Shape
    631: (0.50, 200.0, 300.0),  # wraith6 Ghost
    632: (0.50, 200.0, 300.0),  # wraith7 Wraith
    633: (0.50, 200.0, 300.0),  # wraith8 Specter
    732: (0.50, 200.0, 300.0),  # wraith9 Specter
    118: (0.40, 200.0, 300.0),  # willowisp1 Gloam
    119: (0.60, 200.0, 300.0),  # willowisp2 Swamp Ghost
    120: (0.80, 200.0, 300.0),  # willowisp3 Burning Soul
    121: (0.90, 200.0, 300.0),  # willowisp4 Black Soul
    639: (0.90, 200.0, 300.0),  # willowisp5 Gloam
    640: (0.90, 200.0, 300.0),  # willowisp6 Black Soul
    641: (0.90, 200.0, 300.0),  # willowisp7 Burning Soul
    733: (0.90, 200.0, 300.0),  # willowisp8 Burning Soul
}
BURN_LEAST = 100.0  # a row whose most is under this is no threat to the pool (goatman6 10-20, foulcrow7 10-33)

# The burn seen: a fall of BURN_SHARE of the pool since the look before, within FALL_SECONDS, a drainer in reach. The
# take's one blow took 63 %; a strike costs 16, a Teleport 11-24, the regeneration gives about 36 a second
BURN_SHARE = 0.2
FALL_SECONDS = 1.0
BURN_HOLD = 4.0  # seconds the leave stays first after a burn, a drainer in reach
RECOVERED = 0.6  # of the pool (manaburn.py MANA_SAFE): under it, a burn within RECOVER_SECONDS keeps the leave first
RECOVER_SECONDS = 20.0
BURN_SAID = 'burnt'
# BURN_COVER (2026-10-24, rca/2026-10-24/manaburn-cycle-findings.md §3; the player's "we must not die"): the leave after
# a burn is held by what the next burn would leave, not by the pool's share. The arena's manaburn-death seed 3 (GLUED,
# the pet knobs on) died so: the burn of 482 at 2.3 s, the leave first while the mana came back to ~400, a
# Rejuvenation for the mana at 12.6 s filled it to 739, and at once the leave let go (the burn 10 s old, the mana over
# RECOVERED) with 14-15 Dark Shapes within 18; two blows at 15.1-15.2 s took the mana to 0, no Teleport after, dead at
# 30.6 s (the leave held past the refill: alive, least life 0.35). Live, 18:53:12-13 (take 20261024T155059Z-113):
# four leaves at 735 of 745 mana with one Ghost about, by BURN_HOLD alone; 18:53:25-31: the leave let go at 447 against
# the 519 its Ghosts burnt in one contact. True: within RECOVER_SECONDS of a burn the leave stays first while
# COVER_PACK or more drainers are in reach, whatever the mana; with fewer, as before (BURN_HOLD, then under RECOVERED),
# but BURN_HOLD lets go once the mana less the burn seen is over manaburn.py RESERVE (another such burn leaves an
# escape). Holding a lone drainer's leave to that mark too (the arena's cut of 18:52:51, seed 3) only made more leaves
# the Extra Fast Ghosts caught anyway: kills 9 -> 5, the least mana 236 -> 1. False: BURN_HOLD, then RECOVERED, as
# before.
# Off after its gate (2026-10-24 ~20:00, 20 seeds GLUED): manaburn seed 3 saved but seed 8 killed (the held leave
# zeroes the life budget and stops the keep-range hops, `Safety.pack_back`; its landings did not shake the pack), and
# the 18:52:51 Ghost cut's kills 14.4 -> 11.7. A longer leave is not the way out; a leave that gets clear is.
BURN_COVER = False
COVER_PACK = 3  # drainers in reach that hold the leave whatever the mana (the death: 14-15; live 18:53: 1-3)

# The leave's landings: lengths from the character (the take's Teleports flew up to 29.7), clear of every drainer's
# keep range by LEAVE_CLEAR (what an Extra Fast Dark Shape runs in 0.4 s: 15.6 a second, the take)
FAR_LENGTHS = (30.0, 27.0, 24.0)
LEAVE_CLEAR = 6.0

# A drainer that came CLOSING units nearer the character within CLOSING_SECONDS goes for it, a demon nearer it or not
# (item 7: the take's Dark Shapes went for the character with the bound demon and the mercenary by it, both unhurt)
CLOSING = 2.0
CLOSING_SECONDS = 0.6

# The clearest landings where none is clear (item 8): a ring of CLEAREST_LENGTHS every CLEAREST_STEP degrees, at least
# CLEAREST_GAIN units farther beyond the nearest keep range than the character, CLEAREST_MOST of them
CLEAREST_LENGTHS = (16.0, 22.0, 28.0)
CLEAREST_STEP = 30
CLEAREST_GAIN = 4.0
CLEAREST_MOST = 4

# The way back (item 9): the character's places every TRAIL_STEP units over TRAIL_SECONDS; a leave goes to the latest
# TRAIL_MOST of them TRAIL_LEAST or more away and clear of every keep range
TRAIL_STEP = 6.0
TRAIL_SECONDS = 40.0
TRAIL_LEAST = 12.0
TRAIL_REACH = 26.0  # the navigator steps only to a place on the screen (the take's longest Teleport: 29.7)
TRAIL_MOST = 3

# Past the pack (item 11): landings PASS_CLEAR or more from every drainer (what an Extra Fast Dark Shape runs in 0.6 s
# beside its 3-unit reach), PASS_MOST of them
PASS_CLEAR = 12.0
PASS_MOST = 3

# A refill escape is made within REFILL_FRESH s of the look that priced it
REFILL_FRESH = 0.6

# skills.txt rows of the moves the safety offers beside Teleport (manaburn.py TELEPORT_ROW's columns; the installed
# game's, read 2026-10-23): Blade Warp 390 (mana 15, lvlmana 0, minmana 1, manashift 8)
SKILL_ROWS = {390: {'mana': 15, 'lvlmana': 0, 'minmana': 1, 'manashift': 8}}
NO_MANA = 'no mana for its skill'


def threat(txt: int) -> bool:
    """Whether a type's own blows burn the pool (MANA_ELEMENT, its most BURN_LEAST or more)."""
    row = MANA_ELEMENT.get(txt)
    return row is not None and row[2] >= BURN_LEAST


def drains(m) -> bool:
    """Whether a hostile (with `txt`, `modifiers`) drains mana by its hits: Mana Burn (manaburn.py DRAINING), or with
    MANA_ESCAPE its type's own mana element (`threat`)."""
    return manaburn.drains(tuple(m.modifiers)) or (MANA_ESCAPE and threat(m.txt))


def widened(
    here: Point,
    found: Sequence[manaburn.Burner],
    kept: Sequence[manaburn.Burner],
    escaping: bool,
    hostiles: Iterable = (),
) -> list[manaburn.Burner]:
    """The burners kept at range (macros/safety.py `kept_at_range`) with MANA_ESCAPE: in a drain fight (a kept burner
    drains) or while a burn is remembered (`escaping`), the drainers by type among `hostiles` too (`typed_burners`,
    within PACK_SEEN, those no threat gate judged), and all `found` while escaping. A plain drainer alone is fought as
    before until it burns (item 2: kept at range on its own, the arena's Burning Souls of danger-plains-0508 gave 3.7
    kills against 14.2). Off: `kept`."""
    if not MANA_ESCAPE:
        return list(kept)
    base = list(found) if escaping else list(kept)
    if not escaping and not any(b.drains for b in kept):
        return base
    units = {b.unit for b in base}
    # The Mana Burn ones the threat gate left out stay out (manaburn.py `threatening`: off's judgement; danger-area89-
    # 0428 lost 1.1 kills of 7 to them); the plain drainers by type, which no gate judged, come in
    near = [b for b in typed_burners(hostiles) if math.dist(here, b.at) <= PACK_SEEN]
    for b in near:
        if b.unit not in units:
            units.add(b.unit)
            base.append(b)
    return base


def typed_burners(hostiles: Iterable) -> list[manaburn.Burner]:
    """The melee drainers by type among `hostiles` (`threat`, Mana Burn or not; the wraiths, AI Wraith: they come for
    the character) as burners the landings keep clear of by their keep range (manaburn.py LANDING_ONLY: no hop of
    their own, no approach barred). Not the casters (manaburn.py `caster`: the will-o-wisps fight from range with Chain
    Lightning and touch only when by the character): with the 22 plain Extra Fast Burning Souls of the arena's
    danger-plains-0508 kept clear of, its kills fell 13.6 -> 9.2 (10 seeds); barring and making hops too, 3.85 of
    14.2. Their burn is answered by the leave (item 3)."""
    return [
        manaburn.Burner(m.unit, m.at, manaburn.keep_of(m.txt, tuple(m.modifiers)), manaburn.leader(m.flags))
        for m in hostiles
        if threat(m.txt) and not manaburn.caster(m.txt)
    ]


def drainers_near(here: Point, hostiles: Iterable) -> int:
    """The draining hostiles (`drains`) within PACK_SEEN of the character: a fall of the mana with one of them about is
    a burn, though the look after the blow may find it out of its reach (the arena's seed 19: hopped 25 off by then)."""
    return sum(1 for m in hostiles if drains(m) and math.dist(here, m.at) <= PACK_SEEN)


@dataclass
class BurnWatch:
    """The last burn seen (`seen`), whether the leave stays first (`leaving`), and the drainers' distances at the last
    look (`closing_in`)."""

    burnt_at: float = -math.inf
    points: float = 0.0
    # unit -> (clock, distance to the character) at the looks of the last CLOSING_SECONDS
    gaps: dict[int, list[tuple[float, float]]] = field(default_factory=dict)
    # The character's way, (clock, place) every TRAIL_STEP units over the last TRAIL_SECONDS (`walked`)
    trail: list[tuple[float, Point]] = field(default_factory=list)

    def walked(self, now: float, here: Point) -> None:
        """The character's place at a look, kept on the trail when TRAIL_STEP or more from the last one kept."""
        if not MANA_ESCAPE:
            return
        self.trail = [entry for entry in self.trail if 0.0 <= now - entry[0] <= TRAIL_SECONDS]
        if not self.trail or math.dist(self.trail[-1][1], here) >= TRAIL_STEP:
            self.trail.append((now, here))

    def back(self, here: Point, keeps: Sequence[tuple[Point, float]]) -> list[Point]:
        """The way back (item 9): the trail's places TRAIL_LEAST to TRAIL_REACH from the character (one Teleport's,
        on the screen) that lie farther beyond the nearest keep range than the character does, those clear of every
        keep range by LEAVE_CLEAR first, then the clearest; TRAIL_MOST of them."""
        now = _margin(here, keeps)
        found = []
        for _, at in reversed(self.trail):
            if not TRAIL_LEAST <= math.dist(at, here) <= TRAIL_REACH:
                continue
            gain = _margin(at, keeps)
            if gain > now:
                found.append((gain < LEAVE_CLEAR, -gain, at))
        return [at for _, _, at in sorted(found)[:TRAIL_MOST]]

    def closing_in(self, now: float, here: Point, burning: Sequence[manaburn.Burner], hostiles: Iterable = ()) -> bool:
        """Whether a melee drainer by type (`threat`, not a `manaburn.caster`: the wraiths, AI Wraith, by `hostiles`'
        types) within its keep range came CLOSING units nearer the character within the last CLOSING_SECONDS (items 7
        and 10): it is coming for the character, a demon nearer it or not (the take's Dark Shapes), and the hop answers
        it past the hop budget. Not the Mana Burn monsters of other types, which the demons hold as the Herald tactic
        says (the arena's Flayers of danger-area89-0428: 11 -> 6 kills in one stand seed), nor the casters (its Gloams
        of danger-area86-0407: the stand's lowest life 0.855 -> 0.589). Each look's distances are kept. False with
        MANA_ESCAPE off."""
        if not MANA_ESCAPE:
            return False
        wraiths = {m.unit for m in hostiles if threat(m.txt) and not manaburn.caster(m.txt)}
        coming = False
        for b in manaburn.triggers(burning):
            if not b.drains or b.unit not in wraiths:
                continue
            gap = math.dist(here, b.at)
            seen = [entry for entry in self.gaps.get(b.unit, ()) if 0.0 <= now - entry[0] <= CLOSING_SECONDS]
            if gap < b.keep and seen and max(entry[1] for entry in seen) - gap >= CLOSING:
                coming = True
            self.gaps[b.unit] = [*seen, (now, gap)]
        return coming

    def seen(self, history: Iterable[tuple[float, ...]], now: float, mana: float, most: float, near: int) -> None:
        """A burn: the mana fell BURN_SHARE of the pool from the most read within FALL_SECONDS (same pool), with `near`
        drainers about (`drainers_near`)."""
        if not MANA_ESCAPE or near <= 0 or most <= 0:
            return
        held = [
            entry[1]
            for entry in history
            if 0.0 <= now - entry[0] <= FALL_SECONDS and (len(entry) < 3 or abs(entry[2] - most) <= manaburn.MOST_SLACK)
        ]
        fell = max(held, default=mana) - mana
        if fell >= BURN_SHARE * most:
            self.burnt_at, self.points = now, fell

    def leaving(self, now: float, mana: float, most: float, near: int) -> str | None:
        """Why the leave stays first, in words (it starts with manaburn.MANA_SAID's words after the caller's), or None:
        a drainer in reach (`near`) within BURN_HOLD s of a burn, or within RECOVER_SECONDS of one with the mana under
        RECOVERED of the pool; with BURN_COVER, within RECOVER_SECONDS while COVER_PACK or more are in reach, and
        BURN_HOLD only while the mana less the burn seen is under manaburn.py RESERVE."""
        if not MANA_ESCAPE or near <= 0 or most <= 0:
            return None
        since = now - self.burnt_at
        recovering = since <= RECOVER_SECONDS and mana < RECOVERED * most
        if BURN_COVER and near >= COVER_PACK:
            held = since <= RECOVER_SECONDS  # the pack covers the character: a refill is no reason to stay
        elif BURN_COVER:
            held = (since <= BURN_HOLD and mana - self.points < manaburn.RESERVE) or recovering
        else:
            held = since <= BURN_HOLD or recovering
        if held:
            return (
                f'mana {mana:.0f} of {most:.0f}, {BURN_SAID} {self.points:.0f} {since:.1f} s ago, '
                f'{near} drainers in reach'
            )
        return None


def _keeps(burning: Sequence[manaburn.Burner], hostiles: Iterable) -> list[tuple[Point, float]]:
    """(place, keep range) of every drainer: the draining burners and the draining hostiles (`drains`)."""
    keeps = [(b.at, b.keep) for b in burning if b.drains]
    return keeps + [(m.at, manaburn.keep_of(m.txt, tuple(m.modifiers))) for m in hostiles if drains(m)]


def _margin(spot: Point, keeps: Sequence[tuple[Point, float]]) -> float:
    """Units `spot` lies beyond the nearest keep range (negative: inside one)."""
    return min((math.dist(spot, at) - keep for at, keep in keeps), default=math.inf)


def far_spots(
    here: Point,
    burning: Sequence[manaburn.Burner],
    hostiles: Iterable,
    footed: Callable[[Point], bool] | None = None,
    watch: BurnWatch | None = None,
) -> list[Point]:
    """The leave's landings out of reach (item 4), best first: FAR_LENGTHS along the way from the drainers' centre
    (those within PACK_SEEN, else all), turned by combat/pack.py HOP_TURNS, each clear of every drainer of `burning` and
    of every draining hostile by its keep range and LEAVE_CLEAR, on footing (`footed`, None: any); then the way back
    (`BurnWatch.back` of `watch`); with none of those, the clearest (`clearest`). Empty with MANA_ESCAPE off or no
    drainer."""
    if not MANA_ESCAPE:
        return []
    keeps = _keeps(burning, hostiles)
    if not keeps:
        return []
    near = [at for at, _ in keeps if math.dist(here, at) <= PACK_SEEN] or [at for at, _ in keeps]
    middle = (sum(p[0] for p in near) / len(near), sum(p[1] for p in near) / len(near))
    heading = math.atan2(here[1] - middle[1], here[0] - middle[0]) if math.dist(here, middle) > 1e-6 else 0.0
    found = []
    for turn in HOP_TURNS:
        angle = heading + math.radians(turn)
        for length in FAR_LENGTHS:
            spot = (here[0] + length * math.cos(angle), here[1] + length * math.sin(angle))
            if _margin(spot, keeps) >= LEAVE_CLEAR and (footed is None or footed(spot)):
                found.append(spot)
    back = watch.back(here, keeps) if watch is not None else []
    return opened(found + back, keeps, footed) or clearest(here, keeps, footed) or passing(here, keeps, footed, watch)


def exits(spot: Point, keeps: Sequence[tuple[Point, float]], footed: Callable[[Point], bool] | None) -> bool:
    """Whether a landing has a way on (item 12): a ring spot (CLEAREST_LENGTHS, every CLEAREST_STEP degrees) on
    footing that lies farther beyond the nearest keep range than the landing. True with no footing known."""
    if footed is None:
        return True
    now = _margin(spot, keeps)
    for degrees in range(0, 360, CLEAREST_STEP):
        angle = math.radians(degrees)
        for length in CLEAREST_LENGTHS:
            ahead = (spot[0] + length * math.cos(angle), spot[1] + length * math.sin(angle))
            if footed(ahead) and _margin(ahead, keeps) > now:
                return True
    return False


def opened(
    spots: Sequence[Point], keeps: Sequence[tuple[Point, float]], footed: Callable[[Point], bool] | None
) -> list[Point]:
    """The landings with a way on (`exits`), when any has one; else all of them."""
    found = [spot for spot in spots if exits(spot, keeps, footed)]
    return found or list(spots)


def passing(
    here: Point,
    keeps: Sequence[tuple[Point, float]],
    footed: Callable[[Point], bool] | None = None,
    watch: BurnWatch | None = None,
) -> list[Point]:
    """Cornered (item 11: no landing gains room, the pack between the character and every way out, as it follows the
    character's own way): the landings within TRAIL_REACH, the trail's and the ring's on footing, PASS_CLEAR or more
    from every drainer, the farthest from the nearest first, PASS_MOST of them: a Teleport past the pack, and the next
    leave goes on from there with the pack behind (a Teleport covers about 50 units a second, an Extra Fast Dark Shape
    15.6)."""
    spots = [
        at for _, at in (watch.trail if watch is not None else ()) if TRAIL_LEAST <= math.dist(at, here) <= TRAIL_REACH
    ]
    for degrees in range(0, 360, CLEAREST_STEP):
        angle = math.radians(degrees)
        for length in CLEAREST_LENGTHS:
            spot = (here[0] + length * math.cos(angle), here[1] + length * math.sin(angle))
            if footed is None or footed(spot):
                spots.append(spot)
    ranked = []
    for spot in spots:
        nearest = min(math.dist(spot, at) for at, _ in keeps)
        if nearest >= PASS_CLEAR:
            ranked.append((-nearest, spot))
    return [spot for _, spot in sorted(ranked)[:PASS_MOST]]


def gains(here: Point, spot: Point, burning: Sequence[manaburn.Burner], hostiles: Iterable) -> bool:
    """Whether a landing at `spot` is a way out under a burn that does not land clear: farther beyond the nearest
    drainer's keep range than `here` (the way back, item 9), or PASS_CLEAR or more from every drainer while `here` is
    nearer one than that (past the pack, item 11). False with MANA_ESCAPE off."""
    if not MANA_ESCAPE:
        return False
    keeps = _keeps(burning, hostiles)
    if not keeps:
        return False
    if _margin(spot, keeps) > _margin(here, keeps):
        return True
    nearest = min(math.dist(spot, at) for at, _ in keeps)
    return nearest >= PASS_CLEAR and nearest > min(math.dist(here, at) for at, _ in keeps)


def clearest(
    here: Point, keeps: Sequence[tuple[Point, float]], footed: Callable[[Point], bool] | None = None
) -> list[Point]:
    """With no landing clear of every drainer (item 8: a hop's spots must be clear of each keep range, and among a
    pack spread round the character none is; the arena's seed 12 found none and held while 13 of the pack closed from
    15.7 to 2.7): the ring's spots (CLEAREST_LENGTHS, every CLEAREST_STEP degrees) that lie farther beyond the nearest
    keep range than the character does by CLEAREST_GAIN, on footing (`footed`, None: any), the clearest first,
    CLEAREST_MOST of them."""
    if not keeps:
        return []
    now = _margin(here, keeps)
    ring = []
    for degrees in range(0, 360, CLEAREST_STEP):
        angle = math.radians(degrees)
        for length in CLEAREST_LENGTHS:
            spot = (here[0] + length * math.cos(angle), here[1] + length * math.sin(angle))
            gain = _margin(spot, keeps)
            if gain >= now + CLEAREST_GAIN and (footed is None or footed(spot)):
                ring.append((-gain, spot))
    return [spot for _, spot in sorted(ring)[:CLEAREST_MOST]]


def urgent(burning: Sequence[manaburn.Burner], coming: bool) -> bool:
    """Whether no clear landing is still no reason to stay (item 8): a drainer closing in (`BurnWatch.closing_in`), or
    an Extra Fast one kept at range (manaburn.py FAST_KEEP: it runs its keep range in about a second, 15.6 units a
    second in the take). Not a slow one standing off: danger-area89-0428's Mana Burn minions (not Extra Fast) cost 2
    kills in 2 of 30 seeds to the hop. False with MANA_ESCAPE off."""
    if not MANA_ESCAPE:
        return False
    fast = any(b.drains and b.kind != manaburn.LANDING_ONLY and b.keep >= manaburn.FAST_KEEP for b in burning)
    return coming or fast


def price_clearest(
    p, burning: Sequence[manaburn.Burner], teleport: int, why: str, watch: BurnWatch | None = None
) -> int:
    """The keep range's hop where no spot is clear and it is `urgent` (item 8, macros/safety.py `burn_back`): the
    navigator's first move to each of the clearest spots
    (`clearest`), a Teleport while the mana pays for one, else a walk, priced as a dodge named `why` (2 at most); how
    many were priced. 0 with MANA_ESCAPE off or no drainer."""
    if not MANA_ESCAPE:
        return 0
    keeps = _keeps(burning, p.look.hostiles)
    if not any(b.drains for b in burning):
        return 0
    priced = 0
    back = watch.back(p.here, keeps) if watch is not None else []
    for point in opened(back + clearest(p.here, keeps, p.footed), keeps, p.footed):
        if priced >= 2 or (priced and p.clock.late()):
            break
        offered = p.options(point) if p.options is not None else (p.leg(point),)
        for step in offered:
            spot = getattr(step, 'spot', None)
            if (
                spot is None
                or math.dist(p.here, spot) <= 2
                or (getattr(step, 'skill', None) == teleport) != p.teleport_paid()
            ):
                continue
            if _margin(spot, keeps) <= _margin(p.here, keeps):
                continue
            p.move_price(step, why=why, dodge=True)
            priced += 1
            break
    return priced


def unpaid(skill: int | None, mana: float | None) -> bool:
    """Whether a move by `skill` (not Teleport: manaburn.py's bar) costs more mana than `mana` (None: unread, paid),
    by its skills.txt row at level 1 (SKILL_ROWS); False with MANA_ESCAPE off."""
    if not MANA_ESCAPE or skill is None or mana is None or skill not in SKILL_ROWS:
        return False
    return mana < manaburn.skill_mana(SKILL_ROWS[skill])


@dataclass(frozen=True)
class RefillEscape:
    """A Teleport out a look priced while the mana did not pay for it (item 5): the clock of the look, the step and
    the goal it was for, and its reason."""

    at: float
    step: object  # macros/build.py Step
    goal: object  # macros/goals.py Goal
    reason: str

    def fresh(self, now: float) -> bool:
        return 0.0 <= now - self.at <= REFILL_FRESH


def refill_of(p, places: Sequence[Point], teleport: int, why: str) -> RefillEscape | None:
    """The Teleport out a Rejuvenation for the mana makes at once (item 5): with MANA_ESCAPE and no mana for
    Teleport at this look (macros/safety.py `Pricing` `p`), the navigator's first Teleport to one of the leave's
    `places` (as `Safety.mana_leave` offers them), more than 2 units off and clear of every burner; else None."""
    if not MANA_ESCAPE or p.teleport_paid():
        return None
    for point in places:
        offered = p.options(point) if p.options is not None else (p.leg(point),)
        for step in offered:
            spot = getattr(step, 'spot', None)
            if getattr(step, 'skill', None) != teleport or spot is None or math.dist(p.here, spot) <= 2:
                continue
            if manaburn.clear_of(spot, p.burning):
                said = f'{manaburn.MANA_SAID}: {why}: Teleport after the refill'
                return RefillEscape(p.facts.now, step, p.goal, said)
    return None
