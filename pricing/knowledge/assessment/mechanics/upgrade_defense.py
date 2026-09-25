"""Finite non-ethereal named armor defense outcomes after upgrading.

Pinned D2Game Items.cpp660 rolls the target minac..maxac; D2StatList.cpp414
applies native16 (op13) to base armor. Fixed added defense remains additive.
Ethereal upgrade behavior and variable/per-level added defense need separate proof.
"""

from dataclasses import replace

from pricing.knowledge.assessment.domain.facts import FactStatus, StatKey
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.market_base_catalog import equipment_base


def with_defense_outcomes(facts, contract, paths):
    if (
        contract is None
        or contract.policy != 'named'
        or contract.family not in ('armor', 'helm', 'shield', 'accessory')
    ):
        return paths
    if facts.ethereal is not False:
        return paths
    definition, _ = resolve_named_definition(facts)
    if definition is None:
        return paths
    ranges = definition.get('roll_ranges', {})
    if any(key in ranges for key in ('214', '215')) or any(key in facts.stats for key in ('214:0', '215:0')):
        return paths
    flat = ranges.get('31', {'min': 0, 'max': 0})
    if type(flat['min']) is not int or flat['min'] != flat['max'] or flat['min'] < 0:
        return paths
    enhancement = ranges.get('16', {'min': 0, 'max': 0})
    observed = facts.stat(StatKey(16))
    if observed.status == FactStatus.UNKNOWN and '16' not in ranges and '16:0' not in facts.stats:
        percent = 0
    elif observed.status == FactStatus.KNOWN and type(observed.value) is int:
        percent = observed.value
    else:
        return paths
    if not enhancement['min'] <= percent <= enhancement['max'] or percent < 0:
        return paths
    results = []
    for path in paths:
        target = equipment_base(path.target_name)
        if target is None or target[0]['base_code'] != path.target_code:
            results.append(path)
            continue
        bounds = target[0]['details'].get('base_defense', ())
        if len(bounds) != 2 or any(type(v) is not int or v < 1 for v in bounds) or bounds[0] > bounds[1]:
            results.append(path)
            continue
        values = sorted({base * (100 + percent) // 100 + flat['min'] for base in range(bounds[0], bounds[1] + 1)})
        results.append(
            replace(
                path,
                defense_outcome={
                    'min': values[0],
                    'max': values[-1],
                    'possible_values': values,
                    'base_min': bounds[0],
                    'base_max': bounds[1],
                    'enhanced_defense_percent': percent,
                    'flat_defense': flat['min'],
                    'basis': 'random target base defense with preserved named modifiers',
                    'source': target[1],
                },
            )
        )
    return tuple(results)
