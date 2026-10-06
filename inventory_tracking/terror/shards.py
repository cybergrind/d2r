"""Worldstone Shards: what each elite kill should drop, the kills and the drops seen, and the two compared.

Only Hell champions, uniques, super uniques and Heralds have a shard entry (terror/data/shards.json,
built by build_shards.py from the installed game). Outside a Terror Zone the shard is drawn from
one of five act tables; inside, and for every Herald, from the even one. Which act table is the
elite's *upgraded* class: the last class of its group whose level the monster's level reaches
(area level, or the monster's own for a boss monster; +2 for a champion, +3 for a unique or a
super unique). So the mix follows the level of the area, not its act. That rule is the classic
game's and is unconfirmed on this build beyond the user's Catacombs drops (2026-10-07): the
report below is how it gets checked.

`ShardWatch` turns the probe's events into two more: `elite_kill` (a pack leader's first death,
with its kind and whether the area was terrorized) and `shard` (a shard item first seen on the
ground: carried ones are known from the start, so dropping your own is no drop). Both go to
terror-probe.jsonl with the rest.

    uv run --offline python -m inventory_tracking.terror.shards [--levels] [terror-probe.jsonl ...]
"""

import argparse
import json
import math
from collections import deque
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.loot.ground import GROUND_MODES
from inventory_tracking.terror.tracker import (
    ALIGNMENT_STAT,
    CHAMPION_FLAG,
    HERALD_TIER_STAT,
    LEADER_FLAGS,
    SUPER_FLAG,
    SUPER_ID,
    TYPE_FLAGS,
    data_byte,
    is_minion,
    stat,
)


DATA = Path(__file__).parent / 'data' / 'shards.json'
LOGS = 'inventory_tracking/runs/alt-d/*/terror-probe.jsonl'
LEVEL_BONUS = {'champion': 2, 'unique': 3, 'super': 3}
EVEN = (0.2,) * 5
KILL_SECONDS = 10.0  # a drop belongs to an elite killed this recently...
KILL_REACH = 40  # ...and this near, in world units
KINDS = ('champion', 'unique', 'super', 'herald')
ZONES = {True: 'terror', False: 'regular', None: 'unsure'}


@dataclass(frozen=True)
class Model:
    items: dict[int, tuple[str, str]]  # item class id -> code, name; in the tables' order
    mixes: dict[int, tuple[float, ...]]  # act table -> each shard's share
    classes: dict[str, tuple[int, int, float, int]]  # class -> group, level, shards per kill, act table
    groups: dict[int, tuple[str, ...]]  # group -> its classes, lowest first
    monsters: dict[int, tuple[str, str, int]]  # monster -> champion class, unique class, own level (boss) or 0
    supers: dict[int, tuple[str, int]]  # superuniques.txt hcIdx -> class, monster
    heralds: dict[int, float]  # tier -> shards per kill
    levels: dict[int, tuple[int, int, str]]  # area -> act, Hell level, name

    @property
    def codes(self) -> list[str]:
        return [code for code, _ in self.items.values()]

    @property
    def names(self) -> list[str]:
        return [name.split()[0] for _, name in self.items.values()]


def load(data: dict) -> Model:
    return Model(
        {int(class_id): (code, name) for class_id, (code, name) in data['items'].items()},
        {int(act): tuple(weight / sum(weights) for weight in weights) for act, weights in data['mixes'].items()},
        {name: (group, level, chance, act) for name, (group, level, chance, act) in data['classes'].items()},
        {int(group): tuple(names) for group, names in data['groups'].items()},
        {int(txt_id): (champion, unique, level) for txt_id, (champion, unique, level) in data['monsters'].items()},
        {int(found): (name, monster) for found, (name, monster) in data['supers'].items()},
        {int(tier): chance for tier, chance in data['heralds'].items()},
        {int(area): (act, level, name) for area, (act, level, name) in data['levels'].items()},
    )


@cache
def table(path: Path = DATA) -> Model:
    return load(json.loads(path.read_text(encoding='utf-8')))


