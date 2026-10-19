"""All takes read once each: a take's blows (blows.py) and tallies (rates.py), cached per take, and the
split of the takes into the half the refit is fitted on and the half it is judged on.

A take is loaded, walked and dropped in a worker process; what it leaves is a JSON file in the cache
(not in the repo), named by the take and a stamp of this package's code and the take's manifest, so a
change to either reads the take again and nothing else does. The enchantments of takes from before
2026-10-11 22:23 UTC come from the terror probe logs (takes/hurts.py `sightings`), read once and
cached as well: the logs are 264 MB.
"""

import hashlib
import json
import os
import pickle
import sys
import time
from collections.abc import Iterable, Sequence
from multiprocessing import get_context
from pathlib import Path
from typing import Any

from inventory_tracking.takes.hurts import Sightings, enchantments, sightings
from inventory_tracking.takes.takes import Take
from tests.inventory_tracking.scenarios.arena.cut import level_of
from tests.inventory_tracking.scenarios.arena.evidence import blows, rates


HERE = Path(__file__).parent
REPO = HERE.parents[4]
ROOT = REPO / 'inventory_tracking' / 'runs' / 'combat'
PROBES = REPO / 'inventory_tracking' / 'runs' / 'alt-d'
# The session's scratch directory: per-take results and the raw rows, never in the repo.
SCRATCH = Path('/tmp/claude-1000/-mnt-extra-1000-games-d2r/cd88df62-ceab-4824-82a5-1fbc5fbad0c8/scratchpad')
CACHE = SCRATCH / 'evidence-cache'
TRAIN, CHECK = 'train', 'check'
SPLIT_RULE = 'the first byte of sha1(take name): even is train, odd is check'
_SEEN: Sightings = {}  # the probe logs' sightings, set in the parent before the workers fork


def half(name: str) -> str:
    """Which half a take is in, by its name alone: the same on every run and every host."""
    return TRAIN if hashlib.sha1(name.encode()).digest()[0] % 2 == 0 else CHECK


def stamp() -> str:
    """A hash of the code that makes a take's cache file: blows.py, rates.py and this file."""
    digest = hashlib.sha1()
    for name in ('blows.py', 'rates.py', 'scan.py'):
        digest.update((HERE / name).read_bytes())
    return digest.hexdigest()[:12]


def takes_under(root: Path, since: str | None = None, limit: int | None = None) -> list[Path]:
    """The take directories under `root` (those with a manifest), by name; `since` (YYYYMMDD) leaves out
    earlier ones (a take is named by its start), `limit` keeps the last so many."""
    found = sorted(path.parent for path in root.glob('*/manifest.json'))
    if since:
        found = [path for path in found if path.name[:8] >= since]
    return found[-limit:] if limit else found


def read(directory: Path, seen: Sightings) -> dict[str, Any]:
    """One take's part of the evidence: its blows and its tallies; `skipped` says why there are none."""
    name = directory.name
    try:
        take = Take.load(directory)
    except (OSError, ValueError) as exc:
        return {'take': name, 'skipped': f'not read ({exc})'}
    if take.schema < 2:
        return {'take': name, 'skipped': 'schema 1: no vitals'}
    if not take.frames:
        return {'take': name, 'skipped': 'no frames'}
    mods = enchantments(seen, take)
    moments = list(blows.walk(take))
    rows = blows.blows(take, mods, moments)
    roster = blows.Roster(take, mods)
    found = rates.tally(name, moments, rows, roster, level_of(take))
    found['mods_known'] = sum(roster.mods(unit) is not None for unit in roster.units)
    found['units'] = len(roster.units)
    return {'take': name, 'rows': rows, 'tally': found}


def cached(directory: Path, cache: Path | None, mark: str) -> dict[str, Any]:
    if cache is None:
        return read(directory, _SEEN)
    manifest = directory / 'manifest.json'
    changed = int(manifest.stat().st_mtime) if manifest.exists() else 0
    path = cache / f'{directory.name}.{mark}.{changed}.json'
    if path.exists():
        return json.loads(path.read_text())
    found = read(directory, _SEEN)
    for old in cache.glob(f'{directory.name}.*.json'):
        old.unlink()
    path.write_text(json.dumps(found, separators=(',', ':')))
    return found


def _work(job: tuple[Path, Path | None, str]) -> dict[str, Any]:
    return cached(*job)


def probe_sightings(logs: Sequence[Path], cache: Path | None) -> Sightings:
    """hurts.sightings over the logs, kept in the cache under the logs' sizes and times."""
    if not logs:
        return {}
    if cache is None:
        return sightings(logs)
    digest = hashlib.sha1()
    for log in logs:
        found = log.stat()
        digest.update(f'{log}:{found.st_size}:{int(found.st_mtime)}'.encode())
    path = cache / f'sightings.{digest.hexdigest()[:12]}.pickle'
    if path.exists():
        return pickle.loads(path.read_bytes())
    seen = sightings(logs)
    path.write_bytes(pickle.dumps(seen))
    return seen


def scan(
    directories: Sequence[Path],
    *,
    cache: Path | None = CACHE,
    probes: Iterable[Path] | None = None,
    jobs: int | None = None,
    progress: bool = True,
) -> list[dict[str, Any]]:
    """`read` of every take, from the cache where it holds one, in `jobs` processes."""
    global _SEEN  # the workers inherit it by fork instead of each reading 264 MB of logs
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
    logs = sorted(PROBES.glob('*/terror-probe.jsonl')) if probes is None else sorted(probes)
    began = time.monotonic()
    _SEEN = probe_sightings(logs, cache)
    if progress:
        print(f'{len(logs)} probe logs: {len(_SEEN)} units in {time.monotonic() - began:.0f} s', file=sys.stderr)
    mark = stamp()
    work = [(directory, cache, mark) for directory in directories]
    jobs = jobs or min(os.cpu_count() or 1, 16)
    found = []
    if jobs <= 1 or len(work) <= 1:
        results: Iterable[dict[str, Any]] = map(_work, work)
        pool = None
    else:
        pool = get_context('fork').Pool(jobs)
        results = pool.imap(_work, work, chunksize=2)
    for done, result in enumerate(results, 1):
        found.append(result)
        if progress and (done % 50 == 0 or done == len(work)):
            print(f'{done}/{len(work)} takes, {time.monotonic() - began:.0f} s', file=sys.stderr)
    if pool is not None:
        pool.close()
        pool.join()
    return found
