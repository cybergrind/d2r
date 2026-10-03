"""Total defense for flat-bonus uniques with verified contribution boundaries.

D2Game Items.cpp660 rolls base minac..maxac (also on upgrades); flat armor
properties add to that base. Enhanced/per-level and set contributions are separate.
"""

from inventory_tracking.items.ranges import annotate_roll_ranges
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.handlers.socket_fillers import compare_named_sockets
from pricing.knowledge.assessment.policies.trade_defense import girth_bounds
from pricing.knowledge.assessment.registry import classify
from pricing.knowledge.market_base_catalog import equipment_base


def display_flat_defense(extraction, rows):
    candidates = [r for r in rows if r.get('memory_stat', {}).get('id') == 31]
    if len(candidates) != 1:
        return rows
    facts = normalize(extraction)
    if (
        facts.rarity not in ('unique', 'set')
        or facts.identified is not True
        or type(facts.ethereal) is not bool
        or facts.gaps
    ):
        return rows
    if facts.rarity == 'set' and girth_bounds(facts) is None:
        return rows
    definition, errors = resolve_named_definition(facts)
    if errors or definition is None:
        return rows
    if facts.ethereal and facts.base_code not in definition.get('base_codes', ()):
        return rows  # Ethereal upgrade mechanics require separate evidence.
    ranges = definition.get('roll_ranges', {})
    flat = ranges.get('31')
    if not flat or any(str(s) in ranges or f'{s}:0' in facts.stats for s in (16, 214, 215)):
        return rows
    native_sockets = definition.get('native_socket_range')
    if native_sockets and not native_sockets['min'] <= facts.sockets <= native_sockets['max']:
        return rows
    if facts.socket_contents == 'filled':
        family, _ = classify(facts)
        comparison = compare_named_sockets(facts, definition, family)
        if comparison is None or comparison.facts.stats.get('31:0') != facts.stats.get('31:0'):
            return rows
    elif facts.socket_contents != 'empty':
        return rows
    base = equipment_base(facts.base_name)
    if base is None or base[0]['base_code'] != facts.base_code:
        return rows
    capacity = base[0]['details'].get('max_sockets')
    if type(capacity) is not int or facts.sockets > capacity or (not native_sockets and facts.sockets > 1):
        return rows
    bounds = base[0]['details'].get('base_defense', ())
    if len(bounds) != 2:
        return rows
    values = (*bounds, flat['min'], flat['max'])
    if any(type(v) is not int or v < 0 for v in values) or bounds[0] > bounds[1] or flat['min'] > flat['max']:
        return rows
    # ItemMods.cpp ITEMMODS_ApplyEthereality scales the base stat, not flat bonuses.
    possible_bases = tuple(3 * value // 2 if facts.ethereal else value for value in range(bounds[0], bounds[1] + 1))
    bounds = (possible_bases[0], possible_bases[-1])
    original = candidates[0]
    value = original.get('value')
    low, high = bounds[0] + flat['min'], bounds[1] + flat['max']
    native = original.get('memory_stat', {})
    if (
        original.get('status') != 'decoded'
        or type(value) is not int
        or not low <= value <= high
        or native.get('layer') != 0
        or native.get('raw') != value
        or not any(flat['min'] <= value - base_value <= flat['max'] for base_value in possible_bases)
    ):
        return rows
    row = dict(original)
    annotate_roll_ranges(
        [row],
        {
            'roll_ranges': {
                '31': {
                    'stat_id': 31,
                    'min': low,
                    'max': high,
                    'better': 'higher',
                    'base_range': list(bounds),
                    'flat_bonus_range': [flat['min'], flat['max']],
                    'ethereal': facts.ethereal,
                }
            },
            'source': {'definition': definition['source'], 'base': base[1]},
            'scope': f'{facts.rarity} total defense from base and flat bonus; verified unchanged by sockets',
        },
    )
    return [row if r is original else r for r in rows]