def upgraded(model: Model, name: str, level: int) -> str:
    """The class a monster of `level` drops from in Hell, given its own class."""
    group = model.groups.get(model.classes[name][0], ())
    for other in group[group.index(name) + 1 :] if name in group else ():
        if model.classes[other][1] > level:
            break
        name = other
    return name


def expected(
    model: Model, kind: str, txt_id: int, area: int, *, super_id=None, tier=None, terrorized=None
) -> tuple[float, list[float] | tuple[float, ...] | None] | None:
    """(shards per kill, each shard's share of them); None for a monster or a level not in the tables."""
    if kind == 'herald':
        return (model.heralds[tier], EVEN) if tier in model.heralds else None
    monster = model.supers[super_id][1] if kind == 'super' and super_id in model.supers else txt_id
    if monster not in model.monsters or area not in model.levels or kind not in LEVEL_BONUS:
        return None
    champion, unique, own_level = model.monsters[monster]
    name = model.supers[super_id][0] if kind == 'super' and super_id in model.supers else None
    name = name or (champion if kind == 'champion' else unique)
    if name not in model.classes:
        return None
    level = (own_level or model.levels[area][1]) + LEVEL_BONUS[kind]
    _, _, chance, act = model.classes[upgraded(model, name, level)]
    if not chance:
        return 0, None
    return chance, EVEN if terrorized else list(model.mixes[act])


class ShardWatch:
    def __init__(self, model: Model | None = None, *, terrorized=lambda area: None):
        self.model = model or table()
        self.terrorized = terrorized  # area -> True, False or None (not known): terror/tracker.py
        self.reset()

    def reset(self):
        self.leaders: dict[int, dict] = {}  # unit id -> kind (and tier / super unique), from first sight
        self.killed: set[int] = set()
        self.kills: deque[dict] = deque(maxlen=50)
        self.known: set[int] | None = None  # shard item units seen this game; None until the first read

    def update(self, events, now, *, items=None, area=None) -> list[dict]:
        """The kills among the probe's `events` and the drops among `items` (shard units, any mode;
        None when they were not read), to be logged with those events."""
        found = []
        for event in events:
            if event['event'] == 'left_game':
                self.reset()
            elif event['event'] == 'seen':
                self.saw(event)
            elif event['event'] == 'died' and event['unit_id'] in self.leaders:
                if event['unit_id'] in self.killed:
                    continue
                self.killed.add(event['unit_id'])
                kill = {'event': 'elite_kill', 't': round(now, 3), 'unit_id': event['unit_id']}
                kill |= {'txt_id': event.get('txt_id'), 'area': event['area'], **self.leaders[event['unit_id']]}
                kill |= {'terrorized': self.terrorized(event['area']), 'x': event.get('x'), 'y': event.get('y')}
                self.kills.append(kill)
                found.append(kill)
        if items is None:
            return found
        first, self.known = self.known is None, self.known or set()
        for item in items:
            if item.unit_id in self.known:
                continue
            self.known.add(item.unit_id)
            if first or item.mode not in GROUND_MODES or item.class_id not in self.model.items:
                continue
            kill = self.dropped_by(item, area, now)
            drop = {'event': 'shard', 't': round(now, 3), 'unit_id': item.unit_id}
            drop |= {'code': self.model.items[item.class_id][0], 'area': area, 'terrorized': self.terrorized(area)}
            drop |= {'x': item.x, 'y': item.y, 'from': kill and kill['unit_id'], 'kind': kill and kill['kind']}
            LOG.info(
                'Worldstone Shard: %s in area %s (%s)%s',
                self.model.items[item.class_id][1],
                area,
                ZONES[drop['terrorized']],
                f', from a {kill["kind"]}' if kill else '',
            )
            found.append(drop)
        return found

    def saw(self, event):
        flags = data_byte(event, TYPE_FLAGS) or 0
        if stat(event, ALIGNMENT_STAT) or not flags & LEADER_FLAGS or is_minion(event):
            return
        tier = stat(event, HERALD_TIER_STAT)
        if tier:
            self.leaders[event['unit_id']] = {'kind': 'herald', 'tier': tier}
        elif flags & SUPER_FLAG:
            data = bytes.fromhex(event['data_hex'][2 * SUPER_ID : 2 * SUPER_ID + 4])
            self.leaders[event['unit_id']] = {'kind': 'super', 'super': int.from_bytes(data, 'little')}
        else:
            self.leaders[event['unit_id']] = {'kind': 'champion' if flags & CHAMPION_FLAG else 'unique'}

    def dropped_by(self, item, area, now) -> dict | None:
        near = [
            (math.hypot(item.x - kill['x'], item.y - kill['y']), kill)
            for kill in self.kills
            if kill['area'] == area and now - kill['t'] <= KILL_SECONDS and kill['x'] is not None
        ]
        distance, kill = min(near, key=lambda pair: pair[0], default=(math.inf, None))
        return kill if distance <= KILL_REACH else None


