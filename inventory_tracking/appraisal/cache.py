"""Bounded process-local appraisal cache, keyed by decoded facts and KB revision."""

import copy
import hashlib
import json
from collections import OrderedDict


def item_key(frozen, context=None):
    observation = copy.deepcopy(frozen['observation'])
    source = observation.get('source', {})
    # Preserve identity, viewer context and all decoded/raw stats. Only publication
    # metadata varies between otherwise identical captures.
    for field in ('captured_at', 'run_id'):
        source.pop(field, None)
    payload = [observation, frozen.get('identity'), context]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class ResultCache:
    def __init__(self, seconds=300, capacity=128):
        self.seconds, self.capacity = seconds, capacity
        self.entries = OrderedDict()

    def get(self, key, now):
        for expired in [k for k, (until, _) in self.entries.items() if now >= until]:
            del self.entries[expired]
        entry = self.entries.get(key)
        if entry is None:
            return None
        self.entries.move_to_end(key)
        return copy.deepcopy(entry[1])

    def put(self, key, result, now):
        self.entries[key] = (now + self.seconds, copy.deepcopy(result))
        self.entries.move_to_end(key)
        while len(self.entries) > self.capacity:
            self.entries.popitem(last=False)


def database_revision(path):
    revisions: list[tuple[str, int, int, int] | None] = []
    for file in (path, path.with_name(path.name + '-wal')):
        try:
            stat = file.stat()
            revisions.append((str(file.resolve()), stat.st_ino, stat.st_size, stat.st_mtime_ns))
        except FileNotFoundError:
            revisions.append(None)
    return revisions
