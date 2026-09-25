"""Base generation tier from the offline native upgrade-chain catalog."""

import json
from functools import lru_cache
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact


CATALOG = Path(__file__).resolve().parents[3] / 'data/appraisal-catalog.json'
FIELDS = {'normal_code': 'Normal', 'exceptional_code': 'Exceptional', 'elite_code': 'Elite'}


@lru_cache(maxsize=2)
def _tiers(raw):
    document = json.loads(raw)
    if document.get('schema_version') != 1:
        raise ValueError('Unsupported base catalog schema')
    candidates = {}
    for row in document['rows']:
        code = row.get('base_code')
        if not code:
            continue
        matched = {label for field, label in FIELDS.items() if row.get('details', {}).get(field) == code}
        candidates.setdefault(code, set()).update(matched)
    return {code: next(iter(values)) for code, values in candidates.items() if len(values) == 1}


def base_tier(code):
    try:
        return _tiers(read_artifact(CATALOG)).get(code)
    except OSError, ValueError, TypeError, KeyError:
        return None


@lru_cache(maxsize=2)
def _chains(raw):
    document = json.loads(raw)
    if document.get('schema_version') != 1:
        raise ValueError('Unsupported base catalog schema')
    candidates = {}
    for row in document['rows']:
        code = row.get('base_code')
        chain = tuple(row.get('details', {}).get(field) for field in FIELDS)
        if code and all(isinstance(c, str) and c for c in chain) and len(set(chain)) == 3 and code in chain:
            candidates.setdefault(code, set()).add(chain)
    return {code: next(iter(chains)) for code, chains in candidates.items() if len(chains) == 1}


def is_base_upgrade(original, target):
    """Both catalog rows must agree on one chain and the target must be later."""
    try:
        chains = _chains(read_artifact(CATALOG))
        chain = chains.get(original)
        return bool(chain and chains.get(target) == chain and chain.index(target) > chain.index(original))
    except OSError, ValueError, TypeError, KeyError:
        return False


def base_at_tier(original, tier):
    """Resolve an explicit same-or-higher tier without assuming an upgrade."""
    if tier not in FIELDS.values():
        return None
    if base_tier(original) == tier:
        return original
    try:
        chains = _chains(read_artifact(CATALOG))
        chain = chains.get(original)
        if chain is None:
            return None
        target = chain[tuple(FIELDS.values()).index(tier)]
        return target if chains.get(target) == chain and chain.index(target) > chain.index(original) else None
    except OSError, ValueError, TypeError, KeyError:
        return None
