"""The recorded blades of a take and the hit model's numbers (combat/plan.md stages 3-4).

A contact is the first frame a blade comes within CONTACT_RADIUS of a live hostile's recorded position, once per
blade, monster and leg (missiles.txt NextDelay lets the return hit again). Matching to recorded `hit` events allows
HIT_LAG frames (the server batches life updates). Precision was high (19 in 20 contacts had a drop), recall about
half: the other drops are the companions', Death Mark's, later batches or misplaced blades. The calibration that
measured it is in git history (hits.py `calibrate`, before 2026-10-19).
"""

import collections
import struct
from typing import Any

from inventory_tracking.builds.warlock.echoing_strike.mechanics import BLADES, MISSILE, POINTER_LAG
from inventory_tracking.levels.geometry import Point
from inventory_tracking.takes.takes import ground_under_pointer, missiles_of, monsters_of


CONTACT_RADIUS = 2.0  # world units between a blade and a monster's recorded position
HIT_LAG = 20  # frames a life drop may follow its contact


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
            # A path that was not read in a frame is empty (4 of 129,466 rows in the take 20261011T231408Z-39):
            # the missile has no place in that frame.
            if missile.path and (txt_ids is None or txt_ids.get(missile.unit) == MISSILE):
                tracks[missile.unit].append((frame['n'], path_position(missile.path)))
    return tracks


def full_casts(frames, txt_ids=None, least_frames: int = 30) -> list[tuple[int, list[list[Point]]]]:
    """(first frame, the five blades' positions) per cast whose blades all lived `least_frames`."""
    births: dict[int, list[list[Point]]] = collections.defaultdict(list)
    for track in blade_tracks(frames, txt_ids).values():
        if len(track) >= least_frames:
            births[track[0][0]].append([position for _, position in track])
    return [(n, blades) for n, blades in sorted(births.items()) if len(blades) == BLADES]


def hostiles_by_frame(frames: list[dict[str, Any]]) -> dict[int, dict[int, Point]]:
    """Frame number -> {monster unit: position} for live hostiles."""
    found: dict[int, dict[int, Point]] = collections.defaultdict(dict)
    for frame in frames:
        for m in monsters_of(frame):
            if m.hostile:
                found[frame['n']][m.unit] = m.at
    return found


def pointer_focal(by_n: dict[int, dict[str, Any]], n: int, aspect: float) -> Point | None:
    """The ground under the pointer POINTER_LAG frames before frame `n`, where the game aimed."""
    earlier = by_n.get(n - POINTER_LAG)
    return ground_under_pointer(earlier, aspect) if earlier else None
