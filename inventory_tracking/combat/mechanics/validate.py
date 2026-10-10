"""Emulation against a take: every full cast's blades (combat/plan.md stage 3 gate)."""

import collections
import math
import struct
from typing import Any

from inventory_tracking.combat.mechanics.echoing_strike import BLADES, MISSILE, POINTER_LAG, errors, focal_point
from inventory_tracking.combat.takes import ground_under_pointer, missiles_of, player_of


Point = tuple[float, float]


def path_position(path_hex: str) -> Point:
    fx, x, fy, y = struct.unpack_from('<HHHH', bytes.fromhex(path_hex))
    return x + fx / 65536, y + fy / 65536


def blade_tracks(
    frames: list[dict[str, Any]], txt_ids: dict[int, int] | None = None
) -> dict[int, list[tuple[int, Point]]]:
    """Missile unit -> [(frame number, position)] for the blades (txt id MISSILE; without
    `txt_ids` every missile in the frames counts)."""
    tracks: dict[int, list[tuple[int, Point]]] = collections.defaultdict(list)
    for frame in frames:
        for missile in missiles_of(frame):
            if txt_ids is None or txt_ids.get(missile.unit) == MISSILE:
                tracks[missile.unit].append((frame['n'], path_position(missile.path)))
    return tracks


def full_casts(frames, txt_ids=None, least_frames: int = 30) -> list[tuple[int, list[list[Point]]]]:
    """(first frame, the five blades' positions) per cast whose blades all lived `least_frames`."""
    births: dict[int, list[list[Point]]] = collections.defaultdict(list)
    for track in blade_tracks(frames, txt_ids).values():
        if len(track) >= least_frames:
            births[track[0][0]].append([position for _, position in track])
    return [(n, blades) for n, blades in sorted(births.items()) if len(blades) == BLADES]


JUMP = 5.0  # units between two frames of one blade: a corrupt track (a reused unit id), left out


def clean(blades: list[list[Point]]) -> list[list[Point]]:
    return [b for b in blades if all(math.dist(b[i], b[i + 1]) <= JUMP for i in range(len(b) - 1))]


def validate(frames: list[dict[str, Any]], rect, txt_ids=None) -> dict[str, Any]:
    """Per-cast root mean square errors over the take's full casts, summarised as medians, with
    the focal point fitted from the blades and with the pointer POINTER_LAG frames earlier, and
    how far the two lie apart; casts with a corrupt blade track are counted and left out."""
    by_n = {frame['n']: frame for frame in frames}
    aspect = rect[2] / rect[3]
    fitted_out, fitted_back, pointer_out, pointer_back, apart = [], [], [], [], []
    corrupt = 0
    for n, blades in full_casts(frames, txt_ids):
        caster = player_of(by_n[n])
        if caster is None:
            continue
        if len(clean(blades)) != len(blades):
            corrupt += 1
            continue
        origin = caster.at

        def player_at(k, n=n, origin=origin):
            later = player_of(by_n[n + k]) if n + k in by_n else None
            return later.at if later is not None else origin

        focal = focal_point(blades)
        out, back = errors(blades, origin, focal, player_at)
        fitted_out.append(out)
        fitted_back.append(back)
        earlier = by_n.get(n - POINTER_LAG)
        aim = ground_under_pointer(earlier, aspect) if earlier else None
        if aim is not None:
            out, back = errors(blades, origin, aim, player_at)
            pointer_out.append(out)
            pointer_back.append(back)
            apart.append(math.dist(aim, focal))
    median = lambda found: round(sorted(found)[len(found) // 2], 2) if found else None  # noqa: E731
    return {
        'casts': len(fitted_out),
        'corrupt_casts': corrupt,
        'fitted_focal': {'out': median(fitted_out), 'back': median(fitted_back)},
        'pointer_focal': {'out': median(pointer_out), 'back': median(pointer_back), 'apart': median(apart)},
    }
