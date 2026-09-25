"""Compare poison totals only when eligible affixes establish one rate/duration."""

from functools import lru_cache
from itertools import product
from math import prod

from inventory_tracking.items.metadata import metadata, metadata_generation
from pricing.knowledge.assessment.mechanics.affix_pool import can_generate
from pricing.knowledge.assessment.mechanics.poison import POISON_KEYS, fixed_poison_total


POISON_CODES = frozenset({'dmg-pois', 'pois-min', 'pois-max', 'pois-len'})


@lru_cache(maxsize=512)
def poison_variants(base_code, rarity, generation):
    groups = {}
    for table_name, table in metadata()['affixes'].items():
        for entry in table.values():
            record = entry['game_definition']
            if not can_generate(entry, base_code, rarity):
                continue
            slots = [i for i in (1, 2, 3) if record.get(f'mod{i}code') in POISON_CODES]
            if not slots:
                continue
            if len(slots) != 1 or record[f'mod{slots[0]}code'] != 'dmg-pois' or table_name not in ('prefix', 'suffix'):
                return None  # Ranged rates/automagic need additional contribution rules.
            slot = slots[0]
            rate, high, frames = (record.get(f'mod{slot}{part}') for part in ('min', 'max', 'param'))
            group = record.get('group')
            if any(type(v) is not int or v <= 0 for v in (rate, high, frames, group)) or rate != high:
                return None
            groups.setdefault((table_name, group), set()).add((rate, frames))
    if not groups or prod(len(v) + 1 for v in groups.values()) > 4096:
        return None
    totals = {}
    ordered = sorted(groups)
    for choices in product(*[(None, *sorted(groups[k])) for k in ordered]):
        selected = [v for v in choices if v is not None]
        if rarity == 'crafted' and len(selected) > 4:
            continue
        if not selected or any(
            sum(v is not None and k[0] == table for k, v in zip(ordered, choices, strict=True))
            > (1 if rarity == 'magic' else 3)
            for table in ('prefix', 'suffix')
        ):
            continue
        rate, frames = (sum(v[i] for v in selected) for i in (0, 1))
        # Save/load preserves summed poison stats and resets item count to one
        # (D2Common Items.cpp:5770-5781). Combat averages length for count>1
        # (D2Game SUnitDmg.cpp:619). Include both conventions conservatively;
        # a scalar listing cannot prove which source state it describes.
        for duration in {frames, frames // len(selected)}:
            total = (rate * duration + 128) // 256
            totals.setdefault(total, set()).add((rate, duration))
    return {k: frozenset(v) for k, v in totals.items()}


def affixed_poison_properties(facts):
    if not POISON_KEYS.intersection(facts.stats):
        return {}, set(), []
    gap = ['Affixed poison total does not establish one verified rate and duration.']
    if facts.rarity not in ('magic', 'rare', 'crafted') or facts.socket_contents != 'empty':
        return {}, set(), gap
    if facts.rarity == 'crafted' and facts.base_code not in metadata().get('crafting_affix_only_poison', ()):
        return {}, set(), gap
    low = facts.stats.get('57:0', {}).get('raw')
    high = facts.stats.get('58:0', {}).get('raw')
    frames = facts.stats.get('59:0', {}).get('raw')
    total = fixed_poison_total(facts, low, high, frames)
    variants = poison_variants(facts.base_code, facts.rarity, metadata_generation())
    if total is None or variants is None:
        return {}, set(), gap
    if variants.get(total) != {(low, frames)}:
        return {}, set(), gap
    if any(facts.stats[k].get('market_property') is not None for k in POISON_KEYS):
        return {}, set(), gap
    return {'589': total}, set(POISON_KEYS), []
