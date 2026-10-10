"""Stage 2 of combat/plan.md: what a take says about how the player plays.

The numbers of the first Chaos Sanctuary take (2026-10-09, 4.8 minutes, manual play) set the
shape: the player taps the right mouse button every 0.2 s (held 0.08-0.12 s) and the game casts
every 0.4 s (ten frames); the aimed monster is 12 units away at the median (5.5 to 21 between
the deciles); the pointer sits on the monster or a little short of it, within 4 units across;
play alternates runs of 0.7 s with casts of 0.4 s. Monster life in memory is a 0-128 fraction of
the maximum (the client is not told absolute points), so damage here is in 128ths of a life.
"""

import json
import math
import statistics
from collections.abc import Iterable
from itertools import pairwise
from pathlib import Path
from typing import Any

from inventory_tracking.combat.takes import LIFE_SCALE, Take, ground_under_pointer, monsters_of, player_of
from inventory_tracking.macros.routines import ACTING


RUN_MODES = frozenset((2, 3, 6))  # walk, run, town walk
HIT_WINDOW = 0.6  # seconds after a press within which hits are its
COMBAT_REACH = 30.0  # world units: a second with a hostile this near is a combat second


def deciles(values: Iterable[float]) -> list[float] | None:
    """[p10, p50, p90] rounded, or None for fewer than three values."""
    found = sorted(values)
    if len(found) < 3:
        return None
    cuts = statistics.quantiles(found, n=10)
    return [round(cuts[0], 2), round(cuts[4], 2), round(cuts[8], 2)]


def frame_at(take: Take, t: float) -> dict[str, Any]:
    """The first frame at or after `t` (the last one past the end)."""
    low, high = 0, len(take.frames) - 1
    while low < high:
        mid = (low + high) // 2
        if take.frames[mid]['t'] < t:
            low = mid + 1
        else:
            high = mid
    return take.frames[low]


def aspect_of(take: Take) -> float:
    rect = next((f['rect'] for f in take.frames if f.get('rect')), None)
    return rect[2] / rect[3] if rect else 2560 / 1418


def cadence(take: Take) -> dict[str, Any]:
    """Casts and the right button: counts, hold and gap medians, cast intervals."""
    presses = [e['t'] for e in take.events if e['event'] == 'button' and e['button'] == 3 and e['down']]
    releases = [e['t'] for e in take.events if e['event'] == 'button' and e['button'] == 3 and not e['down']]
    casts = [e['t'] for e in take.events if e['event'] == 'cast']
    frames = [player for f in take.frames if (player := player_of(f)) is not None]
    casting = sum(1 for player in frames if player.mode in ACTING)
    return {
        'casts': len(casts),
        'presses': len(presses),
        'hold_seconds': deciles(up - down for down, up in zip(presses, releases, strict=False) if up >= down),
        'press_gap_seconds': deciles(b - a for a, b in pairwise(presses)),
        'cast_interval_seconds': deciles(b - a for a, b in pairwise(casts)),
        'casting_fraction': round(casting / len(frames), 3) if frames else None,
    }


def aim(take: Take) -> dict[str, Any]:
    """Per right button press: the hostile nearest the ground under the pointer, its distance, the
    aim along the character-monster line past it and across it, the hits that followed."""
    aspect = aspect_of(take)
    hits = [e for e in take.events if e['event'] == 'hit']
    distance, along, across, counts, latency = [], [], [], [], []
    for press in (e for e in take.events if e['event'] == 'button' and e['button'] == 3 and e['down']):
        frame = frame_at(take, press['t'])
        player, ground = player_of(frame), ground_under_pointer(frame, aspect)
        if player is None or ground is None:
            continue
        (x, y), (gx, gy) = player.at, ground
        live = [m for m in monsters_of(frame) if m.hostile]
        if not live:
            continue
        target = min(live, key=lambda m: math.dist(m.at, ground))
        dx, dy = target.x - x, target.y - y
        away = math.hypot(dx, dy) or 1.0
        ux, uy = dx / away, dy / away
        ax, ay = gx - target.x, gy - target.y
        distance.append(away)
        along.append(ax * ux + ay * uy)
        across.append(-ax * uy + ay * ux)
        followed = [h for h in hits if 0 <= h['t'] - press['t'] <= HIT_WINDOW]
        counts.append(len(followed))
        if followed:
            latency.append(followed[0]['t'] - press['t'])
    histogram: dict[str, int] = {}
    for count in counts:
        key = str(min(count, 8)) + ('+' if count >= 8 else '')
        histogram[key] = histogram.get(key, 0) + 1
    return {
        'presses_with_a_hostile': len(distance),
        'distance': deciles(distance),
        'along_past_the_monster': deciles(along),
        'across': deciles(across),
        'hits_within_window': dict(sorted(histogram.items())),
        'press_to_first_hit_seconds': deciles(latency),
    }


