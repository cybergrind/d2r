"""Resolve listing bases only when required level rules out all other tiers.

ITEMS_GetRequiredLevel takes the maximum of base/named requirements before
positive upgrade/socket adjustments. These bounds can exclude a base, never
prove an upgrade from a high requirement. Explicit tier/upgrade fields win.
"""

import json
from functools import lru_cache

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.mechanics.base_tiers import CATALOG, base_at_tier, base_tier


@lru_cache(maxsize=2)
def base_levels(raw):
    candidates = {}
    for row in json.loads(raw)['rows']:
        if code := row.get('base_code'):
            candidates.setdefault(code, set()).add(row.get('details', {}).get('required_level'))
    return {code: next(iter(values)) for code, values in candidates.items() if len(values) == 1}


def resolve(row, variants):
    properties = row.get('properties', {})
    level = properties.get('796')
    if (
        row.get('base_code') is not None
        or '930' in properties
        or '1216' in properties
        or type(level) is not int
        or not 1 <= level <= 99
        or not variants
    ):
        return None
    levels = base_levels(read_artifact(CATALOG))
    possible = set()
    for variant in variants:
        named = variant.get('game_definition', {}).get('lvl req')
        originals = variant.get('base_codes', ())
        if type(named) is not int or not originals:
            return None
        for original in originals:
            tiers = ('Normal', 'Exceptional', 'Elite')
            native_tier = base_tier(original)
            if native_tier not in tiers:
                return None
            for tier in tiers[tiers.index(native_tier) :]:
                code = base_at_tier(original, tier)
                if code is None:
                    return None
                minimum = levels.get(code)
                if type(minimum) is not int:
                    return None
                if level >= max(named, minimum):
                    possible.add(code)
    return next(iter(possible)) if len(possible) == 1 else None
