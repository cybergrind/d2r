"""The Throne of Destruction's five waves and the portal to the Worldstone Chamber on a terror zone run.

The player, 2026-10-20 ~09:33: "tz leveling should do baal and trone fight". Before that ruling the route's fight with
Lister (routes/catalog/act5.py) was a seek over the whole level: it chased the level's hostiles far from the throne,
no wave came, and after SEEK_WAIT the stage was left and the game ended (04:45, 04:57 on 2026-10-20).

What brings the waves (rca/2026-10-20/throne-waves-findings.md): the throne hall's own monsters dead, and the character
in the hall. In the takes of 2026-10-11, 10-14 and 10-17 every wave came 3-20 s after the hall was clear with the
character within ~30 units of the throne; with the character 100-240 units off no wave came (10-17 23:49: 41 s between
waves 3 and 4 while it toured the level, wave 4 eight seconds after its return; today's 01:43 take, 48 s with no living
hostile in the read, 194 units off). Hostiles elsewhere on the level do not hold them (10-14: waves 3 and 4 with 19-28
alive outside the hall).

So on the Throne, for the route's fight stage with no wave boss in sight: the hall's hostiles first, then the stand
(the Throne mark, THRONE_STAND of levels/handlers/worldstone_keep.py: "west-north off actual throne", the player
2026-10-11), waited at until a wave comes. No wave for WAVE_WAIT s at the stand ends the wait (the stage is left as an
empty mark: the level is explored, then the run ends, and agenda.py `no_way_on` ends the game). After Lister, Baal
(543) turns into 559 and walks into the portal once the hall is clear (takes of 2026-10-11, 10-14, 10-17: 10-11 s after
the fifth wave's last monster died): the hall's hostiles are fought, the stand is kept until he is gone (BAAL_LEAVES at
most from the hall's clear) and PORTAL_OPENS more, then the portal is clicked; the stage not done within
BAAL_LEAVES + PORTAL_SECONDS ends the run (the same `no_way_on` end). Pure but for the log.
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Monster
from inventory_tracking.levels.geometry import Point
from inventory_tracking.macros.build import Intent
from inventory_tracking.macros.goals import FIGHT as FIGHT_GOAL, PLACE_NEAR, REACH, Goal
from inventory_tracking.routes.model import FIGHT, USE, Stage


# The player, 2026-10-20 ~09:33: "tz leveling should do baal and trone fight". False: the seek over the level as before
# (the stage left after SEEK_WAIT, the game ended after the Throne)
THRONE_WAVES = True
THRONE, CHAMBER = 131, 132  # levels.txt: Throne of Destruction, The Worldstone Chamber
THRONE_BAAL = 543  # monstats `baalthrone`: Baal on his throne, never killable (terror/tracker.py UNKILLABLE)
# monstats `baalcrabstairs` ("Baal Crab to Stairs", UNKILLABLE too): Baal walking into the portal. Verified in the four
# takes that saw him go (2026-10-11 00:12 and 00:18, 10-14 16:37, 10-17 20:49): the same unit turns from 543 into 559
# 10.1-11.3 s after the fifth wave's last monster died, walks from y 5012 to 5008 (the portal's ground point is at
# 5005) and is gone from the read 0.5-1.6 s later
BAAL_LEAVING = 559
BAAL = (THRONE_BAAL, BAAL_LEAVING)
STAND_MARK = 'Throne'  # the handler's label of the stand (levels/handlers/worldstone_keep.py)
# The stand from Baal on his throne, world units: the Throne mark (15080, 5015) against 543 at (15090.5, 5011.5) in
# every take of 2026-10-11 to 2026-10-20. Used when the card's mark is not at hand, and back for the seat.
STAND_FROM_SEAT = (-10.5, 3.5)
# Units from the seat: the throne hall. Its own monsters were first seen within ~80 of it in the takes; the waves come
# round (15088-15098, 5018-5042), 6-30 from it
HALL_UNITS = 70.0
WAVE_NEAR = 12.0  # units from the stand within which the character waits there (goals.py STAND_NEAR)
# Seconds at the stand with the hall clear and no wave before the wait ends. The waves came 3-20 s after the hall was
# clear or the wave before died (takes of 2026-10-11, 10-14, 10-17); under the watch's 75 s STALL
WAVE_WAIT = 60.0
# Seconds with the hall clear after the waves for Baal to walk into the portal: 10.1-11.3 s after the fifth wave's last
# monster died in the four takes that saw it (00:12 and 00:18 on 2026-10-11, 10-14, 10-17); the portal is clicked
# after, whatever
BAAL_LEAVES = 30.0
# Seconds after Baal (543 or 559) is gone from the read before the portal is clicked: it opens as he goes in
# (objects.txt FinalPortal: Selectable1 and 2, not 0; mode 1 its 50-frame opening). Inferred: no take read the object
# (the recorder's list held no 563 before 2026-10-20); the earliest pointer on it named by the game's hover record was
# 1.26 s after he was gone (10-14 16:40:40), the clicks that took 2.5-5.0 s after. The click is made only with the
# portal under the pointer by that record, so a closed one is never clicked, only tried again
# 2.5 since 2026-10-20 ~23:40, the player: "wait until he moves through his portal + some extra to portal to be
# activatable" (the clicks that took came 2.5-5.0 s after he was gone; was 1.0)
PORTAL_OPENS = 2.5
# The player, 2026-10-21 ~17:41: "1. wait for baal disappears 2. go near portal, wait for a few seconds 3. go through
# portal". Near: the portal's foot, where every entry stood when the level changed (from the portal's ground point:
# +0.5, +4.0 world units; the player's of 2026-10-11 to 10-17 at 3.4-3.9 south; 17:38:17.83 on 10-21 at (15090.6,
# 5009.0), the level changed 0.2 s later). The walk a click makes from the throne's west side goes round it (17:38:15-
# 17:38:17.8: south to (15083.5, 5015.5), then east and north), so the foot is gone to first, then FOOT_WAIT there.
# A few seconds: every click 0.1 s or less after Baal was gone failed (game 2, 17:24:38.6), the clicks that took came
# 2.5-5.0 s after him in the 2026-10-11 to 10-17 takes and 24.9 s on 10-21; FOOT_WAIT 3.0 at the foot, after
# PORTAL_OPENS from his going, puts the click 3 s or more after him
PORTAL_FOOT = (0.5, 4.0)
FOOT_NEAR = 2.5  # world units from the foot: stood there
FOOT_WAIT = 3.0
# FOOT_HOLD (2026-10-25, game 125 at 14:11:28-14:11:43): the Teleport to the foot landed at (15088.3, 5011.7), 3.48 from
# it, at the edge of FOOT_NEAR + 1.0; the reads flipped 3.47/3.51, so the wait at the foot began and ended 57 times in
# 15 s and the pursuit, within its goal, never moved nearer (the portal took 20 s after Baal went, 3.4 s in the 11
# games before). True: stood at the foot within FOOT_NEAR + FOOT_ENTER, and kept there while within FOOT_NEAR +
# FOOT_LEAVE. False: FOOT_NEAR + 1.0 both ways, as before
FOOT_HOLD = True
FOOT_ENTER = 2.0
FOOT_LEAVE = 3.0
PORTAL_AT = (15090.0, 5005.0)  # wthrone.ds1's FinalPortal (563), read there in the takes of 17:21 and 17:34 on 10-21
PORTAL_NEAR = 'Baal is gone: to the portal'
# Seconds since the portal stage began until the run ends with the level unchanged (agenda.py `no_way_on`)
PORTAL_SECONDS = 30.0
DUE_GRACE = 2.0  # seconds a wait under way covers past its last look (`Waves.due`: the no-move watchdog)
WAVES_STAND = 'the stand for the waves'
PORTAL_WAIT = 'the portal opens once Baal leaves his throne'
# 2026-10-21 (rca/2026-10-21/worldstone-chamber-findings.md): the way on's press at the Chamber's portal (the zone's
# NEXT_LEVEL leg, running/legs.py `_way_on`) clicked it 16 times in 13 s from 17:24:25.9 while Lister's last minion
# lived (to 17:24:26.9) and Baal sat on his throne (543 until 17:24:36.9, 559 gone from the read at 17:24:38.5), and
# the game was left at 17:24:39.2: the LOOT stage after Lister had ended the level run, so `wave_goal`'s portal waits
# were never asked. True: while `portal_shut` says so the way on is the level run (the hall fought, Baal waited for at
# the stand, PORTAL_OPENS after him), and the click only after. False: the portal clicked whenever the leg comes
PORTAL_GATE = True
PORTAL_OPENING = 'Baal is gone into the portal: it opens'


@dataclass
class Waves:
    """One game's Throne: since when the stand was quiet, since when the portal was asked, since when the hall was
    clear with Baal on his throne after the waves, since when he was gone, until when a wait is under way (`due`),
    what was said."""

    game: str | None = None
    quiet_since: float | None = None
    portal_since: float | None = None
    clear_since: float | None = None
    gone_since: float | None = None
    foot_since: float | None = None
    due_until: float = -math.inf
    said: str | None = None

    def begin(self, game: str) -> None:
        if game != self.game:
            self.game, self.quiet_since, self.portal_since = game, None, None
            self.clear_since, self.gone_since, self.foot_since = None, None, None
            self.due_until, self.said = -math.inf, None

    def due(self, now: float) -> bool:
        """A wave wait or Baal's walk to the portal is under way: no stall for the no-move watchdog (loop.py
        `still`). `now`: the run's clock (time.monotonic())."""
        return now <= self.due_until

    def say(self, line: str) -> None:
        if line != self.said:
            self.said = line
            LOG.info('Macro: run: Throne of Destruction: %s', line)


