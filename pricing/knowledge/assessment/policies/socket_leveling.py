"""Reviewed socket payload utility; separate from trade price and equip readiness."""

import math
from collections import Counter

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.domain.facts import FactStatus, StatKey
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.mechanics.socket_effects import DIAMONDS, RESIST_RUNES, RUBIES
from pricing.knowledge.assessment.registry import FAMILIES


def positive_stat(facts, stat):
    return minimum(facts, stat, 1)


def minimum(facts, stat, value):
    observed = facts.stat(StatKey(stat, 0))
    return (
        observed.status == FactStatus.KNOWN
        and type(observed.value) in (int, float)
        and math.isfinite(observed.value)
        and observed.value >= value
    )


def topaz_magic_find(facts):
    armor_types = set().union(*(f.types for f in FAMILIES if f.name in ('helm', 'armor')))
    if (
        facts.rarity not in ('normal', 'superior', 'magic', 'rare', 'crafted', 'unique', 'set')
        or facts.runeword
        or facts.item_type not in armor_types
        or facts.socket_contents != 'filled'
        or facts.socket_state.total.status != FactStatus.KNOWN
        or not positive_stat(facts, 80)
    ):
        return False
    topazes = {b['code'] for b in metadata()['bases'].values() if b['type'] == 'gemt'}
    return any(child.get('base_code') in topazes for child in facts.socket_items)


def diamond_resistance(facts):
    shield_types = next(f.types for f in FAMILIES if f.name == 'shield')
    state = facts.socket_state
    if (
        facts.rarity not in ('normal', 'superior', 'magic', 'rare', 'crafted', 'unique', 'set')
        or facts.runeword
        or facts.item_type not in shield_types
        or facts.socket_contents != 'filled'
        or state.total.status != FactStatus.KNOWN
        or state.total.value != 3
        or not state.identities_complete
        or len(facts.socket_items) != 3
    ):
        return False
    diamond = next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Perfect Diamond')
    if (
        any(c.get('base_code') != diamond or type(c.get('unit_id')) is not int for c in facts.socket_items)
        or len({c['unit_id'] for c in facts.socket_items}) != 3
        or [c.get('position') for c in facts.socket_items] != [0, 1, 2]
    ):
        return False
    # Pinned gems.json shieldMod1Code=res-all, Min=Max=19 per perfect diamond.
    for stat in (39, 41, 43, 45):
        observed = facts.stat(StatKey(stat, 0))
        if (
            observed.status != FactStatus.KNOWN
            or type(observed.value) not in (int, float)
            or not math.isfinite(observed.value)
            or observed.value < 3 * 19
        ):
            return False
    return True


def complete_fillers(facts):
    state = facts.socket_state
    if (
        facts.runeword
        or facts.socket_contents != 'filled'
        or state.total.status != FactStatus.KNOWN
        or not state.identities_complete
        or not facts.socket_items
    ):
        return []
    children = facts.socket_items
    if (
        any(type(c.get('unit_id')) is not int for c in children)
        or len({c['unit_id'] for c in children}) != len(children)
        or [c.get('position') for c in children] != list(range(len(children)))
    ):
        return []
    names = {b['code']: b['name'] for b in metadata()['bases'].values()}
    return [names.get(c.get('base_code')) for c in children]


def resistance_setup(facts):
    if facts.rarity not in ('normal', 'superior', 'magic', 'rare', 'crafted', 'unique', 'set'):
        return None
    fillers = complete_fillers(facts)
    if not fillers:
        return None
    bonuses = Counter()
    identity = None
    helm = facts.item_type in next(f.types for f in FAMILIES if f.name == 'helm')
    if helm and facts.sockets == 3 and len(fillers) == 3 and all(n in RESIST_RUNES for n in fillers):
        for name in fillers:
            bonuses[RESIST_RUNES[name]] += 30
        index = 5
    elif facts.rarity == 'unique' and facts.name in ("Moser's Blessed Circle", 'Rockstopper'):
        identity, _ = resolve_named_definition(facts)
        if identity is None:
            return None
        moser = facts.name == "Moser's Blessed Circle"
        index = 9 if moser else 10
        for name in fillers:
            if name in RESIST_RUNES:
                bonuses[RESIST_RUNES[name]] += 35 if moser else 30
            elif moser and name in DIAMONDS:
                for stat in (39, 41, 43, 45):
                    bonuses[stat] += DIAMONDS[name]
            elif not moser and name in RUBIES:
                bonuses[7] += RUBIES[name]
            else:
                return None
    else:
        return None
    ranges = (identity or {}).get('roll_ranges', {})
    if all(minimum(facts, stat, value + ranges.get(str(stat), {}).get('min', 0)) for stat, value in bonuses.items()):
        return index
    return None


def socket_patterns(facts):
    if topaz_magic_find(facts):
        yield (
            1,
            'Early magic find before Stealth or stronger equipment; verify equip requirements and preserve survival.',
        )
    if diamond_resistance(facts):
        yield (
            7,
            "Resistance alternative to Ancient's Pledge; "
            'compare equip requirements, blocking and current survival needs.',
        )
    index = resistance_setup(facts)
    if index is not None:
        yield (
            index,
            'Use fillers for a current resistance or life need; verify equip requirements and compare current gear.',
        )
