"""What the takes show of the hostiles the harm model prices by its conservative stand-in (combat/harm.py `stood_in`:
a boss whose AI is not read, a type with no monstats row): by type, the seconds the character stood within the AI's
radius (sim/casters.py RADIUS, `ai_distance`) of a live one, and the life it lost meanwhile, whoever dealt it (a bound:
the other hostiles' blows are counted too). macros/safety.py STAND_IN_EVIDENCE starts a fight's evidence from these
(rca/2026-10-22/walled-boss-findings.md §2: Radament, 145 s within his radius in three takes, 56 life lost, against
a stand-in price of hundreds a second).

The file data/stand_ins.json is built by `main` from the takes (inventory_tracking/runs/combat); do not edit it by
hand. A type with under POOL_SECONDS of its own takes the pool of all of them (`prior`), as the fit's pooled row is
for a type with no row of its own (combat/sim/monsters.py).

    uv run --offline python -m inventory_tracking.combat.stand_ins
"""

import argparse
import gzip
import json
from collections.abc import Iterator, Sequence
from functools import cache
from pathlib import Path

from inventory_tracking.combat.sim import casters as rules
from inventory_tracking.combat.sim.guard import BOSSES


FILE = Path(__file__).parent / 'data' / 'stand_ins.json'
TAKES = Path(__file__).parents[1] / 'runs' / 'combat'
POOL_SECONDS = 60.0  # seconds of a type's own the takes must hold before its own row prices it (`prior`)
FRAME_MOST = 0.5  # seconds one frame counts at most: a gap is no exposure seen
DEAD_MODES = (0, 12)  # monmode: death, dead


@cache
def table() -> dict:
    """data/stand_ins.json: {'types': {txt: {'seconds', 'lost', 'biggest', 'takes'}}, 'pooled': {...}}; empty with no
    file."""
    if not FILE.exists():
        return {'types': {}, 'pooled': {'seconds': 0.0, 'lost': 0.0, 'biggest': 0.0, 'takes': 0}}
    return json.loads(FILE.read_text(encoding='utf-8'))


def prior(txt: int) -> tuple[float, float]:
    """The takes' (seconds within its radius, life lost then) for type `txt`: its own row with POOL_SECONDS and more,
    else the pool's."""
    found = table()
    row = found['types'].get(str(txt))
    if row is None or row['seconds'] < POOL_SECONDS:
        row = found['pooled']
    return float(row['seconds']), float(row['lost'])


def frames(take: Path) -> Iterator[dict]:
    with gzip.open(take / 'frames.jsonl.gz', 'rt') as lines:
        for line in lines:
            yield json.loads(line)


def scan(take: Path, types: frozenset[int], rows: dict[int, dict]) -> None:
    """Adds one take's exposure to `rows` (txt -> tallies)."""
    before = None
    for frame in frames(take):
        player = frame.get('p')
        if not player or not frame.get('game'):
            before = None
            continue
        clock, here, life = frame['t'], (player[3], player[4]), player[7]
        near = {
            m[1]
            for m in frame.get('m', ())
            if m[1] in types
            and m[2] not in DEAD_MODES
            and m[5] > 0
            and rules.ai_distance(here, (m[3], m[4])) < rules.RADIUS
        }
        if before is not None and near:
            step = min(max(clock - before[0], 0.0), FRAME_MOST)
            lost = max(0.0, before[1] - life) if life > 0 else 0.0
            for txt in near:
                row = rows.setdefault(txt, {'seconds': 0.0, 'lost': 0.0, 'biggest': 0.0, 'takes': set()})
                row['seconds'] += step
                row['lost'] += lost
                row['biggest'] = max(row['biggest'], lost)
                row['takes'].add(take.name)
        before = (clock, life)


def build(takes: Path = TAKES) -> dict:
    from inventory_tracking.combat.harm import stood_in

    types = frozenset(txt for txt in BOSSES if stood_in(txt))
    rows: dict[int, dict] = {}
    for take in sorted(takes.iterdir()):
        units = take / 'units.jsonl.gz'
        if not units.exists() or not (take / 'frames.jsonl.gz').exists():
            continue
        with gzip.open(units, 'rt') as lines:
            if not {json.loads(line)['txt'] for line in lines} & types:
                continue
        scan(take, types, rows)

    def out(row: dict) -> dict:
        return {
            'seconds': round(row['seconds'], 1),
            'lost': round(row['lost'], 1),
            'biggest': round(row['biggest'], 1),
            'takes': len(row['takes']) if isinstance(row['takes'], set) else row['takes'],
        }

    pooled = {
        'seconds': sum(r['seconds'] for r in rows.values()),
        'lost': sum(r['lost'] for r in rows.values()),
        'biggest': max((r['biggest'] for r in rows.values()), default=0.0),
        'takes': len(set().union(*(r['takes'] for r in rows.values()))) if rows else 0,
    }
    return {
        'about': (
            'built by inventory_tracking/combat/stand_ins.py from the takes: seconds the character stood within '
            "the AI radius of a live stand-in hostile, by type, and the life lost meanwhile (any hostile's). "
            'Do not edit by hand.'
        ),
        'types': {str(txt): out(rows[txt]) for txt in sorted(rows)},
        'pooled': out(pooled),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--takes', type=Path, default=TAKES)
    args = parser.parse_args(argv)
    found = build(args.takes)
    FILE.write_text(json.dumps(found, indent=1) + '\n', encoding='utf-8')
    table.cache_clear()
    for txt, row in found['types'].items():
        print(txt, row)
    print('pooled', found['pooled'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