GIVEN_UP = object()  # `wave_goal`'s answer when the wait ends: the caller leaves the stage


def seat_of(monsters: Sequence[Monster]) -> Point | None:
    """Baal on his throne (543), or on his way into the portal (559), where the read has him (`World.monsters`: the
    living); None when not read (far off, or gone into the portal)."""
    found = next((m for m in monsters if m.txt_id in BAAL), None)
    return (found.x, found.y) if found is not None else None


def hall_of(
    hostiles: Sequence[Monster], seat: Point, passed: Callable[[Monster], bool] = lambda monster: False
) -> list[Monster]:
    """The hostiles in the throne hall (HALL_UNITS from the seat), those passed by the clearing judge left out."""
    return [m for m in hostiles if math.dist(seat, (m.x, m.y)) <= HALL_UNITS and not passed(m)]


def hall_fight(
    hall: Sequence[Monster], here: Point, label: str, reach: float, spend: Intent, route: str, stage: Stage
) -> Goal:
    """A clearing fight with the nearest of `hall`."""
    nearest = min(hall, key=lambda m: math.dist(here, (m.x, m.y)))
    return Goal(
        f'{label}: the throne hall first ({len(hall)} left)', (nearest.x, nearest.y), FIGHT_GOAL, reach, spend,
        unit=nearest.unit_id, route=route, stage=stage, clearing=True,
    )  # fmt: skip


