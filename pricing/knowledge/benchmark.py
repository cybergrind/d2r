"""Offline retrieval benchmark; fresh CLI processes and separately instrumented phases.

Run: uv run --offline python -m pricing.knowledge.benchmark --output PATH
The first observation is not a cold-disk measurement: OS caches are not flushed.
"""

import argparse
import hashlib
import json
import math
import platform
import sqlite3
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pricing.knowledge import index, retrieval


ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = {
    'sorceress_leveling_search': ['search', '', '--kind', 'leveling', '--class', 'sorceress'],
    'bloodfist_lookup': ['lookup', 'Bloodfist'],
    'grand_charm_lookup': ['lookup', 'Grand Charm'],
    'unknown_lookup': ['lookup', 'Unknown benchmark identity xyz'],
    'crystal_sword_sockets': ['sockets', 'Crystal Sword', '--method', 'larzuk', '--ilvl', '28'],
}


def summary(values):
    """Nearest-rank p95, interpolated median; values retain their input units."""
    values = sorted(values)
    return {
        'samples': len(values),
        'p50': statistics.median(values),
        'p95': values[math.ceil(len(values) * 0.95) - 1],
        'min': values[0],
        'max': values[-1],
    }


def timed_call(timings, key, callback, *args, **kwargs):
    start = time.perf_counter_ns()
    try:
        return callback(*args, **kwargs)
    finally:
        timings[key] += (time.perf_counter_ns() - start) / 1_000_000


class TimedCursor:
    def __init__(self, cursor, timings):
        self.cursor, self.timings = cursor, timings

    def __iter__(self):
        return self

    def __next__(self):
        return timed_call(self.timings, 'sqlite_fetch_ms', next, self.cursor)

    def fetchone(self):
        return timed_call(self.timings, 'sqlite_fetch_ms', self.cursor.fetchone)

    def fetchall(self):
        return timed_call(self.timings, 'sqlite_fetch_ms', self.cursor.fetchall)


class TimedConnection:
    def __init__(self, connection, timings, statements):
        self.connection, self.timings, self.statements = connection, timings, statements

    def execute(self, sql, parameters=()):
        self.statements.append((sql, parameters))
        cursor = timed_call(self.timings, 'sqlite_execute_ms', self.connection.execute, sql, parameters)
        return TimedCursor(cursor, self.timings)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.connection.close()


def phase_sample(database, scenario):
    """Instrument actual index code without changing production SQL or logic."""
    timings, statements = defaultdict(float), []
    connect = index._connect

    def measured_connect(path):
        connection = timed_call(timings, 'connect_schema_check_ms', connect, path)
        return TimedConnection(connection, timings, statements)

    def measured_loads(value):
        return timed_call(timings, 'json_decode_ms', json.loads, value)

    present = retrieval._present

    def measured_present(*args, **kwargs):
        return timed_call(timings, 'compact_projection_ms', present, *args, **kwargs)

    with (
        patch.object(index, '_connect', measured_connect),
        patch.object(retrieval, 'json', SimpleNamespace(loads=measured_loads, dumps=json.dumps)),
        patch.object(retrieval, '_present', measured_present),
        patch.object(index, 'json', SimpleNamespace(loads=measured_loads)),
    ):
        if scenario[0] == 'recommend':
            result = retrieval.recommend(database, class_name='sorc', quality='unique,set', max_level=25)
        elif scenario[0] == 'search':
            result = index.search(database, '', kind='leveling', **{'class': 'sorceress'})
        elif scenario[0] == 'lookup':
            result = index.lookup(database, scenario[1], limit=2)
        elif scenario[0] == 'sockets':
            from pricing.knowledge.utility import socket_options_from_row

            rows = index.lookup(database, 'Crystal Sword', limit=1000)['evidence'].get('base_rule', [])
            row = next(row for row in rows if row.get('details', {}).get('rule') == 'socket_potential')
            result = {
                'name': 'Crystal Sword',
                **socket_options_from_row(row, method='larzuk', ilvl=28, quality='normal', current_sockets=0),
                'source': row.get('source'),
                'offline': True,
            }
        else:
            return None
    if scenario[0] in ('search', 'lookup'):
        result = timed_call(timings, 'compact_projection_ms', index.compact_result, result)
    timed_call(
        timings,
        'serialization_ms',
        json.dumps,
        result,
        ensure_ascii=False,
        indent=2 if scenario[0] == 'sockets' else None,
    )
    timings['database_execute_fetch_ms'] = timings['sqlite_execute_ms'] + timings['sqlite_fetch_ms']
    return dict(timings), statements


