"""The engagement plan for a tier 5 Herald pack: one plan kept across looks, in phases, instead of each look's own move
(see builds/warlock/TACTICS.md §4.11; rca/2026-10-26/herald-engage-findings.md).

The player, 2026-10-26 ~09:10: "we're still having issues with proper engaging T5 heralds: against a pack we're not
using DM properly and keep teleporting around => daemons loose aggro; lethargy is god knows where, random places; we're
teleporting a lot, and thesse teleports are hectic, not something tactical. like we're don't have general plan and just
do thing and then on the next step doing something that is opposite and repeat. what it should be: teleport to safe
spot, once; move daemons to get aggro with DM between char and pack; walk closer, behind the daemons that gets aggro;
put sigil of lethargy where the main battle will occur => more damage delivered; deliver damage, focus herald or fast
pack killing".

The takes of 2026-10-25/26 (196 T5 Herald fights, the findings §1): 6.2 jumps a fight, 1.9 a fight undoing the one
before within 3 s (the keep range against the firing spot, the "kept at range" retreats against each other); 29% of the
Death Marks followed by a jump within 2 s; the sigil a median 5.1 units off where the melee was over the next 5 s.

The phases (`Phase`), one plan a pack (`Plan`, the module's PLAN), moved on by `observe` at every look:

- STANDOFF: the pack is on the character when the plan starts. One jump out is the plan's (the safety's keep range or
  a voluntary move, as priced); the next phase begins at its landing, or once the pack is off the character.
- MARK: the Death Mark sends the demons onto the pack (builds/warlock/mark.py `pack_designated` asks `remark`). No
  voluntary jump. Done once the mark has been keyed and the demons have landed (pack.py MARK_LANDS), or the demons hold
  the pack, or no demon is out, or MARK_WAIT has passed.
- CLOSE_IN: walk (never jump) closer, behind the demons that hold the pack: no voluntary jump and no keep range's hop
  (pack.py `held`), the keep ranges' bars lifted off the walks that end clear of the melee (`walk_ok`), the fight's
  places judged by `place_ok`. The sigil goes at the contact point (`contact`), where the demons meet the pack.
- STRIKE: the character within CLOSE of the contact point: the strike's own rules (the Herald held, the T5 best line).

A real threat (macros/safety.py `Safety.real_threat`: surrounded, a burst, the life budget spent, blows in reach that
take the life, the alarm, a drainer on the character, a doll, shooters) lifts every hold of the plan, and the safety's
retreats, dodges, the mana leave and the rebuff are never held: they are its "danger" moves. A jump the plan did not
make for itself (`HOP` after the phase began) took the demons along (TACTICS.md §2.1), so the plan goes back to MARK at
its landing, not to the start. The demons losing the pack (none holding it for LOST_SECONDS, or PRESSED of it on the
character for PRESS_SECONDS) brings MARK back too: the mark again only then, never after every small move. A walk that
does not get on (STUCK_SECONDS with under STUCK_UNITS moved, nothing in the strike's reach) is let one jump.

Pure state over points; the safety (pack.py `jump_hold`) and the build (mark.py, casters.py) ask it. ENGAGE_PLAN off:
`observe` keeps no plan and every question answers as before.
"""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import Enum

from inventory_tracking.common import LOG
from inventory_tracking.levels.geometry import Point


