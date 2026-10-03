"""Named throwing totals from pinned native bases, local ED and fixed bonuses."""

import json
from functools import lru_cache
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.mechanics.base_tiers import is_base_upgrade


WEAPONS = Path(__file__).resolve().parents[4] / 'third-parties/d2data/json/weapons.json'
THROWING_TYPES = frozenset({'tkni', 'taxe', 'jave', 'ajav'})
CHANNELS = ((21, 'mindam', 0), (22, 'maxdam', 1), (159, 'minmisdam', 0), (160, 'maxmisdam', 1))


@lru_cache(maxsize=2)
def weapon_bases(raw):
    return json.loads(raw)


def fixed_quantity_keys(facts, definition):
    record = definition.get('game_definition', {})
    slots = [i for i in range(1, 13) if record.get(f'prop{i}') == 'rep-quant']
    if not slots:
        return set(), []
    rate = record.get(f'par{slots[0]}')
    row = facts.stats.get('253:0', {})
    if (
        len(slots) != 1
        or type(rate) is not int
        or rate <= 0
        or row.get('status') != 'decoded'
        or type(row.get('raw')) is not int
        or row['raw'] != rate
        or type(row.get('value')) is not int
        or row['value'] != rate
        or row.get('unit') != 'replenishment_rate'
        or row.get('market_property') is not None
    ):
        return set(), ['Named replenishment rate is missing, changed or unverified.']
    return {'253:0'}, []


def throwing_damage_keys(facts, definition):
    if facts.item_type not in THROWING_TYPES:
        return set(), []
    error = ['Named throwing damage totals are missing, changed or unverified.']
    original = definition.get('base_definition', {})
    original_code = original.get('code')
    upgraded = facts.base_code != original_code
    if upgraded and facts.ethereal is True:
        return set(), ['Named throwing ethereal upgrade damage requires separate verification.']
    if (
        type(facts.ethereal) is not bool
        or facts.sockets != 0
        or facts.socket_contents != 'empty'
        or (upgraded and not is_base_upgrade(original_code, facts.base_code))
    ):
        return set(), error
    try:
        bases = weapon_bases(read_artifact(WEAPONS))
    except OSError, ValueError, TypeError:
        return set(), error
    base = bases.get(facts.base_code, {})
    source = bases.get(original_code, {})
    if (
        base.get('type') != facts.item_type
        or any(original.get(field) != source.get(field) for _, field, _ in CHANNELS)
        or any(base.get(k) != source.get(k) for k in ('normcode', 'ubercode', 'ultracode'))
    ):
        return set(), error
    percentages = []
    for stat in (17, 18):
        row = facts.stats.get(f'{stat}:0', {})
        value = row.get('value')
        if (
            row.get('status') != 'decoded'
            or type(value) is not int
            or value < 0
            or type(row.get('raw')) is not int
            or row['raw'] != value
        ):
            return set(), error
        percentages.append(value)
    if percentages[0] != percentages[1]:
        return set(), error
    flat = [0, 0]
    record = definition.get('game_definition', {})
    if {'218:0', '219:0'} & facts.stats.keys():
        return set(), error
    for i in range(1, 13):
        prop = record.get(f'prop{i}')
        if prop in ('dmg/lvl', 'dmg%/lvl'):
            return set(), error
        if prop not in ('dmg-min', 'dmg-max', 'dmg-norm'):
            continue
        low, high = record.get(f'min{i}'), record.get(f'max{i}')
        if (
            type(low) is not int
            or type(high) is not int
            or not 0 <= low <= high
            or (prop != 'dmg-norm' and low != high)
        ):
            return set(), error
        if prop != 'dmg-max':
            flat[0] += low
        if prop != 'dmg-min':
            flat[1] += high
    for stat, field, side in CHANNELS:
        value = base.get(field)
        if type(value) is not int or value <= 0:
            return set(), error
        if facts.ethereal:
            value = value * 3 // 2
        expected = value * (100 + percentages[side]) // 100 + flat[side]
        row = facts.stats.get(f'{stat}:0', {})
        if (
            row.get('status') != 'decoded'
            or type(row.get('raw')) is not int
            or row['raw'] != expected
            or type(row.get('value')) is not int
            or row['value'] != expected
        ):
            return set(), error
    return {'159:0', '160:0'}, []