def stand_of(marks: Sequence[Point], seat: Point | None) -> Point | None:
    """The stand in world units: the card's Throne mark, else from the seat."""
    if marks:
        return marks[0]
    if seat is not None:
        return (seat[0] + STAND_FROM_SEAT[0], seat[1] + STAND_FROM_SEAT[1])
    return None


def wave_goal(
    waves: Waves,
    *,
    area: int,
    stage: Stage | None,
    route: str,
    found: Goal | None,
    here: Point,
    hostiles: Sequence[Monster],
    seat: Point | None,
    stand: Point | None,
    reach: float,
    spend: Intent,
    now: float,
    passed: Callable[[Monster], bool] = lambda monster: False,
) -> Goal | object | None:
    """The run's goal on the Throne for the route's fight with Lister (waves) or its portal (`stage`), from `found`
    (goals.py `goal_of`'s). `found` itself off the Throne, for another stage, with a wave's boss in sight (goal_of
    names him) or with no stand known. GIVEN_UP when the wait for a wave ends. `hostiles`: what may be struck (543 and
    559 are not), `seat`: Baal's place (`seat_of`), None once he is gone into the portal (or out of the read)."""
    if not THRONE_WAVES or area != THRONE or stage is None:
        return found
    if stage.kind == FIGHT:
        if found is not None and (found.unit is not None or found.known):
            waves.quiet_since = None  # a wave's boss in sight, or where one was last seen
            return found
        if stand is None:
            return found
        hall = hall_of(hostiles, seat if seat is not None else seat_from(stand), passed)
        if hall:
            # The hall's own monsters, and a wave's left when its boss is dead: the next wave waits for them
            waves.quiet_since = None
            return hall_fight(hall, here, stage.boss, reach, spend, route, stage)
        goal = Goal(f'{stage.boss}: {WAVES_STAND}', stand, REACH, PLACE_NEAR, spend, route=route, stage=stage)
        if math.dist(here, stand) > WAVE_NEAR:
            waves.quiet_since = None  # the wait counts at the stand only: away, no wave comes
            return goal
        if waves.quiet_since is None:
            waves.quiet_since = now
            waves.say('the hall is clear: waiting for the waves at the Throne')
        waited = now - waves.quiet_since
        if waited >= WAVE_WAIT:
            waves.due_until = -math.inf
            waves.say(f'no wave came in {waited:.0f} s at the Throne: the stage is left and the level explored')
            return GIVEN_UP
        waves.due_until = now + DUE_GRACE
        return goal
    if stage.kind == USE and stage.to == CHAMBER:
        if waves.portal_since is None:
            waves.portal_since = now
        waited = now - waves.portal_since
        if waited >= BAAL_LEAVES + PORTAL_SECONDS:
            waves.say(f'the portal to the Worldstone Chamber did not take in {waited:.0f} s: the run ends')
            return None
        if stand is None:
            return found
        label = 'Worldstone Chamber'
        if seat is not None:  # Baal still on his throne, or on his way into the portal
            waves.gone_since = None
            hall = hall_of(hostiles, seat, passed)
            if hall:
                # Inferred from the waves' rule: he left 10-11 s after the fifth wave's last monster died, never before
                waves.clear_since = None
                return hall_fight(hall, here, label, reach, spend, route, stage)
            if waves.clear_since is None:
                waves.clear_since = now
            if now - waves.clear_since < BAAL_LEAVES or PORTAL_GATE:  # the player: "1. wait for baal disappears"
                waves.due_until = now + DUE_GRACE
                waves.say('the waves are done: waiting for Baal to leave his throne for the portal')
                return Goal(f'{label}: {PORTAL_WAIT}', stand, REACH, PLACE_NEAR, spend, route=route, stage=stage)
        else:
            if waves.gone_since is None:
                waves.gone_since = now
            portal = found.place if found is not None else PORTAL_AT
            shut = foot_wait(waves, here, portal, now) if PORTAL_GATE else None
            if shut is not None:
                waves.due_until = now + DUE_GRACE
                waves.say(shut)
                foot = foot_of(portal)
                return Goal(f'{label}: {shut}', foot, REACH, FOOT_NEAR, spend, route=route, stage=stage)
            if not PORTAL_GATE and now - waves.gone_since < PORTAL_OPENS:
                waves.due_until = now + DUE_GRACE
                waves.say(PORTAL_OPENING)
                return Goal(f'{label}: {PORTAL_OPENING}', stand, REACH, PLACE_NEAR, spend, route=route, stage=stage)
        if found is not None:
            waves.say('through the portal to the Worldstone Chamber')
        return found
    return found


