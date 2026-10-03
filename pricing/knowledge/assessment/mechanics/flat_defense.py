"""Total defense for named flat bonuses without enhanced/per-level contributions."""

from pricing.knowledge.assessment.policies.trade_defense import girth_bounds
from pricing.knowledge.market_base_catalog import equipment_base


def possible_defense(facts, definition, family):
    ranges = definition.get('roll_ranges', {})
    flat = ranges.get('31')
    if not flat or flat.get('property') != 'ac' or type(facts.ethereal) is not bool:
        return None
    if facts.rarity == 'set' and girth_bounds(facts) is None:
        return None  # Other set-specific contributions require separate evidence.
    if any(str(s) in ranges or f'{s}:0' in facts.stats for s in (16, 214, 215)):
        return None
    low, high = flat['min'], flat['max']
    if any(type(v) is not int or v < 0 for v in (low, high)) or low > high:
        return None
    if family in ('weapon', 'jewelry'):
        bases = (0,)
    else:
        if facts.ethereal and facts.base_code not in definition.get('base_codes', ()):
            return None  # Preserve the separately tracked ethereal-upgrade gap.
        found = equipment_base(facts.base_name)
        if found is None or found[0]['base_code'] != facts.base_code:
            return None
        bounds = found[0]['details'].get('base_defense', ())
        if len(bounds) != 2 or any(type(v) is not int or v < 0 for v in bounds) or bounds[0] > bounds[1]:
            return None
        bases = tuple(3 * n // 2 if facts.ethereal else n for n in range(bounds[0], bounds[1] + 1))
    return bases, (low, high)


def capture_gap(facts, definition, family):
    bounds = possible_defense(facts, definition, family)
    if bounds is None:
        return None
    bases, (low, high) = bounds
    row = facts.stats.get('31:0', {})
    value = row.get('value')
    if (
        row.get('status') != 'decoded'
        or type(value) is not int
        or type(row.get('raw')) is not int
        or row['raw'] != value
        or not any(low <= value - base <= high for base in bases)
    ):
        return (
            'Named total defense is outside its native base plus flat bonus range '
            f'{min(bases) + low}-{max(bases) + high}.'
        )
    return None