@dataclass
class Row:
    kills: dict[str, int] = field(default_factory=dict)
    expected: list[float] = field(default_factory=lambda: [0.0] * 5)
    dropped: list[int] = field(default_factory=lambda: [0] * 5)
    unknown: int = 0  # kills the tables have no class for


def summarise(events, model: Model, *, by_level=False) -> dict[tuple, Row]:
    """Kills, the shards they should give and the shards seen, by (act or level, zone), in game order."""
    rows: dict[tuple, dict[str, Row]] = {}
    for event in events:
        if event.get('event') not in ('elite_kill', 'shard') or event.get('area') not in model.levels:
            continue
        act, _, name = model.levels[event['area']]
        zones = rows.setdefault((event['area'], name) if by_level else (act, 0), {})
        row = zones.setdefault(ZONES[event.get('terrorized')], Row())
        if event['event'] == 'shard':
            row.dropped[model.codes.index(event['code'])] += 1
            continue
        row.kills[event['kind']] = row.kills.get(event['kind'], 0) + 1
        found = expected(
            model,
            event['kind'],
            event.get('txt_id'),
            event['area'],
            super_id=event.get('super'),
            tier=event.get('tier'),
            terrorized=bool(event.get('terrorized')),
        )
        if found is None:
            row.unknown += 1
        elif found[1] is not None:
            row.expected = [total + found[0] * share for total, share in zip(row.expected, found[1], strict=True)]
    return {
        (key[1] if by_level else key[0], zone): row
        for key, zones in sorted(rows.items())
        for zone, row in sorted(zones.items())
    }


def report(rows: dict[tuple, Row], model: Model) -> str:
    names = model.names
    head = f'{"where":<28}{"zone":<8}{"kills":>6}' + ''.join(f'{kind[:5]:>7}' for kind in KINDS)
    head += f'{"shards":>8}' + ''.join(f'{name:>12}' for name in names)
    lines = [head + '   (seen / expected)']
    for (where, zone), row in rows.items():
        label = f'Act {where}' if isinstance(where, int) else where
        line = f'{label[:27]:<28}{zone:<8}{sum(row.kills.values()):>6}'
        line += ''.join(f'{row.kills.get(kind, 0):>7}' for kind in KINDS)
        line += f'{sum(row.dropped):>3} /{sum(row.expected):>5.1f}'
        line += ''.join(f'{seen:>5} /{wanted:>5.1f}' for seen, wanted in zip(row.dropped, row.expected, strict=True))
        lines.append(line + (f'   ({row.unknown} kills not in the tables)' if row.unknown else ''))
    return '\n'.join(lines)


def read_events(paths):
    for path in paths:
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                if '"elite_kill"' in line or '"shard"' in line:
                    yield json.loads(line)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('logs', nargs='*', type=Path, help=f'terror-probe.jsonl files (default: {LOGS})')
    parser.add_argument('--levels', action='store_true', help='one row per level instead of per act')
    args = parser.parse_args(argv)
    events = list(read_events(args.logs or sorted(Path().glob(LOGS))))
    if not events:
        print('No elite kills logged yet: they are recorded from the next `serve` run on.')
        return 0
    dates = sorted(event['at'][:10] for event in events if event.get('at'))
    print(f'Hell elite kills and Worldstone Shards seen dropping, {dates[0]} to {dates[-1]}' if dates else '')
    print(report(summarise(events, table(), by_level=args.levels), table()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
