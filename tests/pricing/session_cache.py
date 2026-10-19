"""Session caches for the pricing tests' expensive, deterministic builds (cleanup phase 2, 2026-10-19).

`memoize` wraps a production function for the test session only (tests/pricing/conftest.py installs it).
An entry records every file the call opened (an `open` audit hook) and serves a hit only while each of
those files, and the directory holding it, keeps its mtime and size: an edited or regenerated input, or
a file added beside one, recomputes. A hit returns a fresh unpickled copy, so a test may mutate what it
gets; `copy=False` shares the stored result, only for deeply frozen results.
"""

import os
import pickle
import sys
from functools import wraps


_recording: list[set[str]] = []  # read sets of the cached calls now computing, innermost last


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CODE = ('.py', '.pyc', '.so')  # imports during a call are code, not inputs
VENV = os.sep + '.venv' + os.sep


def _audit(event, args):
    if event == 'open' and _recording and isinstance(args[0], (str, bytes, os.PathLike)):
        path = os.path.abspath(os.fsdecode(args[0]))
        if (
            path.startswith(ROOT + os.sep)
            and not path.endswith(CODE)
            and '__pycache__' not in path
            and VENV not in path
        ):
            for reads in _recording:
                reads.add(path)


sys.addaudithook(_audit)


def _stamp(paths):
    def one(path):
        try:
            status = os.stat(path)
        except OSError:
            return None
        return status.st_mtime_ns, status.st_size

    watched = sorted(set(paths) | {os.path.dirname(path) for path in paths})
    return tuple((path, one(path)) for path in watched)


def memoize(function, key, *, copy=True):
    """`key(*args, **kwargs)` names the entry; None bypasses the cache (another root, a patched input)."""
    entries = {}

    @wraps(function)
    def cached(*args, **kwargs):
        name = key(*args, **kwargs)
        if name is None:
            return function(*args, **kwargs)
        entry = entries.get(name)
        if entry is not None and _stamp(entry[0]) == entry[1]:
            for reads in _recording:  # an enclosing cached call depends on these files too
                reads.update(entry[0])
            return pickle.loads(entry[2]) if copy else entry[2]
        reads: set[str] = set()
        _recording.append(reads)
        try:
            result = function(*args, **kwargs)
        finally:
            _recording.remove(reads)
        for outer in _recording:
            outer.update(reads)
        entries[name] = (reads, _stamp(reads), pickle.dumps(result, protocol=5) if copy else result)
        return result

    return cached