# ENGAGE_PLAN (2026-10-26, the player's words above): True: a tier PLAN_TIER Herald pack within PLAN_SEEN is fought by
# the plan's phases. False: as before (the looks' own moves: pack.py MARK_HOLDS_JUMPS, NO_SHORT_HOPS_T5, the keep
# ranges, mark.py's re-marks).
ENGAGE_PLAN = False
PLAN_TIER = 5
PLAN_SEEN = 30.0  # units from the character a member starts the plan (pack.py HARD_SEEN)
PLAN_GONE = 3.0  # seconds with no member within PLAN_LOST of the character: the plan ends
PLAN_LOST = 40.0
STRIKE_REACH = 22.1  # units: Echoing Strike's (builds/warlock/echoing_strike/mechanics.py RANGE)
ON_US = 10.0  # units: a member nearer, not held by a demon, is on the character (pack.py PACK_BACK)
SURROUND = (3, 5.0)  # members within units: the character is surrounded (pack.py SURROUND_COUNT, SURROUND_RADIUS)
HOLDS = 5.8  # units: a companion this near a member holds it (pack.py DEMON_HOLDS)
APART = 3.0  # units: a companion nearer the character holds nobody (pack.py DEMON_APART)
REMARK_HOP = 4.0  # units: a shorter jump took no demon along (builds/warlock/mark.py REMARK_HOP)
MARK_LANDS = 0.45  # s after the mark's key: the demons have landed (pack.py MARK_LANDS)
MARK_WAIT = 2.5  # s in MARK with no mark keyed (or none that could be): on to CLOSE_IN anyway
STANDOFF_WAIT = 2.0  # s in STANDOFF with no jump out: on to MARK
HELD_SETTLE = 0.3  # s the demons hold the pack before MARK counts it taken with no key of its own
LOST_SECONDS = 0.8  # s with no companion holding the pack, demons out: the aggro is lost
PRESSED = 2  # members on the character (not held, within ON_US)
PRESS_SECONDS = 0.6
CLOSE = 16.0  # units from the contact point: STRIKE (the engage ring 13.9 and a margin)
STAND_LEAST = 9.0  # units from the contact point a walk's end or a place keeps (behind the demons, not in the melee)
MELEE_GAP = 6.0  # units from every member a walk's end or a place keeps
STUCK_SECONDS = 2.0
STUCK_UNITS = 1.5
SIGIL_KEEPS = 4.0  # units: a lying sigil this near the contact point is kept (SIGIL_RADIUS 6 less a margin)
SIGIL_COVERS = 5.5  # units: a held member this near the lying sigil stands in it (SIGIL_RADIUS 6 less SIGIL_EDGE)
SIGIL_SHARE = 0.5  # of the held members in the lying sigil: kept (the contact point drifts as members die)
THREAT_SECONDS = 1.5  # a real threat (safety.py `real_threat`) this recent: the plan steps aside. The canyon gate,
# 2026-10-26: the plan's mark after every danger jump under the Slingers' javelins raised the deaths 6 -> 14 of 80
SAID = 'engage'


class Phase(Enum):
    STANDOFF = 'standoff'
    MARK = 'mark'
    CLOSE_IN = 'close in'
    STRIKE = 'strike'


COMMITTED = (Phase.CLOSE_IN, Phase.STRIKE)


@dataclass
class Plan:
    """One tier 5 pack's plan: its phase and since when, the clocks and counts its moves are judged by."""

    key: int | None = None  # the pack's Herald unit, else its lowest member's
    phase: Phase = Phase.MARK
    began: float = -math.inf  # the plan's start
    entered: float = -math.inf  # the phase's start
    seen: float = -math.inf  # the last look a member was within PLAN_LOST
    looked: float = -math.inf  # the last look's clock
    jumps: int = 0  # jumps landed under the plan, its own included
    danger: int = 0  # jumps landed that the plan did not ask for
    marks: int = 0  # times MARK was entered
    remarks: list[str] = field(default_factory=list)  # why MARK came again
    hop_seen: float = -math.inf  # the last landing (pack.py HOP) the plan counted
    stuck_jump: bool = False  # a stuck walk's jump allowed now
    lost_since: float | None = None
    pressed_since: float | None = None
    held_since: float | None = None
    moved: list[tuple[float, Point]] = field(default_factory=list)  # (clock, where) of the last looks in CLOSE_IN
    contact_at: Point | None = None  # the contact point at the last look
    burners: bool = False  # the pack drains mana (pack.py `burning`): read by the caller
    threat: str | None = None  # the last real threat the safety saw (pack.py `JumpHold.exempt`)
    threat_at: float = -math.inf  # its clock

    def threatened(self) -> bool:
        """Whether a real threat was seen within THREAT_SECONDS of the last look: the plan steps aside (the mark, the
        sigil and the jumps are the rules' as before)."""
        return self.looked - self.threat_at <= THREAT_SECONDS

    @property
    def committed(self) -> bool:
        return self.phase in COMMITTED

    def to(self, phase: Phase, now: float, why: str) -> None:
        if phase is self.phase:
            return
        LOG.info('Macro: %s: %s -> %s: %s', SAID, self.phase.value, phase.value, why)
        if phase is Phase.MARK:
            self.marks += 1
            if self.marks > 1:
                self.remarks.append(why)
        self.phase, self.entered = phase, now
        self.lost_since = self.pressed_since = self.held_since = None
        self.moved = []
        self.stuck_jump = False


PLAN = Plan()
ACTIVE: list[bool] = [False]  # whether PLAN is a live plan
PLAN_HERE: list[Point | None] = [None]  # where the character stood at the plan's last look (pack.py `breaks_range`)


