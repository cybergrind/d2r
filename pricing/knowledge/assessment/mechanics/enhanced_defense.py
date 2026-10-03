"""Attainable unique armor totals; ethereal upgrades require separate proof."""

from pricing.knowledge.market_base_catalog import equipment_base


def capture_gap(facts, definition, family):
    if (
        facts.rarity != 'unique'
        or type(facts.ethereal) is not bool
        or family not in ('armor', 'helm', 'shield', 'accessory')
    ):
        return None
    if facts.ethereal and facts.base_code not in definition.get('base_codes', ()):
        return None
    ranges = definition.get('roll_ranges', {})
    enhancement = ranges.get('16')
    if not enhancement or any(str(s) in ranges or f'{s}:0' in facts.stats for s in (214, 215)):
        return None
    row = facts.stats.get('16:0', {})
    percent = row.get('value')
    if (
        row.get('status') != 'decoded'
        or type(percent) is not int
        or not enhancement['min'] <= percent <= enhancement['max']
    ):
        return None  # The scalar validator owns missing/invalid enhanced-defense rolls.
    base = equipment_base(facts.base_name)
    if base is None or base[0]['base_code'] != facts.base_code:
        return None
    bounds = base[0]['details'].get('base_defense', ())
    flat = ranges.get('31', {'min': 0, 'max': 0})
    if (
        len(bounds) != 2
        or any(type(v) is not int or v < 0 for v in (*bounds, flat['min'], flat['max']))
        or bounds[0] > bounds[1]
        or flat['min'] > flat['max']
    ):
        return None
    bases = (bounds[1] + 1,) if facts.base_code in definition.get('base_codes', ()) else range(bounds[0], bounds[1] + 1)
    if facts.ethereal:
        bases = [base * 3 // 2 for base in bases]
    enhanced = [base * (100 + percent) // 100 for base in bases]
    defense = facts.stats.get('31:0', {})
    value = defense.get('value')
    if (
        defense.get('status') != 'decoded'
        or type(value) is not int
        or type(defense.get('raw')) is not int
        or defense['raw'] != value
        or not any(flat['min'] <= value - base <= flat['max'] for base in enhanced)
    ):
        return f'Named total defense is incompatible with its base and captured {percent}% enhanced defense.'
    return None
