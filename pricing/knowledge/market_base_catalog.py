"""Exact equipment catalog identities for ordinary base/affixed market listings."""

import hashlib
import json
from functools import lru_cache

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.domain.facts import freeze
from pricing.knowledge.assessment.mechanics.base_tiers import CATALOG
from pricing.knowledge.names import normalize_name


@lru_cache(maxsize=2)
def equipment_index(raw):
    document = json.loads(raw)
    if document.get('schema_version') != 1:
        raise ValueError('Unsupported equipment catalog')
    candidates = {}
    for row in document['rows']:
        if row.get('source_id') not in ('d2data-armor', 'd2data-weapons') or not row.get('base_code'):
            continue
        candidates.setdefault(normalize_name(row['name']), []).append(row)
    # Duplicates with differing mechanics are ambiguous, even if codes match.
    index = freeze({name: rows[0] for name, rows in candidates.items() if all(row == rows[0] for row in rows)})
    return index, hashlib.sha256(raw).hexdigest()


def equipment_base(name):
    try:
        raw = read_artifact(CATALOG)
        index, generation = equipment_index(raw)
        row = index.get(normalize_name(name))
        if row is None:
            return None
        return row, {
            'kind': 'equipment_catalog',
            'path': str(CATALOG),
            'sha256': generation,
        }
    except OSError, ValueError, KeyError, TypeError:
        return None