def active() -> Plan | None:
    """The live plan, None with none (or ENGAGE_PLAN off)."""
    return PLAN if ENGAGE_PLAN and ACTIVE[0] else None


def reset() -> None:
    """No plan (a test's start; a clock that went back)."""
    global PLAN
    PLAN = Plan()
    ACTIVE[0] = False
    PLAN_HERE[0] = None


def at_of(m) -> Point:
    return m.at if hasattr(m, 'at') else (m.x, m.y)


def unit_of(m) -> int:
    return m.unit if hasattr(m, 'unit') else m.unit_id


def members_of(hostiles: Iterable, here: Point, within: float) -> list:
    return [m for m in hostiles if getattr(m, 'tier', 0) >= PLAN_TIER and math.dist(here, at_of(m)) <= within]


def holders(here: Point, companions: Iterable[Point]) -> list[Point]:
    return [c for c in companions if math.dist(c, here) >= APART]


def held_points(members: Sequence[Point], here: Point, companions: Iterable[Point]) -> list[Point]:
    """The members a companion holds (one APART or more off the character within HOLDS)."""
    by = holders(here, companions)
    return [m for m in members if any(math.dist(m, c) <= HOLDS for c in by)]


def contact(members: Sequence[Point], here: Point, companions: Iterable[Point]) -> Point | None:
    """Where the demons meet the pack: the middle of the members a companion holds; None while none holds any."""
    found = held_points(members, here, companions)
    if not found:
        return None
    return (sum(p[0] for p in found) / len(found), sum(p[1] for p in found) / len(found))


def on_us(members: Sequence[Point], here: Point, companions: Iterable[Point]) -> list[Point]:
    """The members within ON_US of the character that no holding companion is nearer than it is."""
    by = holders(here, companions)
    found = []
    for m in members:
        away = math.dist(here, m)
        if away < ON_US and all(away <= math.dist(c, m) for c in by):
            found.append(m)
    return found


def surrounded(members: Sequence[Point], here: Point) -> bool:
    count, radius = SURROUND
    return sum(1 for m in members if math.dist(here, m) <= radius) >= count


def key_of(members: Sequence) -> int:
    heralds = [unit_of(m) for m in members if getattr(m, 'flags', 0) & 0x0E and not getattr(m, 'flags', 0) & 0x10]
    return heralds[0] if heralds else min(unit_of(m) for m in members)


def observe(
    now: float,
    here: Point,
    hostiles: Iterable,
    companions: Sequence[Point],
    demons_out: bool,
    hop_at: float,
    hop_units: float,
    mark_at: float,
) -> Plan | None:
    """The plan moved on by one look (the module text): `hostiles` (with `at` or `x`, `y`, `tier`, `flags`, `unit` or
    `unit_id`), the companions' places, whether a demon of the character's is out, the last landing (pack.py HOP) and
    the mark's last key (pack.py MARK). The live plan, None with none (or ENGAGE_PLAN off). One look's clock once."""
    if not ENGAGE_PLAN:
        return None
    plan = PLAN
    if ACTIVE[0] and (now < plan.looked or now - plan.looked > 10.0):
        reset()  # another game, a test, a clock that went back
        plan = PLAN
    if ACTIVE[0] and now == plan.looked:
        return plan
    found = list(hostiles)
    near = members_of(found, here, PLAN_SEEN)
    seen = members_of(found, here, PLAN_LOST)
    if not ACTIVE[0]:
        if not near:
            return None
        start(now, here, near, companions, hop_at)
        plan = PLAN
    plan.looked = now
    if seen:
        plan.seen = now
    elif now - plan.seen >= PLAN_GONE:
        end(now, f'no member of the pack within {PLAN_LOST:.0f} for {PLAN_GONE:.0f} s')
        return None
    points = [at_of(m) for m in seen]
    step(plan, now, here, points, companions, demons_out, hop_at, hop_units, mark_at)
    return plan


