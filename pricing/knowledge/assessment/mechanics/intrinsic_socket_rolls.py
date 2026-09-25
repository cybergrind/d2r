"""Recover reviewed additive rolls from complete linked-jewel captures.

Only reviewed unscaled scalar stats are enabled. This is not a general subtraction rule:
weapon damage, armor defense, scaled and compound effects need other mechanics.
Rune/gem payloads use separately compiled recipient-specific fixed effects.
"""

from dataclasses import replace

from pricing.knowledge.assessment.domain.facts import FactStatus, thaw
from pricing.knowledge.assessment.mechanics.fixed_socket_scalars import contribution as fixed_contribution


# ItemStatCost: op0, ValShift0, no parameter for each of these item bonuses.
SUPPORTED = frozenset({'2:0', '330:0', '331:0', '333:0', '334:0'})


def intrinsic_socket_rolls(facts, keys):
    state = facts.socket_state
    if (
        state.total.status != FactStatus.KNOWN
        or state.occupied.status != FactStatus.KNOWN
        or not state.identities_complete
    ):
        return None, {}
    if state.occupied.value == 0:
        return facts, {}
    if facts.socket_contents != 'filled' or not facts.capture_complete or facts.gaps:
        return None, {}
    stats = thaw(facts.stats)
    evidence = {}
    for key in keys:
        if key not in SUPPORTED:
            return None, {}
        row = stats.get(key, {})
        total = row.get('value')
        if row.get('status') != 'decoded' or type(total) is not int or total < 0:
            return None, {}
        contribution = 0
        for child in facts.socket_items:
            if child.get('item_type') not in ('jewl', 'cjwl'):
                value = fixed_contribution(facts, child, key)
                if value is None or value < 0:
                    return None, {}
                contribution += value
                continue
            if child.get('stats_complete') is not True:
                return None, {}
            child_row = child.get('stats', {}).get(key)
            value = 0 if child_row is None else child_row.get('value')
            if child_row is not None and child_row.get('status') != 'decoded':
                return None, {}
            if type(value) is not int or value < 0:
                return None, {}
            contribution += value
        intrinsic = total - contribution
        if intrinsic < 0:
            return None, {}
        stats[key] = {**row, 'value': intrinsic}
        evidence[key] = {'observed': total, 'socket': contribution, 'intrinsic': intrinsic}
    # This copy is solely for tier predicates; market properties and capture stay intact.
    return replace(facts, stats=stats), evidence
