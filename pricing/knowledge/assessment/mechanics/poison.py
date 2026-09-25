"""Verify fixed single-source poison in native and decoded units."""

POISON_KEYS = frozenset({'57:0', '58:0', '59:0', '326:0'})


def fixed_poison_range(facts, low, high, frames):
    if any(type(v) is not int or v <= 0 for v in (low, high, frames)) or low > high:
        return None
    expected = {
        '57:0': (low, low / 256, 'damage_per_frame'),
        '58:0': (high, high / 256, 'damage_per_frame'),
        '59:0': (frames, frames / 25, 'seconds'),
        '326:0': (1, 1, 'count'),
    }
    for key, (raw, value, unit) in expected.items():
        row = facts.stats.get(key, {})
        if (
            row.get('status') != 'decoded'
            or type(row.get('raw')) is not int
            or row['raw'] != raw
            or type(row.get('value')) not in (int, float)
            or row['value'] != value
            or row.get('unit') != unit
        ):
            return None
    return tuple((rate * frames + 128) // 256 for rate in (low, high))


def fixed_poison_total(facts, low, high, frames):
    if low != high:
        return None
    result = fixed_poison_range(facts, low, high, frames)
    return result[0] if result is not None else None