def start(now: float, here: Point, near: Sequence, companions: Sequence[Point], hop_at: float) -> None:
    global PLAN
    points = [at_of(m) for m in near]
    pressed = surrounded(points, here) or bool(on_us(points, here, companions))
    held = bool(held_points(points, here, companions))
    phase = Phase.STANDOFF if pressed and not held else Phase.CLOSE_IN if held else Phase.MARK
    PLAN = Plan(key=key_of(near), phase=phase, began=now, entered=now, seen=now, looked=now, hop_seen=hop_at)
    PLAN.marks = 1 if phase is Phase.MARK else 0
    ACTIVE[0] = True
    nearest = min(math.dist(here, p) for p in points)
    LOG.info(
        'Macro: %s: a tier %d Herald pack (%d near, the nearest %.1f): the plan begins at %s (ENGAGE_PLAN)',
        SAID, PLAN_TIER, len(points), nearest, phase.value,
    )  # fmt: skip


def end(now: float, why: str) -> None:
    plan = PLAN
    LOG.info(
        'Macro: %s: the plan ends after %.1f s (%s): %d jumps (%d not the plan\'s), %d marks asked, re-marked for: %s',
        SAID, now - plan.began, why, plan.jumps, plan.danger, plan.marks, '; '.join(plan.remarks) or 'nothing',
    )  # fmt: skip
    reset()


def step(
    plan: Plan,
    now: float,
    here: Point,
    members: Sequence[Point],
    companions: Sequence[Point],
    demons_out: bool,
    hop_at: float,
    hop_units: float,
    mark_at: float,
) -> None:
    """One look's transitions (the module text)."""
    if hop_at > plan.hop_seen:
        plan.hop_seen = hop_at
        if hop_units >= REMARK_HOP:
            plan.jumps += 1
            if plan.phase is Phase.STANDOFF:
                plan.to(Phase.MARK, now, f'the jump out landed ({hop_units:.0f} units)')
                return
            plan.danger += 1
            plan.to(Phase.MARK, now, f'a jump of {hop_units:.0f} took the demons along: the mark again at its landing')
            return
    if not members:
        return
    held = held_points(members, here, companions)
    plan.contact_at = contact(members, here, companions)
    if plan.phase is Phase.STANDOFF:
        if not surrounded(members, here) and not on_us(members, here, companions):
            plan.to(Phase.MARK, now, 'the pack is off the character')
        elif now - plan.entered >= STANDOFF_WAIT:
            plan.to(Phase.MARK, now, f'no jump out in {STANDOFF_WAIT:.0f} s')
        return
    reach = any(math.dist(here, m) <= STRIKE_REACH for m in members)
    if plan.phase is Phase.MARK:
        if not demons_out:
            plan.to(Phase.CLOSE_IN, now, 'no demon out to send')
        elif not reach and mark_at < plan.entered:
            plan.to(Phase.CLOSE_IN, now, "none of the pack in the mark's reach: the walk in first")
        elif mark_at >= plan.entered and now - mark_at >= MARK_LANDS:
            plan.to(Phase.CLOSE_IN, now, f'the mark keyed {now - mark_at:.2f} s ago: the demons are on the pack')
        elif held:
            plan.held_since = plan.held_since if plan.held_since is not None else now
            if now - plan.held_since >= HELD_SETTLE:
                plan.to(Phase.CLOSE_IN, now, f'the demons hold {len(held)} of the pack')
        elif now - plan.entered >= MARK_WAIT:
            plan.to(Phase.CLOSE_IN, now, f'no mark landed in {MARK_WAIT:.1f} s')
        return
    # CLOSE_IN, STRIKE: the aggro kept? (a mark again only on a member it reaches)
    if demons_out and not held and reach:
        plan.lost_since = plan.lost_since if plan.lost_since is not None else now
        if now - plan.lost_since >= LOST_SECONDS:
            plan.to(Phase.MARK, now, f'no demon on the pack for {now - plan.lost_since:.1f} s')
            return
    else:
        plan.lost_since = None
    pressing = on_us(members, here, companions)
    if demons_out and len(pressing) >= PRESSED and reach:
        plan.pressed_since = plan.pressed_since if plan.pressed_since is not None else now
        if now - plan.pressed_since >= PRESS_SECONDS:
            plan.to(Phase.MARK, now, f'{len(pressing)} of the pack on the character, not on the demons')
            return
    else:
        plan.pressed_since = None
    middle = plan.contact_at
    if middle is not None:
        close = math.dist(here, middle) <= CLOSE
        if plan.phase is Phase.CLOSE_IN and close:
            plan.to(Phase.STRIKE, now, f'{math.dist(here, middle):.1f} from where the demons hold the pack')
        elif plan.phase is Phase.STRIKE and math.dist(here, middle) > CLOSE + 4.0:
            plan.to(Phase.CLOSE_IN, now, f'the melee moved {math.dist(here, middle):.1f} off')
    plan.moved = [(t, p) for t, p in plan.moved if now - t <= STUCK_SECONDS + 0.5] + [(now, here)]
    in_reach = reach
    first = next((p for t, p in plan.moved if now - t >= STUCK_SECONDS), None)
    plan.stuck_jump = (
        plan.phase is Phase.CLOSE_IN and not in_reach and first is not None and math.dist(first, here) < STUCK_UNITS
    )


