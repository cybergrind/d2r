"""Exact comparisons for verified fixed armor/shield socket contributions."""

from collections import Counter
from dataclasses import dataclass, replace

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.domain.facts import FactStatus, ItemFacts, StatKey
from pricing.knowledge.assessment.mechanics.socket_effects import BOOLEAN_SOCKET_STATS


@dataclass(frozen=True)
class SocketComparison:
    facts: ItemFacts
    payload: tuple[str, ...]


def compare_named_sockets(facts, definition, family):
    ranges = definition.get('roll_ranges', {})
    sockets = ranges.get('194')
    if sockets is None:
        source = definition.get('game_definition', {})
        params = [source.get(f'par{i}') for i in range(1, 13) if source.get(f'prop{i}') == 'sock']
        if params:
            # PropertyFunc14 falls back to its parameter when min/max are zero.
            if len(params) != 1 or type(params[0]) is not int or not 1 <= params[0] <= 6:
                return None
            sockets = {'min': params[0], 'max': params[0]}
        else:
            sockets = {'min': 1, 'max': 1}
    return _compare(facts, family, sockets, ranges, bounded=True)


def compare_equipment_sockets(facts, family, policy):
    """Keep exact affix totals while proving the fixed socket contribution."""
    from pricing.knowledge.market_base_catalog import equipment_base

    if family not in ('helm', 'armor', 'shield', 'weapon') or facts.socket_contents != 'filled':
        return None
    found = equipment_base(facts.base_name)
    if found is None or found[0]['base_code'] != facts.base_code:
        return None
    maximum = found[0]['details'].get('max_sockets')
    if type(maximum) is not int or maximum < 1:
        return None
    # Affixed comparisons retain the observed modifier; this does not certify
    # that the innate roll is legal or assign it a price from an empty base.
    options = None
    if policy == 'base' and family == 'shield':
        options = found[0]['details'].get('base_resistance_options')
        if not options or any(type(v) is not int or not 0 <= v <= 100 for v in options):
            return None
    return _compare(facts, family, {'min': 1, 'max': maximum}, {}, bounded=policy == 'base', base_resistances=options)


def filler_effects(family):
    """Use only reviewed effects from the request's pinned metadata generation."""
    effects = metadata().get('comparison_socket_effects', {}).get(family, {})
    return {name: {int(stat): value for stat, value in values.items()} for name, values in effects.items()}


def _compare(facts, family, socket_range, ranges, *, bounded, base_resistances=None):
    state = facts.socket_state
    count = state.total.value
    occupied = state.occupied.value
    if (
        family not in ('helm', 'armor', 'shield', 'weapon')
        or facts.runeword
        or facts.socket_contents != 'filled'
        or state.total.status != FactStatus.KNOWN
        or not socket_range['min'] <= count <= socket_range['max']
        or not state.identities_complete
        or state.occupied.status != FactStatus.KNOWN
        or state.empty.status != FactStatus.KNOWN
        or not occupied
    ):
        return None
    effects = filler_effects(family)
    fillers = {b['code']: b['name'] for b in metadata()['bases'].values() if b['name'] in effects}
    if (
        any(c.get('base_code') not in fillers or type(c.get('unit_id')) is not int for c in facts.socket_items)
        or len({c['unit_id'] for c in facts.socket_items}) != occupied
        or [c.get('position') for c in facts.socket_items] != list(range(occupied))
    ):
        return None
    payload = tuple(fillers[c['base_code']] for c in facts.socket_items)
    bonuses = Counter()
    for name in payload:
        bonuses.update(effects[name])
    if base_resistances and any(base_resistances):
        for stat in (39, 41, 43, 45):
            bonuses.setdefault(stat, 0)
    adjusted = dict(facts.stats)
    for stat, bonus in bonuses.items():
        key = f'{stat}:0'
        observed = facts.stat(StatKey(stat, 0))
        if observed.status != FactStatus.KNOWN or type(observed.value) is not int:
            return None
        # The decoder currently proves flag presence only for raw1. Do not
        # turn stacked/non-boolean payloads into a valid flag.
        if stat in BOOLEAN_SOCKET_STATS and (observed.value != 1 or bonus != 1):
            return None
        row = facts.stats[key]
        scale = 256 if stat == 7 else 1
        if (
            row.get('raw') != observed.value * scale
            or facts.properties.get(row.get('market_property')) != observed.value
        ):
            return None
        innate = observed.value - bonus
        spec = ranges.get(str(stat), {'min': 0, 'max': 0})
        if base_resistances is not None and stat in (39, 41, 43, 45):
            if innate not in base_resistances:
                return None
        elif innate < spec['min'] or (bounded and innate > spec['max']):
            return None
        adjusted[key] = {**row, 'value': innate}
    if (
        base_resistances
        and any(base_resistances)
        and len({adjusted[f'{stat}:0']['value'] for stat in (39, 41, 43, 45)}) != 1
    ):
        return None
    return SocketComparison(replace(facts, stats=adjusted), payload)
