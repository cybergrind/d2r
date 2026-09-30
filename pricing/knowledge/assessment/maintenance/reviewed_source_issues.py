"""Pinned manual source-conflict reviews; changed evidence reopens review."""

import hashlib
import json
from copy import deepcopy

from pricing.knowledge.builds import decode_planner


def _snapshot(reference, root):
    raw = (root / reference['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference['sha256']:
        return False
    if 'locator' in reference:
        value = json.loads(raw)
        if reference.get('format') == 'maxroll_planner':
            value = decode_planner(value)
        elif reference.get('format', 'json') != 'json':
            return False
        for part in reference['locator'].split('/')[1:]:
            part = part.replace('~1', '/').replace('~0', '~')
            value = value[int(part)] if isinstance(value, list) else value[part]
        return value == reference['expected']
    return True


def reviewed_source_issues(reviews, root):
    results = []
    for original in sorted(reviews, key=lambda row: row['id']):
        row = deepcopy(original)
        stale = []
        resolution = row.get('resolution')
        evidence = resolution.get('evidence', []) if resolution is not None else []
        if resolution is not None and not evidence:
            stale.append(row['source']['path'])
        for reference in [row['source'], *row['mechanics'], *evidence]:
            try:
                valid = _snapshot(reference, root)
            except OSError, ValueError, KeyError, TypeError, IndexError:
                valid = False
            if not valid:
                stale.append(reference['path'])
        row['status'] = 'stale_review' if stale else 'reconciled_source' if resolution else 'reviewed_conflict'
        row['stale_sources'] = sorted(set(stale))
        results.append(row)
    return results
