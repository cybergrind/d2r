"""The combat gate over every take, one take at a time, a take that cannot be cut named instead of ending the run."""

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from inventory_tracking.builds.warlock.echoing_strike.scoreboard import LEAST_CASTS, lines, row, totals
from inventory_tracking.builds.warlock.echoing_strike.sim.situation import cut
from inventory_tracking.takes.takes import Take


def one(path: Path):
    try:
        situation = cut(Take.load(path))
        if len(situation.casts) < LEAST_CASTS:
            return path.name, {'skipped': f'{len(situation.casts)} full casts'}
        return path.name, {'side': 'n/a', **row(situation, policies=True)}
    except Exception as failure:
        return path.name, {'skipped': f'not cut: {type(failure).__name__}: {failure}'[:160]}


if __name__ == '__main__':
    root = Path(sys.argv[1])
    paths = sorted(p for p in root.iterdir() if (p / 'frames.jsonl').exists() or (p / 'frames.jsonl.gz').exists())
    with ProcessPoolExecutor(max_workers=8) as pool:
        rows = dict(pool.map(one, paths, chunksize=4))
    board = {'takes': rows, 'totals': totals(rows), 'changes': []}
    print('\n'.join(lines(board)))
