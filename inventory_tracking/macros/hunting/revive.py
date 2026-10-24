"""A firing spot at a reviver raising its pack from past the strike's reach (REVIVER_STAND, 2026-10-23).

The live fights of 2026-10-23 (session 20261022T223539Z-d878def0): Cold Plains 02:08 (Fallen Shamans 5 behind a tier 5
Fallen Herald pack: 35 s, 15 jumps, 0 kills), Tal Rasha's Tomb 02:23 and 02:27-02:33 (Unravelers behind their Burning
Dead: 48 s and 350 s, 190 strikes, 96 jumps). The revivers stood 24 to 30 units off, past the blades' 22.1: the fight
struck what they raised, and combat/revivers.py REVIVERS_FIRST (whom to strike first) could not help where no line
reached them (tests/.../arena/situations/revivers.py, the module text there has the numbers).

`reviver_goal`: while the run fights a raising reviver's pack (one it covers, combat/revivers.py `covers`, stands in
the strike's reach), or the reviver stands within STAND_NEAR, the look's fight goal is that reviver (the nearest within
STAND_FROM), struck from within STAND_NEAR with a shot (the casts at the end of the reach land on it a third of the
time: echoing_strike/attack.py HIT_BY_DISTANCE; the arena's shamans 23 to 25 off were "left alone" as taking no
damage). The rest is the pursuit's as for any fight goal not reached (hunting/judging.py `judge`): the firing spot on
the engage ring with a shot at it (sight.py `firing_spots`), the way there priced by the safety as the goal's move
against holding (macros/safety.py `Safety.price`), every bar and veto of a move on it. The goal is not a clearing one,
so the reviver counts as the pursued fight's boss (hunt.py `Hunter.boss`): never left alone as one that takes no
damage, neared instead.

Every raising reviver of the look (not the goal's only) is a boss to the hunt while the switch is on (`Hunter.raisers`,
hunt.py `Hunter.boss`): the strike's "takes no damage: left alone" (`untouched`, `unharmed`) misread them in the
arena, the shaman raised to full life reading as one no cast hurt, and the one left alone raised the others again
and again (a shaman at 27% left alone 6.5 s to 30 s while 90 raises came).

A route's boss stage, a pickup, a use, a wait are not taken over: only a fight goal or none.
"""

import math
from collections.abc import Sequence
from dataclasses import replace
from typing import Protocol

from inventory_tracking.combat import revivers
from inventory_tracking.game.records import Monster, World
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.hunting.base import hostiles
from inventory_tracking.macros.travel import STANDING, label
from inventory_tracking.routes.model import FIGHT


class Hunt(Protocol):
    """What `reviver_goal` reads and writes of the hunt (hunt.py `Hunter`)."""

    raisers: frozenset[int]
    passed: dict[object, float]  # a level run's clearing goals passed (hunting/choice.py `pass_by`)

    @property
    def reach(self) -> float: ...

    @property
    def running(self) -> bool: ...


