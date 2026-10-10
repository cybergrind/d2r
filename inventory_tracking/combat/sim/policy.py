"""The policies of combat/policy.py through a take's situation (combat/plan.md stage 5).

`compare` runs the recorded casts and each candidate closed loop on the same situation and scores
them by blade plus linked points per combat second (the policy-dependent terms):

- `slots`: the line sweep at exactly the recorded cast frames (the aim alone);
- `yield`: the line sweep whenever the character is free, never while the recorded character ran
  (what the game runs: takeover with yield);
- `free`: the line sweep whenever free, the record's runs ignored (the ceiling, not fluent);
- `nearest`: the hunt's rule of 2026-10-09 (the elite first, then the nearest, one unit past),
  whenever free: the live macro's aim before the line sweep reached the game;
- `live`: the aim the game's fight runs today (combat/controller.py `LiveAim`): `yield`'s sweep with
  the focal points the window lets the pointer reach, and straight at a monster in reach when the
  sweep finds no line (review.md, finding 2: `yield` alone is not what the game casts).
"""

import math
from dataclasses import dataclass
from typing import Any

from inventory_tracking.combat.controller import LiveAim
from inventory_tracking.combat.policy import RUN_MODES, Choice, LinePolicy, NearestPolicy, Observation, Policy
from inventory_tracking.combat.sim.engine import Outcome, gate, score, simulate
from inventory_tracking.combat.sim.input import BIRTH_LAG
from inventory_tracking.combat.sim.situation import Situation
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.macros.view import Viewport


FREE, YIELD, SLOTS, NEAREST, LIVE = 'free', 'yield', 'slots', 'nearest', 'live'
MODES = (SLOTS, YIELD, FREE, NEAREST, LIVE)
COMBAT_REACH = 30.0  # a frame with a live hostile this near is combat time (analysis.py)


@dataclass
class AtSlots:
    """`policy` asked only at the frames the record cast."""

    policy: Policy
    slots: frozenset[int]

    def __call__(self, seen: Observation) -> Choice | None:
        return self.policy(seen) if seen.frame in self.slots else None


def candidate(situation: Situation, mode: str, **options: Any) -> Policy:
    """The policy `compare` runs under `mode`; `options` go to the policy (damage_of, offsets...)."""
    if mode == NEAREST:
        return NearestPolicy(**options)
    if mode == LIVE:
        return LiveAim(LinePolicy(yields=True, **options), Viewport(situation.aspect).reachable_focal)
    if mode == SLOTS:
        return AtSlots(LinePolicy(yields=False, **options), frozenset(c.frame - BIRTH_LAG for c in situation.casts))
    return LinePolicy(yields=mode == YIELD, **options)


def run_policy(situation: Situation, policy: Policy, **options: Any) -> Outcome:
    """The policy through the situation, closed loop (the engine asks it at every free frame)."""
    return simulate(situation, [], policy=policy, **options)


def policy_score(situation: Situation, outcome: Outcome) -> dict[str, Any]:
    """The stage 5 yardstick: blade plus linked points per combat second, with the full score beside."""
    combat_frames = sum(
        1
        for frame in range(situation.start, situation.end + 1)
        if any(
            frame in t.path and math.dist(t.path[frame], situation.player_at(frame)) <= COMBAT_REACH
            for t in situation.monsters.values()
        )
    )
    seconds = combat_frames / GAME_RATE or 1.0
    placement = outcome.placement  # the life taken, not the blows: overkill earns nothing
    full = score(situation, outcome)
    full.update(combat_seconds=round(seconds, 1), placement_points=round(placement))
    full['placement_per_combat_second'] = round(placement / seconds)
    return full


def compare(situation: Situation, modes: tuple[str, ...] = MODES, **options: Any) -> dict[str, Any]:
    """The recorded casts and each candidate through the same situation (`options` to `simulate`)."""
    recorded = [(c.frame, c.fitted) for c in situation.casts]
    manual = simulate(situation, recorded, **options)
    report: dict[str, Any] = {
        'manual': {'casts': len(recorded), 'score': policy_score(situation, manual), 'gate': gate(situation, manual)}
    }
    base = report['manual']['score']['placement_per_combat_second']
    running = sum(1 for mode in situation.modes.values() if mode in RUN_MODES)
    for mode in modes:
        outcome = run_policy(situation, candidate(situation, mode), **options)
        interrupted = sum(1 for birth, _ in outcome.cast_frames if situation.modes.get(birth - BIRTH_LAG) in RUN_MODES)
        found = policy_score(situation, outcome)
        report[mode] = {
            'casts': outcome.casts,
            'casts_while_recorded_running': interrupted,
            'recorded_running_frames': running,
            'gain': round(found['placement_per_combat_second'] / base - 1, 3) if base else None,
            'score': found,
        }
    return report
