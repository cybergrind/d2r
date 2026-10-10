"""Which monsters the emulated blades touch, matched to the recorded life drops (combat/plan.md
stage 3 hit model, stage 4 calibration gate).

A contact is the first frame a blade's emulated position comes within CONTACT_RADIUS of a live
hostile's recorded position, once per blade, monster and leg (missiles.txt NextDelay 20 lets the
return hit again). Matching to the recorded `hit` events allows HIT_LAG frames: the server's life
updates reach the client in batches. On the fourth and fifth Chaos Sanctuary takes (2026-10-10)
19 in 20 contacts had a life drop within the lag (precision), while only half the life drops had
a contact before them (recall): the rest are the mercenary's, the pets', Death Mark's, later
batches, or blades the emulation misplaces (the hand moves between the press and the spawn).
"""

import collections
import math
from collections.abc import Callable
from typing import Any

from inventory_tracking.combat.mechanics.echoing_strike import OUT_FRAMES, POINTER_LAG, cast, focal_point
from inventory_tracking.combat.mechanics.validate import full_casts
from inventory_tracking.combat.takes import ground_under_pointer, monsters_of, player_of


Point = tuple[float, float]
Contact = tuple[int, int, int, str]  # cast frame, monster unit, contact frame, 'out' | 'back'

CONTACT_RADIUS = 2.0  # world units between a blade and a monster's recorded position
HIT_LAG = 20  # frames a life drop may follow its contact


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


def contacts(
    frames: list[dict[str, Any]],
    aspect: float,
    txt_ids: dict[int, int] | None = None,
    *,
    focal: str = 'pointer',
    radius: float = CONTACT_RADIUS,
) -> list[Contact]:
    """Emulated contacts over every five-blade cast of the frames, the focal point from the
    pointer (`focal='pointer'`, the policy's knowledge) or fitted from the recorded blades."""
    by_n = {frame['n']: frame for frame in frames}
    monsters = hostiles_by_frame(frames)
    found: list[Contact] = []
    for n, blades in full_casts(frames, txt_ids, least_frames=1):
        caster = player_of(by_n[n])
        if caster is None:
            continue
        origin = caster.at
        aim = pointer_focal(by_n, n, aspect) if focal == 'pointer' else focal_point(blades)
        if aim is None:
            continue

        def player_at(k: int, n: int = n, origin: Point = origin) -> Point:
            later = player_of(by_n[n + k]) if n + k in by_n else None
            return later.at if later is not None else origin

        for path in cast(origin, aim, player_at):
            touched: set[tuple[int, str]] = set()
            for k, position in enumerate(path):
                leg = 'out' if k <= OUT_FRAMES else 'back'
                for unit, where in monsters.get(n + k, {}).items():
                    if (unit, leg) not in touched and math.dist(position, where) <= radius:
                        touched.add((unit, leg))
                        found.append((n, unit, n + k, leg))
    return found


def match(
    contacts_found: list[Contact],
    events: list[dict[str, Any]],
    frame_of: Callable[[float], int | None],
    lag: int = HIT_LAG,
) -> dict[str, Any]:
    """Contacts followed by a life drop within `lag` frames (precision) and life drops preceded by
    a contact within `lag` frames (recall)."""
    hits: dict[int, list[int]] = collections.defaultdict(list)
    for event in events:
        if event['event'] == 'hit':
            n = frame_of(event['t'])
            if n is not None:
                hits[event['unit']].append(n)
    by_unit: dict[int, list[int]] = collections.defaultdict(list)
    for _, unit, k, _ in contacts_found:
        by_unit[unit].append(k)
    explained = sum(1 for _, unit, k, _ in contacts_found if any(k <= h <= k + lag for h in hits.get(unit, ())))
    total_hits = sum(len(found) for found in hits.values())
    hits_explained = sum(
        1 for unit, found in hits.items() for h in found if any(h - lag <= k <= h for k in by_unit.get(unit, ()))
    )
    legs = collections.Counter(leg for *_, leg in contacts_found)
    return {
        'contacts': len(contacts_found),
        'out': legs['out'],
        'back': legs['back'],
        'hits': total_hits,
        'contact_to_hit': round(explained / len(contacts_found), 3) if contacts_found else None,
        'hit_from_contact': round(hits_explained / total_hits, 3) if total_hits else None,
    }


def calibrate(take) -> dict[str, Any]:
    """The hit model's precision and recall on a take, from the pointer and from the fitted focal point."""
    rect = next((f['rect'] for f in take.frames if f.get('rect')), [0, 0, 2560, 1418])
    aspect = rect[2] / rect[3]
    txt_ids = {m['unit_id']: m['txt_id'] for m in take.missiles} or None
    frame_of_t = {f['t']: f['n'] for f in take.frames}
    report: dict[str, Any] = {'take': take.directory.name, 'radius': CONTACT_RADIUS, 'lag_frames': HIT_LAG}
    for focal in ('pointer', 'fitted'):
        found = contacts(take.frames, aspect, txt_ids, focal=focal)
        report[focal] = match(found, take.events, frame_of_t.get)
    return report
