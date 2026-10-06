"""Recognize reported affixes without inventing a missing rarity or sale price."""

from functools import lru_cache

from inventory_tracking.items.metadata import metadata, metadata_generation


@lru_cache(maxsize=2)
def affix_ranges(generation, *, inherent=False):
    from pricing.knowledge.assessment.adapters.market_projection import market_properties

    game = metadata()
    projection = {
        f'{key}:0': str(stat['property_id']) for key, stat in game['stats'].items() if stat.get('property_id')
    }
    projection.update(market_properties())
    result = {}
    for table in ('auto',) if inherent else ('prefix', 'suffix'):
        for affix in game['affixes'][table].values():
            if not inherent and not affix.get('spawnable'):
                continue
            for key, spec in affix.get('roll_ranges', {}).items():
                native = key if ':' in key else key + ':0'
                prop = projection.get(native)
                if prop is None:
                    continue
                for code in affix.get('base_codes', []):
                    result.setdefault(code, {}).setdefault(str(prop), []).append((spec['min'], spec['max']))
    return result


def proven(row, base):
    from pricing.triage.adapters import BASE_CONTEXT
    from pricing.triage.market_bases import native_staffmods

    if row.get('category') != 'base' or row.get('rarity') is not None or not base:
        return False
    # With potential or unknown inserts these stats could belong to gems or a
    # completed word. Zero capacity is native evidence even if sockets are omitted.
    if base.get('max_sockets') != 0 and row.get('sockets') != 0:
        return False
    if row.get('socket_contents') == 'filled':
        return False
    excluded = BASE_CONTEXT | {'399', '551', '446', '538', '937', '423'}
    excluded |= native_staffmods(metadata_generation()).get(base['type'], {}).keys()
    excluded |= affix_ranges(metadata_generation(), inherent=True).get(base['code'], {}).keys()
    if base['type'] == 'ashd':
        excluded |= {'441', '401', '426', '427', '428', '510'}
    if base['type'] in ('abow', 'ajav', 'aspe'):
        excluded |= {'454', '456'}
    ranges = affix_ranges(metadata_generation()).get(base['code'], {})
    for prop, value in row.get('properties', {}).items():
        if type(value) not in (int, float) or value <= 0:
            continue
        enhanced = prop == ('425' if base['category'] == 'armor' else '510') and value > 15
        if prop in excluded and not enhanced:
            continue
        if any(low <= value <= high for low, high in ranges.get(prop, [])):
            return True
    return False


def review_pattern(item, tables):
    from pricing.triage.adapters import AFFIXED
    from pricing.triage.patterns import check_reason, matched_patterns
    from pricing.triage.rule_index import candidates

    for category in sorted(AFFIXED):
        candidate = item | {'category': category}
        rows = candidates(candidate, tables['pattern_index']) if 'pattern_index' in tables else tables['rules']['rows']
        patterns = matched_patterns(candidate, rows)
        if patterns:
            return min((check_reason(candidate, pattern) for pattern in patterns), key=len)
    return None
