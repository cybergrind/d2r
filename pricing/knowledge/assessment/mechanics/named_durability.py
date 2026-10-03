"""Maximum durability includes the base plus a named flat durability modifier."""

from pricing.knowledge.market_base_catalog import equipment_base


def capture_gap(facts, definition):
    ranges = definition.get('roll_ranges', {})
    flat = ranges.get('73')
    if not flat or flat.get('property') != 'dur' or type(facts.ethereal) is not bool:
        return None
    if '75' in ranges or '75:0' in facts.stats:
        return None  # Percentage durability needs a separate native projection proof.
    if facts.ethereal and facts.base_code not in definition.get('base_codes', ()):
        return None  # Do not infer the ethereal upgrade's base state.
    if any(
        value in ('dur', 'dur%')
        for key, value in definition.get('game_definition', {}).items()
        if key.startswith('aprop')
    ):
        return None
    found = equipment_base(facts.base_name)
    if found is None or found[0]['base_code'] != facts.base_code:
        return None
    base = found[0]['details'].get('durability')
    low, high = flat['min'], flat['max']
    if (
        type(base) is not int
        or not 1 <= base <= 255
        or any(type(n) is not int or n < 0 for n in (low, high))
        or low > high
        or found[0]['details'].get('no_durability')
    ):
        return None
    base = base // 2 + 1 if facts.ethereal else base
    low, high = base + low, base + high
    row = facts.stats.get('73:0', {})
    value = row.get('value')
    if (
        row.get('status') != 'decoded'
        or type(value) is not int
        or type(row.get('raw')) is not int
        or row['raw'] != value
        or not low <= value <= high
    ):
        return f'Named maximum durability is outside its native base plus bonus range {low}-{high}.'
    return None
