"""Equipment conditions that paid-property models must not pool."""

from functools import lru_cache

from inventory_tracking.items.metadata import metadata, metadata_generation
from pricing.knowledge.artifacts import artifact_snapshot
from pricing.knowledge.assessment.mechanics.base_tiers import CATALOG, base_tier


FIELDS = ('ethereal', 'sockets', 'socket_contents', 'base_tier')


@lru_cache(maxsize=2)
def base_conditions(generation, revision):
    bases = metadata()['bases'].values()
    with artifact_snapshot([CATALOG]):
        rows = {b['code']: (b, 'not_applicable' if b['category'] == 'misc' else base_tier(b['code'])) for b in bases}
    return rows, {b['name'].casefold(): code for code, (b, _) in rows.items()}


def conditions(item):
    """Unknown facets cannot borrow a known equipment variant's model."""
    if type(item.get('ethereal')) is not bool or type(item.get('sockets')) is not int:
        return None
    if not 0 <= item['sockets'] <= 6 or item.get('socket_contents') not in ('empty', 'filled'):
        return None
    stat = CATALOG.stat()
    bases, names = base_conditions(metadata_generation(), (stat.st_mtime_ns, stat.st_size))
    code = item.get('base_code') or names.get(str(item.get('base_name') or item.get('name', '')).casefold())
    base, tier = bases.get(code, ({}, None))
    if tier is None or item.get('base_name') not in (None, base['name']):
        return None
    return {**{key: item[key] for key in FIELDS[:3]}, 'base_tier': tier}


def group_key(item):
    facets = conditions(item)
    if facets is None:
        return None
    return item['category'], item.get('family'), *(facets[key] for key in FIELDS)