def foot_of(portal: Point) -> Point:
    """Where the character stands to go through the portal on its ground point `portal` (PORTAL_FOOT)."""
    return (portal[0] + PORTAL_FOOT[0], portal[1] + PORTAL_FOOT[1])


def foot_wait(waves: Waves, here: Point, portal: Point, now: float) -> str | None:
    """With Baal gone (`Waves.gone_since` set): why the portal is not clicked yet — the character not at its foot, or
    not FOOT_WAIT there and PORTAL_OPENS since he went; None once it may be."""
    away = math.dist(here, foot_of(portal))
    held = FOOT_LEAVE if waves.foot_since is not None else FOOT_ENTER
    near = FOOT_NEAR + (held if FOOT_HOLD else 1.0)
    if away > near:
        waves.foot_since = None
        return PORTAL_NEAR
    if waves.foot_since is None:
        waves.foot_since = now
    gone = waves.gone_since if waves.gone_since is not None else now
    if now - waves.foot_since < FOOT_WAIT or now - gone < PORTAL_OPENS:
        return PORTAL_OPENING
    return None


def portal_shut(
    waves: Waves, *, seat: Point | None, hall: Sequence[Monster], now: float, here: Point | None = None
) -> str | None:
    """Why the portal to the Chamber takes no click yet, None once it may: Baal (543 or 559) read (`seat`), the hall's
    hostiles (`hall`, `hall_of`) first; once he is gone from the read, PORTAL_OPENS more (`Waves.gone_since`, shared
    with `wave_goal`). The game opens the Chamber only as 559 reaches the portal (D2MOO AiThink.cpp BaalToStairs ->
    A5Q6.cpp `ACT5Q6_OpenWorldStoneChamber`; `OBJECTS_OperateFunction70_BaalPortal` warps nobody before): the object's
    mode (2 at every frame of the 17:21-17:24 take) and its selectable flag (always set) tell nothing."""
    if seat is not None:
        waves.gone_since = None
        if hall:
            return f'the throne hall first ({len(hall)} left)'
        return 'Baal has not left his throne'
    if waves.gone_since is None:
        waves.gone_since = now
    if here is not None:
        return foot_wait(waves, here, PORTAL_AT, now)
    if now - waves.gone_since < PORTAL_OPENS:
        return PORTAL_OPENING
    return None


def seat_from(stand: Point) -> Point:
    """Baal's seat from the stand (STAND_FROM_SEAT)."""
    return (stand[0] - STAND_FROM_SEAT[0], stand[1] - STAND_FROM_SEAT[1])
