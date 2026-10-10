"""The input model (combat/plan.md stage 5): presses of the strike button become casts.

From the takes (2026-10-09/10): the game casts every CAST_FRAMES while the button is down or
tapped (cast bouts of 0.36-0.40 s), a press during a cast queues one more that starts when the
current one ends (384 presses gave 237 cast animations on the first take), the blades appear
BIRTH_LAG frames after the cast starts (4-5 recorded), and the focal point is the ground under the
pointer POINTER_LEAD frames before the cast starts (the pointer 6 frames before the birth).
`validate_inputs` checks the model against a take: its predicted births against the recorded
blades' first frames.
"""

from collections.abc import Callable
from typing import Any

from inventory_tracking.combat.mechanics.validate import full_casts


Point = tuple[float, float]
CAST_FRAMES = 9  # frames one cast occupies the character (0.36 s cast bouts; 9 beats 10 and 11 on the takes)
BIRTH_LAG = 5  # frames from the cast start to the blades' first frame
POINTER_LEAD = 1  # frames before the cast start whose pointer the game takes
MATCH_FRAMES = 3  # a predicted birth this near a recorded one counts as the same cast


def casts_from_presses(
    presses: list[tuple[int, bool]], pointer_at: Callable[[int], Point | None], end: int | None = None
) -> list[tuple[int, Point]]:
    """(birth frame, focal point) per cast the presses produce. A press while free casts at once;
    while a cast runs it queues one more; a button held through a cast's end casts again."""
    events = sorted(presses)
    down = False
    queued = False
    busy_until = -1  # the frame the current cast ends (exclusive)
    casts: list[tuple[int, Point]] = []
    last = end if end is not None else (events[-1][0] + CAST_FRAMES if events else -1)
    index = 0
    frame = events[0][0] if events else 0
    while frame <= last:
        while index < len(events) and events[index][0] == frame:
            down = events[index][1]
            if down and frame < busy_until:
                queued = True
            index += 1
        if frame >= busy_until and (queued or down):
            focal = pointer_at(frame - POINTER_LEAD) or pointer_at(frame)
            if focal is not None:
                casts.append((frame + BIRTH_LAG, focal))
            busy_until = frame + CAST_FRAMES
            queued = False
        frame += 1
    return casts


def validate_inputs(take, situation) -> dict[str, Any]:
    """Predicted births from the recorded presses against the recorded blades' births."""
    txt_ids = {m['unit_id']: m['txt_id'] for m in take.missiles} or None
    births = (n for n, _ in full_casts(take.frames, txt_ids, least_frames=1))
    recorded = sorted(situation.ticks[n] for n in births if n in situation.ticks)  # in the situation's ticks
    predicted = sorted(
        frame for frame, _ in casts_from_presses(situation.presses, situation.pointer.get, situation.end)
    )
    matched = 0
    pool = list(recorded)
    for frame in predicted:
        near = [r for r in pool if abs(r - frame) <= MATCH_FRAMES]
        if near:
            pool.remove(min(near, key=lambda r: abs(r - frame)))
            matched += 1
    return {
        'presses': sum(1 for _, down in situation.presses if down),
        'recorded_casts': len(recorded),
        'predicted_casts': len(predicted),
        'matched': matched,
        'precision': round(matched / len(predicted), 2) if predicted else None,
        'recall': round(matched / len(recorded), 2) if recorded else None,
    }