# --- What the others ask ---------------------------------------------------------------------------------------------


def holds_jump(kind: str) -> str | None:
    """Why the plan does not make a jump of `kind` now (pack.py PLACE: a voluntary one, KEEP: the keep range's hop;
    the retreats and the other escapes are the safety's danger moves, never held here), None to let it be priced as
    before. The caller lifts it on a real threat."""
    plan = active()
    if plan is None or kind not in ('place', 'keep'):
        return None
    if plan.phase is Phase.STANDOFF:
        return None  # the one jump out is the plan's
    if plan.stuck_jump and kind == 'place':
        return None  # the walk does not get on: one jump
    return f'the plan holds it ({plan.phase.value}: no jump but for danger; ENGAGE_PLAN)'


def walks() -> bool:
    """Whether the fight's places are walked to now (the plan past STANDOFF, its stuck jump not allowed)."""
    plan = active()
    return plan is not None and plan.phase is not Phase.STANDOFF and not plan.stuck_jump


def lifts_range() -> bool:
    """Whether the keep ranges' bars are off the walks now (CLOSE_IN, STRIKE): the demons hold the pack, and no real
    threat was seen (THREAT_SECONDS)."""
    plan = active()
    return plan is not None and plan.committed and not plan.threatened()


def place_ok(spot: Point, members: Sequence[Point], here: Point, companions: Sequence[Point]) -> bool:
    """A place to walk to or stand at under the plan: MELEE_GAP from every member, ON_US from those on the character,
    STAND_LEAST from the contact point (behind the demons, not in the melee)."""
    if any(math.dist(spot, m) < MELEE_GAP for m in members):
        return False
    pressing = on_us(members, here, companions)
    if any(math.dist(spot, m) < ON_US for m in pressing):
        return False
    middle = contact(members, here, companions)
    return middle is None or math.dist(spot, middle) >= STAND_LEAST


def threatened(now: float, exempt: str | None) -> None:
    """The safety's real threat at this look (pack.py `jump_hold`'s `exempt`), None: none."""
    plan = active()
    if plan is not None and exempt is not None:
        plan.threat, plan.threat_at = exempt, now


def stands_aside() -> bool:
    """Whether the live plan steps aside for a real threat (THREAT_SECONDS)."""
    plan = active()
    return plan is not None and plan.threatened()


def remark() -> bool | None:
    """The plan's word on the T5 pack's mark: True: wanted now (MARK); False: held (the demons hold the pack: the mark
    rules' re-marks wait); None: no plan, or the plan steps aside for a real threat (the rules as before)."""
    plan = active()
    if plan is None or plan.threatened():
        return None
    return plan.phase is Phase.MARK


def sigil_at(members: Sequence[Point], here: Point, companions: Sequence[Point]) -> Point | None:
    """Where the pack's sigil goes under the plan: the contact point once the demons hold the pack (CLOSE_IN, STRIKE);
    None: no plan, or no contact yet (the sigil waits for the melee to form, the omen's aside)."""
    plan = active()
    if plan is None or not plan.committed:
        return None
    return contact(members, here, companions)


def sigil_waits() -> bool:
    """Whether the pack's sigil waits: the plan in STANDOFF or MARK (the melee is not where it will be yet)."""
    plan = active()
    return plan is not None and not plan.committed and not plan.threatened()


def sigil_kept(lying: Point, members: Sequence[Point], here: Point, companions: Sequence[Point]) -> bool | None:
    """Whether the sigil that lies at `lying` is kept under the plan: within SIGIL_KEEPS of the contact point, or
    SIGIL_SHARE of the members the demons hold within SIGIL_COVERS of it; None: no plan or no contact (the caster's own
    rule)."""
    middle = sigil_at(members, here, companions)
    if middle is None:
        return None
    if math.dist(lying, middle) <= SIGIL_KEEPS:
        return True
    held = held_points(members, here, companions)
    return sum(1 for m in held if math.dist(lying, m) <= SIGIL_COVERS) >= SIGIL_SHARE * len(held)
