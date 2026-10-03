"""Display the unmodified native defense range after contribution validation."""

from inventory_tracking.items.ranges import annotate_roll_ranges
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_base_defense import IDENTITY, capture_bounds
from pricing.knowledge.definition_store import catalog


def display_base_defense(extraction, rows):
    item = extraction.get('item', {})
    if (item.get('rarity'), item.get('name')) != IDENTITY:
        return rows
    facts = normalize(extraction)
    bounds = capture_bounds(facts)
    candidates = [r for r in rows if r.get('memory_stat', {}).get('id') == 31]
    if bounds is None or len(candidates) != 1:
        return rows
    original = candidates[0]
    native = original.get('memory_stat', {})
    value = original.get('value')
    if (
        original.get('status') != 'decoded'
        or type(value) is not int
        or not bounds[0] <= value <= bounds[1]
        or native.get('raw') != value
        or native.get('layer') != 0
    ):
        return rows
    row = dict(original)
    definition = catalog().named[facts.rarity, facts.name]
    annotate_roll_ranges(
        [row],
        {
            'roll_ranges': {
                '31': {
                    'stat_id': 31,
                    'min': bounds[0],
                    'max': bounds[1],
                    'better': 'higher',
                }
            },
            'source': dict(definition['base_defense_range']['source']),
            'scope': 'verified unmodified native set base defense',
        },
    )
    return [row if r is original else r for r in rows]
