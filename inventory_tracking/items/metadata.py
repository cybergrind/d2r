"""Offline item metadata and stat output assembly; unknowns remain explicit."""

import hashlib
import json
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

from inventory_tracking.items.poison import combine_poison
from inventory_tracking.items.stat_constants import TOTAL_STATS_DESCRIPTOR_OFFSET
from inventory_tracking.items.stats import StatContext, decode_stat, derived_base_stats


@cache
def _default_metadata():
    raw = (Path(__file__).parent / 'data/item_metadata.json').read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


_PINNED_METADATA = ContextVar('item_metadata_snapshot', default=None)


def metadata():
    return (_PINNED_METADATA.get() or _default_metadata())[0]


metadata.cache_clear = _default_metadata.cache_clear


def metadata_generation():
    return (_PINNED_METADATA.get() or _default_metadata())[1]


@lru_cache(maxsize=2)
def _published_metadata(raw):
    value = json.loads(raw)
    if not all(isinstance(value.get(key), dict) for key in ('bases', 'stats', 'skills')):
        raise ValueError('Invalid published item metadata')
    return value, hashlib.sha256(raw).hexdigest()


@contextmanager
def metadata_snapshot(raw):
    current = _published_metadata(raw)
    token = _PINNED_METADATA.set(current)
    try:
        yield current[0]
    finally:
        _PINNED_METADATA.reset(token)


def item_base(class_id):
    return metadata()['bases'].get(str(class_id))


def unresolved_row(stat, spec):
    name = ' / '.join(spec.get('ambiguous_names', [spec['name']])) if spec else f'Unknown stat {stat["id"]}'
    return {
        'memory_stat': stat,
        'status': 'unresolved',
        'name': name,
        'text': (f'{name.replace("_", " ")}: raw {stat["raw"]}, parameter {stat["layer"]} (interpretation unresolved)'),
    }


def market_facet(stat, spec, fields):
    """Only scalar strategies return labels eligible for market projection."""
    if not fields.get('label') or not spec.get('property_id'):
        return None
    return {
        'property_id': spec['property_id'],
        'value': fields['value'],
        'label': fields['label'],
        'memory_stat': stat,
        'descriptor_offset': TOTAL_STATS_DESCRIPTOR_OFFSET,
    }


def unambiguous_facets(affixes):
    # Never let downstream dictionary construction silently replace a facet.
    properties = Counter(a['property_id'] for a in affixes)
    return [a for a in affixes if properties[a['property_id']] == 1]


def decode_stats(
    stats, *, base=None, viewer_level=None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep every entry, separating readable values from market search facets."""
    catalog = metadata()
    counts = Counter((s['id'], s['layer']) for s in stats)
    decoded, affixes, unresolved = [], [], []
    for stat in stats:
        spec = catalog['stats'].get(str(stat['id']), {})
        row = unresolved_row(stat, spec)
        if type(stat['raw']) is int and counts[stat['id'], stat['layer']] == 1:
            fields = decode_stat(StatContext(stat, spec, catalog['skills'], base, viewer_level))
            if fields is not None:
                row.update(fields, status='decoded')
                if facet := market_facet(stat, spec, fields):
                    affixes.append(facet)
        if row['status'] == 'unresolved':
            unresolved.append(stat)
        decoded.append(row)
    decoded = combine_poison(decoded)
    unresolved = [r['memory_stat'] for r in decoded if r['status'] == 'unresolved']
    decoded, damage_facet = combine_enhanced_damage(decoded)
    if damage_facet:
        affixes.append(damage_facet)
    decoded.extend(derived_base_stats(base))
    return decoded, unambiguous_facets(affixes), unresolved


def combine_enhanced_damage(decoded):
    """One visible bonus when both captured damage components agree exactly."""
    components = [r for r in decoded if r.get('memory_stat', {}).get('id') in (17, 18)]
    if (
        len(components) != 2
        or {r['memory_stat']['id'] for r in components} != {17, 18}
        or any(r['status'] != 'decoded' or r['memory_stat']['layer'] != 0 for r in components)
        or components[0]['value'] != components[1]['value']
    ):
        return decoded, None
    value = components[0]['value']
    raw = [r['memory_stat'] for r in components]
    label = '+{{value}}% Enhanced Damage'
    combined = {
        'status': 'decoded',
        'name': 'item_damage_percent',
        'value': value,
        'label': label,
        'text': f'+{value}% Enhanced Damage',
        'memory_stats': raw,
    }
    result = []
    inserted = False
    for row in decoded:
        if row in components:
            if not inserted:
                result.append(combined)
                inserted = True
        else:
            result.append(row)
    # Verified local appraisal-properties.json: enhanced damage is property510.
    facet = {
        'property_id': '510',
        'value': value,
        'label': label,
        'memory_stats': raw,
        'descriptor_offset': TOTAL_STATS_DESCRIPTOR_OFFSET,
    }
    return result, facet
