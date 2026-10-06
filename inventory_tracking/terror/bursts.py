"""Burst events in the probe logs: when the player lost much life at once, and what stood there.

The ground truth for the deadly-pack model (danger.py; danger-plan.md R4): a burst is `SHARE` of
the player's life lost within `WINDOW` seconds, or a death, from the probe's `life` events. Each
is listed with the packs around the player as the model scores them, so a burst from a pack the
model left unmarked, or a marked pack that never hurts, shows which factor is off. Monster
positions are those of the log (first sight, `back`, `gone`), not the live ones.

    uv run --offline python -m inventory_tracking.terror.bursts inventory_tracking/runs/alt-d/*/terror-probe.jsonl
"""

import argparse
import json
import math
from collections import deque
from dataclasses import dataclass, replace
from pathlib import Path

from inventory_tracking.native.layout import DEAD_MODES
from inventory_tracking.terror.danger import Pack, Unit, packs
from inventory_tracking.terror.tracker import ALIGNMENT_STAT, AURA_MODIFIER, aura, modifiers, stat


SHARE = 0.3  # of the most life
WINDOW = 1.0  # seconds
REACH = 100  # world units around the player: about a screen and a half


@dataclass(frozen=True)
class Burst:
    t: float
    area: int
    lost: int  # life points within the window
    most: int
    died: bool
    packs: tuple[Pack, ...]  # those within REACH of the player, the highest score first

    @property
    def line(self) -> str:
        what = 'died' if self.died else f'-{self.lost / self.most:.0%}'
        found = '; '.join(f'{pack.label} [{pack.band or "unmarked"} {pack.score:g}]' for pack in self.packs[:3])
        return f'{self.t:10.1f}  area {self.area:3}  {what:>5}  {found or "nothing known nearby"}'


def bursts(events, *, share=SHARE, window=WINDOW, reach=REACH) -> list[Burst]:
    units: dict[int, tuple[int, Unit]] = {}  # unit id -> (area, monster), alive
    recent: deque[tuple[float, int]] = deque()  # (t, life) within the window
    found: list[Burst] = []
    for event in events:
        kind, unit_id = event.get('event'), event.get('unit_id')
        if kind == 'left_game':
            units.clear()
            recent.clear()
        elif kind == 'seen' and 'x' in event and event.get('mode') not in DEAD_MODES:
            if not stat(event, ALIGNMENT_STAT) and event.get('txt_id') is not None:
                found_modifiers = modifiers(event)
                unit = Unit(unit_id, event['txt_id'], event['x'], event['y'], found_modifiers, aura(event))
                units[unit_id] = (event['area'], replace(unit, owner=AURA_MODIFIER in found_modifiers))
        elif kind in ('back', 'gone') and unit_id in units:
            area, unit = units[unit_id]
            units[unit_id] = (area, replace(unit, x=event['x'], y=event['y']))
        elif kind == 'died':
            units.pop(unit_id, None)
        elif kind == 'life':
            t, life, most = event['t'], event['life'], event['max']
            while recent and t - recent[0][0] > window:
                recent.popleft()
            lost = max((before for _, before in recent), default=life) - life
            died = life <= 0 < max((before for _, before in recent), default=0)
            recent.append((t, life))
            if not (died or lost >= share * most):
                continue
            here = [unit for area, unit in units.values() if area == event['area']]
            near = [pack for pack in packs(here) if math.hypot(pack.x - event['x'], pack.y - event['y']) <= reach]
            found.append(Burst(t, event['area'], lost, most, died, tuple(near)))
            recent.clear()  # one burst, not one per pass while the life stays low
            recent.append((t, life))
    return found


def read(path: Path):
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            try:
                yield json.loads(line)
            except ValueError:
                continue  # a line cut off by a stopped service


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('logs', nargs='+', type=Path, help='terror-probe.jsonl files')
    args = parser.parse_args(argv)
    total = 0
    for path in args.logs:
        found = bursts(read(path))
        total += len(found)
        if found:
            print(path)
            print('\n'.join(burst.line for burst in found))
    print(f'{total} burst event{"" if total == 1 else "s"} in {len(args.logs)} log{"" if len(args.logs) == 1 else "s"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
