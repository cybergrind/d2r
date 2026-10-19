"""What the fight against the Herald could have been: the moment of a take as a scene of the stance
harness (the monsters where they stood, standing still and not striking; the production aim; the blades
of the simulator), played with the strikes the game made and with strikes all the time.

The harness's life for an elite (twice its type's) is far from a Herald's: its full life is fitted here
to what the recorded strikes took off it (`fitted_life`). Fitted to one number, the model keeps that
number and not the shape: it takes more off the Herald while it stood 17 units off behind its pack than
the game did, and less once it had come near.
"""

import bisect
from collections.abc import Callable
from dataclasses import replace

from inventory_tracking.levels.model import Ground
from inventory_tracking.takes.takes import monsters_of
from tests.inventory_tracking.scenarios.battle.replay import Replay, character
from tests.inventory_tracking.scenarios.stance import harness


RATE = 25  # the harness's frames a second
UNDYING = 1e9


def scene_at(replay: Replay, seconds: float) -> harness.Scene:
    """The hostiles of the take's frame at `seconds`, where they stood, with the life they showed."""
    frame = replay.frames[bisect.bisect_right(replay.times, seconds) - 1]
    row = character(frame)
    bodies = [
        harness.body(m.unit, m.txt, (m.x, m.y), row.area, elite=m.elite, life=max(m.life, 1) / (m.max_life or 128))
        for m in monsters_of(frame)
        if m.hostile
    ]
    return harness.scene(
        f'{replay.take.directory.name} at {seconds} s', row.area, (row.x, row.y), bodies, Ground(replay.level.ground)
    )


def with_life(scene: harness.Scene, unit: int, points: float) -> harness.Scene:
    bodies = tuple(replace(body, points=points) if body.unit == unit else body for body in scene.bodies)
    return harness.Scene(scene.name, scene.area, scene.origin, bodies, scene.ground, scene.doors)


def striking_in(spans: list[tuple[float, float]], start: float) -> Callable[[harness.View], harness.Move | None]:
    """Strikes only within `spans` (seconds into the take; the scene begins at `start`): outside them the
    character stands idle (a walk on the spot, the harness's only way to cast nothing)."""
    frames = [(round((since - start) * RATE), round((to - start) * RATE)) for since, to in spans]

    def strategy(view: harness.View) -> harness.Move | None:
        if any(since <= view.frame < to for since, to in frames):
            return None
        ahead = [since - view.frame for since, _ in frames if since > view.frame]
        idle = max(min(ahead) if ahead else 2000, harness.WALK_LATENCY_FRAMES + 1)
        return harness.Move(view.seen.origin, walk=(idle - harness.WALK_LATENCY_FRAMES) * harness.RUN_SPEED / RATE)

    return strategy


def play(scene: harness.Scene, strategy, seconds: float) -> harness.Trace:
    trace = harness.Trace()
    harness.play(scene, strategy, seconds, trace=trace, near=40.0)
    return trace


def left(trace: harness.Trace, unit: int, seconds: float, full: float) -> float:
    """The life `unit` has `seconds` into the play, in the 128ths the game shows."""
    seen = [life for frame, body, life in trace.life if body == unit and frame <= round(seconds * RATE)]
    return 128 * (seen[-1] if seen else full) / full


def dead_at(trace: harness.Trace, unit: int) -> float | None:
    frame = trace.deaths.get(unit)
    return None if frame is None else frame / RATE


def fitted_life(scene: harness.Scene, unit: int, strategy, seconds: float, lost: float) -> float:
    """The full life in points with which the strikes of `strategy` take `lost` (a share) off `unit` in `seconds`."""
    trace = play(with_life(scene, unit, UNDYING), strategy, seconds)
    taken = UNDYING * (1 - left(trace, unit, seconds, UNDYING) / 128)
    return taken / lost
