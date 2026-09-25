"""Prove PropertyFunc07's +1 maximum-damage fallback from selected quality.

Primary ItemMods.cpp converts an ED roll adding zero damage into Func06 with
nValue=1. The underlying percentage is lost, so it is never reconstructed.
"""

from pricing.knowledge.market_base_catalog import equipment_base
from pricing.knowledge.market_mechanics import THROWING_TYPES


def flat_damage_fallback(facts, pattern):
    if (
        not facts.capture_complete
        or facts.identified is not True
        or facts.ethereal is not False
        or facts.socket_contents != 'empty'
        or facts.item_type in THROWING_TYPES
        or {'17:0', '18:0', '159:0', '160:0'} & facts.stats.keys()
        or '510' in facts.properties
        or facts.properties.get('448', 1) != 1
    ):
        return False
    slots = [slot for slot in (1, 2) if pattern.get(f'mod{slot}code') == 'dmg%']
    if len(slots) != 1:
        return False
    slot = slots[0]
    low, high = pattern.get(f'mod{slot}min'), pattern.get(f'mod{slot}max')
    if type(low) is not int or type(high) is not int or not 0 < low <= high:
        return False
    base = equipment_base(facts.base_name)
    if not base or base[0]['base_code'] != facts.base_code:
        return False
    details = base[0]['details']
    modes = []
    for key, minimum in (('one_hand_damage', 21), ('two_hand_damage', 23)):
        bounds = details.get(key, ())
        if len(bounds) == 2 and all(type(value) is int and value > 0 for value in bounds):
            modes.append((minimum, bounds))
    if not modes or max(bounds[1] for _, bounds in modes) * low // 100 != 0:
        return False
    if max(bounds[1] for _, bounds in modes) * high // 100 != 0:
        # Totals can coincide with real percentage ED. Require local +1 entries
        # whose complete owned chain was also checked for absent17/18.
        owned = facts.provenance.get('capture', {}).get('superior_flat_damage', ())
        expected_owned = [{'id': stat + 1, 'layer': 0, 'raw': 1} for stat, _ in modes]
        if list(owned) != expected_owned:
            return False
    expected = {f'{stat + offset}:0': value + offset for stat, bounds in modes for offset, value in enumerate(bounds)}
    if ({'21:0', '22:0', '23:0', '24:0'} & facts.stats.keys()) != expected.keys():
        return False
    return all(
        (row := facts.stats.get(key, {})).get('status') == 'decoded'
        and type(row.get('value')) is int
        and type(row.get('raw')) is int
        and row['value'] == row['raw'] == value
        for key, value in expected.items()
    )