def movement(take: Take) -> dict[str, Any]:
    """Run and cast fractions and bouts: how play alternates between them."""
    modes = [player.mode for f in take.frames if (player := player_of(f)) is not None]
    if not modes:
        return {}
    period = take.seconds / max(len(take.frames) - 1, 1)
    bouts: dict[str, list[float]] = {'run': [], 'cast': [], 'other': []}
    current, length = None, 0
    for mode in modes:
        kind = 'run' if mode in RUN_MODES else 'cast' if mode in ACTING else 'other'
        if kind == current:
            length += 1
        else:
            if current is not None:
                bouts[current].append(length * period)
            current, length = kind, 1
    if current is not None:
        bouts[current].append(length * period)
    return {
        'run_fraction': round(sum(m in RUN_MODES for m in modes) / len(modes), 3),
        'cast_fraction': round(sum(m in ACTING for m in modes) / len(modes), 3),
        'bouts': {kind: {'count': len(found), 'seconds': deciles(found)} for kind, found in bouts.items()},
    }


def kills(take: Take) -> dict[str, Any]:
    """Kills, time from the first hit to the kill, damage dealt per combat second (in lives)."""
    first_hit: dict[int, float] = {}
    to_kill = []
    for event in take.events:
        if event['event'] == 'hit':
            first_hit.setdefault(event['unit'], event['t'])
        elif event['event'] == 'kill' and event['unit'] in first_hit:
            to_kill.append(event['t'] - first_hit[event['unit']])
    killed = [e for e in take.events if e['event'] == 'kill']
    damage = sum(e['life'][0] - e['life'][1] for e in take.events if e['event'] == 'hit') / LIFE_SCALE
    combat_seconds = combat_time(take)
    by_type: dict[str, int] = {}
    for event in killed:
        by_type[str(event['txt'])] = by_type.get(str(event['txt']), 0) + 1
    return {
        'kills': len(killed),
        'kills_per_minute': round(len(killed) / take.seconds * 60, 2) if take.seconds else None,
        'first_hit_to_kill_seconds': deciles(to_kill),
        'by_txt_id': dict(sorted(by_type.items(), key=lambda pair: -pair[1])),
        'combat_seconds': round(combat_seconds, 1),
        'lives_per_combat_second': round(damage / combat_seconds, 3) if combat_seconds else None,
    }


def combat_time(take: Take) -> float:
    """Seconds of the take with a live hostile within COMBAT_REACH of the character."""
    frames = 0
    for f in take.frames:
        player = player_of(f)
        if player is not None:
            frames += any(m.hostile and math.dist(m.at, player.at) <= COMBAT_REACH for m in monsters_of(f))
    return frames * take.seconds / max(len(take.frames) - 1, 1)


def analyse(take: Take) -> dict[str, Any]:
    return {
        'take': take.directory.name,
        'seconds': round(take.seconds, 1),
        'frames': len(take.frames),
        'late_frames': sum(f.get('late', 0) for f in take.frames),
        'manual_frames': sum(not f.get('macro') for f in take.frames),
        'cadence': cadence(take),
        'aim': aim(take),
        'movement': movement(take),
        'kills': kills(take),
    }


def write_analysis(directory: Path) -> dict[str, Any]:
    take = Take.load(directory)
    found = analyse(take)
    (directory / 'analysis.json').write_text(json.dumps(found, indent=1))
    return found
