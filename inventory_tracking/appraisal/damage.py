"""Pair damage endpoints for display without changing native facts or market facets."""

DAMAGE_PAIRS = (
    (21, 22, 'One-Hand Damage: {lo}-{hi}'),
    (23, 24, 'Two-Hand Damage: {lo}-{hi}'),
    (159, 160, 'Throw Damage: {lo}-{hi}'),
    (48, 49, 'Adds {lo}-{hi} Fire Damage'),
    (50, 51, 'Adds {lo}-{hi} Lightning Damage'),
    (52, 53, 'Adds {lo}-{hi} Magic Damage'),
    (54, 55, 'Adds {lo}-{hi} Cold Damage'),
)


def endpoint(row):
    text = f'{row["value"]:g}'
    bounds = row.get('roll_quality_range') or row.get('roll_range')
    if bounds:
        text += f' ({bounds["min"]}-{bounds["max"]})'
    if row.get('roll_tier'):
        text += f' [T{row["roll_tier"]}]'
    return text


def per_level_maximum(rows):
    """Native218 adds floor(coefficient * level / 8) to physical maxima.

    Verified itemstatcost218 op4/param3 targets maxdamage, secondary_maxdamage
    and item_throw_maxdamage. Keep malformed or duplicated evidence uncombined.
    """
    candidates = [row for row in rows if row.get('memory_stat', {}).get('id') == 218]
    if len(candidates) != 1:
        return 0
    row = candidates[0]
    native = row['memory_stat']
    raw, level, value = native.get('raw'), row.get('viewer_level'), row.get('value')
    if (
        row.get('status') != 'decoded'
        or row.get('origin') != 'level_formula'
        or native.get('layer') != 0
        or type(raw) is not int
        or raw < 0
        or type(level) is not int
        or not 1 <= level <= 99
        or type(value) is not int
        or row.get('per_level') != {'numerator': raw, 'denominator': 8}
        or value != raw * level // 8
    ):
        return 0
    return value


def armor_damage(rows):
    """Collapse only complete, equal native armor bonus representations."""
    groups = []
    for stats, label in (((21, 23, 159), 'Minimum'), ((22, 24, 160), 'Maximum')):
        matches = [
            [(i, row) for i, row in enumerate(rows) if row.get('memory_stat', {}).get('id') == stat] for stat in stats
        ]
        if any(len(match) != 1 for match in matches):
            continue
        entries = [match[0] for match in matches]
        expected = entries[0][1].get('value')
        if type(expected) is not int or any(
            row.get('status') != 'decoded'
            or row['memory_stat'].get('layer') != 0
            or type(row['memory_stat'].get('raw')) is not int
            or row['memory_stat']['raw'] != expected
            or type(row.get('value')) is not int
            or row['value'] != expected
            for _, row in entries
        ):
            continue
        groups.append((entries, label))
    replacements, consumed = {}, set()
    if len(groups) == 2 and groups[0][0][0][1]['value'] <= groups[1][0][0][1]['value']:
        lo, hi = groups[0][0][0][1], groups[1][0][0][1]
        entries = [entry for group, _ in groups for entry in group]
        first = min(i for i, _ in entries)
        replacements[first] = {'status': 'decoded', 'text': f'Adds {endpoint(lo)}-{endpoint(hi)} Damage'}
        if lo.get('roll_quality') and lo.get('roll_quality') == hi.get('roll_quality'):
            replacements[first]['roll_quality'] = lo['roll_quality']
        consumed.update(i for i, _ in entries if i != first)
    else:
        for entries, label in groups:
            first = min(i for i, _ in entries)
            source = entries[0][1]
            replacements[first] = {'status': 'decoded', 'text': f'+{endpoint(source)} to {label} Damage'}
            if source.get('roll_quality'):
                replacements[first]['roll_quality'] = source['roll_quality']
            consumed.update(i for i, _ in entries if i != first)
    return [replacements.get(i, row) for i, row in enumerate(rows) if i not in consumed]


def display_damage(rows, item=None):
    if (item or {}).get('category') == 'armor':
        rows = armor_damage(rows)
    replacements, consumed = {}, set()
    maximum_bonus = per_level_maximum(rows)
    for minimum, maximum, template in DAMAGE_PAIRS:
        throwing = minimum == 159
        if throwing and not (
            (item or {}).get('category') == 'weapons'
            and (item or {}).get('item_type') in {'tkni', 'taxe', 'jave', 'ajav'}
        ):
            continue
        pairs = [
            [(i, r) for i, r in enumerate(rows) if r.get('memory_stat', {}).get('id') == stat]
            for stat in (minimum, maximum)
        ]
        if any(len(pair) != 1 for pair in pairs):
            continue
        (low_index, low), (high_index, high) = pairs[0][0], pairs[1][0]
        if (
            any(
                r.get('status') != 'decoded'
                or r['memory_stat'].get('layer') != 0
                or type(r.get('value')) not in (int, float)
                or (r.get('presentation') == 'internal' and not throwing)
                for r in (low, high)
            )
            or low['value'] > high['value']
        ):
            continue
        if minimum == 21 and (item or {}).get('item_type') in ('bow', 'abow', 'xbow'):
            template = 'Two-Hand Damage: {lo}-{hi}'
        if minimum in (21, 23) and maximum_bonus and high['memory_stat'].get('raw') == high['value']:
            high = {**high, 'value': high['value'] + maximum_bonus}
        combined = {'status': 'decoded', 'text': template.format(lo=endpoint(low), hi=endpoint(high))}
        if low.get('roll_quality') == high.get('roll_quality') and low.get('roll_quality'):
            combined['roll_quality'] = low['roll_quality']
        first = min(low_index, high_index)
        replacements[first] = combined
        consumed.add(max(low_index, high_index))
    return [replacements.get(i, r) for i, r in enumerate(rows) if i not in consumed]
