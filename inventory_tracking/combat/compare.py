"""Macro against manual, from the takes (combat/plan.md stage 6).

`combat compare <takes directory>` reads every take and says, per take and per level and side, what
the play was worth by what the record shows, no simulator involved: the life points the hostiles
lost per combat second (every source: blades, companions, the link), the kills per combat minute,
and how the character spent its opportunities: of the frames in which a hostile stood within the
hunt's reach with a clear line, the share spent casting, running and standing. A take is the
macro's when most of its casts were made while a macro run was acting (the recorder's `macro` flag),
else manual. The standing share is the macro's cost: 17-66% in the Catacombs takes of 2026-10-10
against 12-21% of the player's own play, before the fight became one held strike.
"""

import statistics
from pathlib import Path
from typing import Any

from inventory_tracking.combat.analysis import combat_time
from inventory_tracking.combat.mechanics.tables import points_of
from inventory_tracking.combat.policy import RUN_MODES, Foe, NearestPolicy, Observation
from inventory_tracking.combat.sim.situation import cut
from inventory_tracking.combat.takes import LIFE_SCALE, Take
from inventory_tracking.macros.routines import ACTING


LEAST_COMBAT_SECONDS = 10.0  # a take with less combat than this says nothing


def opportunities(take: Take) -> dict[str, Any]:
    """Of the frames with a target for the hunt's rule (a live hostile in reach, the line clear):
    the shares the character spent casting, on the move and standing."""
    situation = cut(take)
    rule = NearestPolicy()
    frames = casting = running = 0
    for frame in range(situation.start, situation.end + 1):
        foes = {
            unit: Foe(track.txt, track.path[frame], 1.0, track.elite)
            for unit, track in situation.monsters.items()
            if frame in track.path
        }
        if frame not in situation.modes or not foes:
            continue
        if rule(Observation(situation.player_at(frame), foes, blocked=situation.blocked_at(frame))) is None:
            continue
        frames += 1
        mode = situation.modes[frame]
        casting += mode in ACTING
        running += mode in RUN_MODES
    if not frames:
        return {'frames': 0}
    return {
        'frames': frames,
        'casting': round(casting / frames, 2),
        'moving': round(running / frames, 2),
        'standing': round((frames - casting - running) / frames, 2),
    }


def row(take: Take) -> dict[str, Any]:
    area = int(take.manifest.get('area', 0))
    casts = [e for e in take.events if e['event'] == 'cast']
    macro = sum(bool(e.get('macro')) for e in casts)
    points = sum(
        (e['life'][0] - e['life'][1]) / LIFE_SCALE * points_of(e['txt'], area)
        for e in take.events
        if e['event'] == 'hit'
    )
    kills = sum(1 for e in take.events if e['event'] == 'kill')
    seconds = combat_time(take)
    return {
        'area': area,
        'side': 'macro' if casts and macro * 2 > len(casts) else 'manual',
        'casts': len(casts),
        'combat_seconds': round(seconds, 1),
        'points_per_combat_second': round(points / seconds) if seconds else None,
        'kills_per_combat_minute': round(kills / seconds * 60, 1) if seconds else None,
        'opportunities': opportunities(take),
    }


def spread(values: list[float]) -> dict[str, float] | None:
    return {'median': statistics.median(values), 'least': min(values), 'most': max(values)} if values else None


def compare(directory: Path) -> dict[str, Any]:
    takes: dict[str, dict[str, Any]] = {}
    for path in sorted(p for p in directory.iterdir() if (p / 'manifest.json').exists()):
        take = Take.load(path)
        if not take.frames:
            continue
        found = row(take)
        if found['combat_seconds'] >= LEAST_COMBAT_SECONDS and found['casts']:
            takes[path.name] = found
    groups: dict[str, dict[str, Any]] = {}
    for key in sorted({(found['area'], found['side']) for found in takes.values()}):
        mine = [found for found in takes.values() if (found['area'], found['side']) == key]
        groups[f'{key[0]} {key[1]}'] = {
            'takes': len(mine),
            'combat_seconds': round(sum(found['combat_seconds'] for found in mine), 1),
            'points_per_combat_second': spread([found['points_per_combat_second'] for found in mine]),
            'kills_per_combat_minute': spread([found['kills_per_combat_minute'] for found in mine]),
            'standing_with_a_target': spread(
                [found['opportunities']['standing'] for found in mine if found['opportunities']['frames']]
            ),
        }
    return {'takes': takes, 'groups': groups}


def lines(report: dict[str, Any]) -> list[str]:
    out = []
    for name, found in report['takes'].items():
        seen = found['opportunities']
        shares = (
            f'casting {seen["casting"]:.0%} moving {seen["moving"]:.0%} standing {seen["standing"]:.0%}'
            if seen['frames']
            else 'no target frames'
        )
        out.append(
            f'{name:24} {found["area"]:4} {found["side"]:6} {found["combat_seconds"]:6.1f}s '
            f'{found["points_per_combat_second"]:6} points/s {found["kills_per_combat_minute"]:5} kills/min | {shares}'
        )
    for key, found in report['groups'].items():
        points, kills, standing = (
            found['points_per_combat_second'], found['kills_per_combat_minute'], found['standing_with_a_target'],
        )  # fmt: skip
        out.append(
            f'{key:12} {found["takes"]} takes {found["combat_seconds"]:.0f}s: '
            f'{points["median"]:.0f} points/s ({points["least"]:.0f}-{points["most"]:.0f}), '
            f'{kills["median"]:g} kills/min ({kills["least"]:g}-{kills["most"]:g})'
            + (
                f', standing {standing["median"]:.0%} ({standing["least"]:.0%}-{standing["most"]:.0%})'
                if standing
                else ''
            )
        )
    return out