# The player, 2026-10-23: "push xp/hour", and of fights that jump about: "what is estimated exp/hour if we're jumping
# around without kills?" (the module text). True: a raising reviver is the fight's goal, struck from within STAND_NEAR,
# and every raising reviver is a boss to the hunt. Measured with combat/revivers.py REVIVERS_FIRST (its comment has the
# arena's numbers; this one alone: shamans 5 behind cleared in 11 plays of 20 against 8 off and 19 with both).
# False: the fight's goal as before.
# Off 2026-10-23 08:55: live, its goal handed the press to the route ("the route's own step takes the press") and each
# TZ next level leg ended at once with nothing left: ~30 empty legs in 30 s blocked Catacombs Level 3 with Andariel
# alive (08:51:46-08:52:16), the loop stopped. On again once the goal keeps the level run's own key.
# On again 2026-10-23 ~17:00 with REVIVER_KEEPS_RUN (below; rca/2026-10-23/unraveler-findings.md §6): the arena, 20
# seeds a scene off -> on, every danger fight, both Fane cuts, the canyon and Dominus played the same play for play
# (20 of 20 each), the live cuts of 15:07 and 15:59-16:01 too; the revivers' scenes no death, no least lowest life
# lower: shamans 5 behind cleared 14 of 20 against 7, in a run 20 against 16, 10 behind 18 against 16.
REVIVER_STAND: bool = True
# 2026-10-23 (rca/2026-10-23/unraveler-findings.md §5): the goal of 08:51:43 was the run's own one replaced by a bare
# Goal: `clearing` and `stage` dropped, so pursuit.py `routed` read no route stage, and the level run ended ("nothing is
# left to go to on this level") or, pressed, handed the press on (`run_level` Defer). True: the reviver's goal is the
# run's goal it takes over with its place, unit and reach (route, stage, `clearing` kept: the run's own fight), one
# made with no goal is a clearing one while a level run works (`Hunt.running`), and a reviver the run passed
# (`Hunt.passed`, no way to it) is not taken again. False: the bare goal, as before.
REVIVER_KEEPS_RUN: bool = True
# REVIVER_OWN_RUN (2026-10-24, rca/2026-10-23/death-halls-findings.md): the death of 23:31:06 on 2026-10-23 (Halls of
# the Dead Level 2) was the 08:51 hole again by another way in. The goal the reviver's took over was a guarded healing
# potion's "the fight first" (hunting/choice.py `goal`: `first_fight` of a level run's side drop), the run's own only
# by `guarded` (pursuit.py `routed`), and the takeover sets `guarded` False (no pickup is guarded at a reviver): no
# route stage, so each TZ next level leg ended the run or handed its press to the pickup step, 37 legs with no strike
# under a tier 5 pack. True: a goal the reviver's takes over while a level run works is the run's own clearing fight
# (`clearing`, as one made with no goal), whatever made the goal it replaced the run's. False: `clearing` as it was.
# On 2026-10-24 ~12:15, gated: halls 8/17 dead -> 0/20, 820 pairs identical (danger, fane, pursuit incl.).
REVIVER_OWN_RUN: bool = True
STAND_NEAR = 14.0  # units from the reviver the stand is within (the engage ring is 13.9: echoing_strike/attack.py)
STAND_FROM = 40.0  # units: a reviver further from the character than this is not gone for


def reviver_goal(self: Hunt, world: World, foes: Sequence[Monster], goal: Goal | None) -> Goal | None:
    """`goal`, or the fight at the nearest reviver raising the pack being fought from where no shot reaches it (the
    module text)."""
    player = world.player
    if not REVIVER_STAND or player is None:
        self.raisers = frozenset()
        return goal
    everyone = hostiles(world)  # those left alone too: what a reviver raises is wherever it stands
    covering = revivers.covers((m.unit_id, m.txt_id, (m.x, m.y), m.flags) for m in everyone)
    self.raisers = frozenset(covering)  # a boss to the hunt (hunt.py `Hunter.boss`): never left alone
    if goal is not None and (goal.do != FIGHT or (goal.stage is not None and not goal.clearing)):
        return goal  # not a fight, or a route's boss: theirs
    here, reach = (player.x, player.y), self.reach
    by_unit = {m.unit_id: m for m in everyone}
    fought = {m.unit_id for m in foes}
    covering = {unit: covered for unit, covered in covering.items() if unit in fought}
    found = []
    for unit, covered in covering.items():
        if REVIVER_KEEPS_RUN and unit in self.passed:
            continue  # the run passed it (no way there): not gone for again meanwhile
        reviver = by_unit[unit]
        away = math.dist(here, (reviver.x, reviver.y))
        if away > STAND_FROM:
            continue  # too far to go for
        if away <= STAND_NEAR or any(math.dist(here, (by_unit[u].x, by_unit[u].y)) <= reach for u in covered):
            found.append((away, unit, reviver))
    if not found:
        return goal
    _, unit, reviver = min(found)
    if goal is not None and goal.unit == unit and goal.near <= STAND_NEAR:
        return goal
    label_ = f'{label(reviver)} raising its pack: struck from within {STAND_NEAR:.0f}'
    if REVIVER_KEEPS_RUN and goal is not None:
        # The run's goal taken over: its route, stage and `clearing` say whose fight it is (pursuit.py `routed`)
        clearing = goal.clearing or (REVIVER_OWN_RUN and self.running)  # the run's own fight, guarded or not
        return replace(
            goal, label=label_, place=(reviver.x, reviver.y), do=FIGHT, near=STAND_NEAR, unit=unit, known=True,
            mark=None, guarded=False, shrine=False, clearing=clearing,
        )  # fmt: skip
    if REVIVER_KEEPS_RUN:
        return Goal(label_, (reviver.x, reviver.y), FIGHT, STAND_NEAR, STANDING, unit=unit, clearing=self.running)
    return Goal(
        f'{label(reviver)} raising its pack: struck from within {STAND_NEAR:.0f}',
        (reviver.x, reviver.y),
        FIGHT,
        STAND_NEAR,
        goal.spend if goal is not None else STANDING,
        unit=unit,
        route=goal.route if goal is not None else '',
    )