def observe_cli(database, arguments):
    command = ['uv', 'run', '--offline', 'python', '-m', 'pricing.knowledge', '--database', str(database), *arguments]
    start = time.perf_counter_ns()
    result = subprocess.run(command, cwd=ROOT, capture_output=True, check=True)
    elapsed = (time.perf_counter_ns() - start) / 1_000_000
    parsed = json.loads(result.stdout)
    return {'wall_ms': elapsed, 'output_bytes': len(result.stdout), 'result_type': type(parsed).__name__}


def benchmark(database, samples, include_recommend=False):
    scenarios = dict(SCENARIOS)
    if include_recommend:
        scenarios['sorceress_recommend'] = [
            'recommend',
            '--class',
            'sorc',
            '--quality',
            'unique,set',
            '--max-level',
            '25',
        ]
    result = {
        'measured_at': datetime.now(UTC).isoformat(),
        'methodology': {
            'offline': True,
            'cli': 'uv run --offline; sequential fresh subprocesses; wall includes uv startup and output capture',
            'cache': 'First sample reported separately; warm OS caches expected; no cold disk claim or cache flush.',
            'phases': 'Separate in-process runs; instrumented nonoverlapping phases, not full wall time.',
            'percentiles': 'Median p50; nearest-rank p95; milliseconds.',
            'network': 'Only local read operations; no refresh command invoked.',
        },
        'environment': {'python': sys.version, 'platform': platform.platform(), 'sqlite': sqlite3.sqlite_version},
        'database': {'path': str(database), 'bytes': database.stat().st_size, 'build': index.index_status(database)},
        'code_sha256': {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                Path(__file__),
                ROOT / 'pricing/knowledge/index.py',
                ROOT / 'pricing/knowledge/__main__.py',
                ROOT / 'pricing/knowledge/retrieval.py',
            )
        },
        'scenarios': {},
    }
    for name, arguments in scenarios.items():
        first = observe_cli(database, arguments)
        observations = [observe_cli(database, arguments) for _ in range(samples)]
        phases, statements = defaultdict(list), []
        for _ in range(samples):
            observed = phase_sample(database, arguments)
            if observed:
                timings, statements = observed
                for key, value in timings.items():
                    phases[key].append(value)
        plans = []
        with sqlite3.connect(f'{database.resolve().as_uri()}?mode=ro', uri=True) as connection:
            for sql, parameters in dict.fromkeys((sql, tuple(params)) for sql, params in statements):
                plans.append(
                    {
                        'sql': sql,
                        'parameters': parameters,
                        'plan': connection.execute('EXPLAIN QUERY PLAN ' + sql, parameters).fetchall(),
                    }
                )
        result['scenarios'][name] = {
            'arguments': arguments,
            'first_observation': first,
            'warm_cli_wall_ms': summary([row['wall_ms'] for row in observations]),
            'warm_output_bytes': summary([row['output_bytes'] for row in observations]),
            'in_process_phases': {key: summary(values) for key, values in phases.items()},
            'actual_sql_plans': plans,
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=ROOT / 'pricing/data/appraisal.sqlite3')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=30)
    parser.add_argument('--include-recommend', action='store_true')
    args = parser.parse_args()
    if args.samples < 1:
        parser.error('--samples must be positive')
    result = benchmark(args.database, args.samples, args.include_recommend)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(args.output)


if __name__ == '__main__':
    main()
