"""Prove omitted cold duration from all eligible affix endpoint combinations."""

from functools import lru_cache
from itertools import product
from math import prod

from inventory_tracking.items.metadata import metadata, metadata_generation
from pricing.knowledge.assessment.mechanics.affix_pool import can_generate
from pricing.knowledge.assessment.mechanics.elemental import cold_duration_matches


COLD_CODES = frozenset({'cold-min', 'cold-max', 'cold-len', 'dmg-cold'})


def cold_bounds(record):
    mods = {}
    for slot in (1, 2, 3):
        code = record.get(f'mod{slot}code')
        if code not in COLD_CODES:
            continue
        if code in mods:
            return None
        low, high = record.get(f'mod{slot}min'), record.get(f'mod{slot}max')
        if type(low) is not int or type(high) is not int or not 0 < low <= high:
            return None
        mods[code] = (low, high)
        if code == 'dmg-cold':
            frames = record.get(f'mod{slot}param')
            if type(frames) is not int or frames <= 0:
                return None
            mods[code] = (low, low, high, high, frames, frames)
    if set(mods) == {'dmg-cold'}:
        return mods['dmg-cold']
    if set(mods) == {'cold-min', 'cold-max', 'cold-len'}:
        return (*mods['cold-min'], *mods['cold-max'], *mods['cold-len'])
    return None


@lru_cache(maxsize=512)
def cold_groups(base_code, rarity, generation):
    groups = {}
    for table_name, table in metadata()['affixes'].items():
        for entry in table.values():
            record = entry['game_definition']
            # ITEMS_RollMagicAffixesNew excludes frequency zero; legacy-only rows
            # without frequency are not current online D2R affix outcomes.
            if not can_generate(entry, base_code, rarity):
                continue
            if not any(record.get(f'mod{i}code') in COLD_CODES for i in (1, 2, 3)):
                continue
            bounds = cold_bounds(record)
            group = record.get('group')
            if bounds is None or table_name not in ('prefix', 'suffix') or type(group) is not int or group <= 0:
                return None
            groups.setdefault((table_name, group), set()).add(bounds)
    return tuple((table, tuple(sorted(options))) for (table, _), options in sorted(groups.items()))


@lru_cache(maxsize=1024)
def possible_durations(base_code, rarity, low, high, generation):
    groups = cold_groups(base_code, rarity, generation)
    if not groups or len(groups) > 6 or prod(len(options) + 1 for _, options in groups) > 4096:
        return frozenset()
    durations = set()
    for choices in product(*[(None, *options) for _, options in groups]):
        counts = {
            kind: sum(c is not None and group[0] == kind for c, group in zip(choices, groups, strict=True))
            for kind in ('prefix', 'suffix')
        }
        if rarity == 'crafted' and sum(counts.values()) > 4:
            continue  # ItemsMagic.cpp:765-783 caps crafted random affixes at four.
        if any(count > (1 if rarity == 'magic' else 3) for count in counts.values()):
            continue
        totals = tuple(sum(c[i] for c in choices if c is not None) for i in range(6))
        if totals[0] <= low <= totals[1] and totals[2] <= high <= totals[3]:
            if totals[4] != totals[5]:
                return frozenset()  # The endpoints leave a variable duration.
            durations.add(totals[4])
    return frozenset(durations)


def affixed_cold_properties(facts):
    if not any(key in facts.stats for key in ('54:0', '55:0', '56:0')):
        return {}, set(), []
    gap = ['Affixed cold endpoints do not establish one verified duration.']
    if facts.rarity not in ('magic', 'rare', 'crafted') or facts.socket_contents != 'empty':
        return {}, set(), gap
    endpoints = []
    for key, prop in (('54:0', '482'), ('55:0', '483')):
        row = facts.stats.get(key, {})
        raw = row.get('raw')
        if (
            row.get('status') != 'decoded'
            or type(raw) is not int
            or raw <= 0
            or type(row.get('value')) is not int
            or row['value'] != raw
            or type(facts.properties.get(prop)) not in (int, float)
            or facts.properties[prop] != raw
        ):
            return {}, set(), gap
        endpoints.append(raw)
    low, high = endpoints
    if facts.rarity == 'crafted' and facts.base_code not in metadata().get('crafting_affix_only_cold', ()):
        return {}, set(), gap
    durations = possible_durations(facts.base_code, facts.rarity, low, high, metadata_generation())
    if low > high or len(durations) != 1 or not cold_duration_matches(facts, next(iter(durations))):
        return {}, set(), gap
    if facts.stats['56:0'].get('market_property') is not None:
        return {}, set(), gap
    return {}, {'56:0'}, []
