"""Compare explicit fractional rates, never rounded viewer-dependent totals.

Cached fields535/536 mix totals with coefficients. Nonintegral rates cannot be
integer tooltip totals; integer conventions remain unresolved. Native func17,
stat op/shift and eligible affix parameters establish the supported coefficients.
"""

from functools import lru_cache

from inventory_tracking.items.metadata import metadata, metadata_generation
from pricing.knowledge.assessment.mechanics.affix_pool import can_generate


SPECS = {
    '218:0': ('dmg/lvl', '535', 4, 3),
    '224:0': ('att/lvl', '536', 2, 1),
}


@lru_cache(maxsize=512)
def eligible_coefficients(base_code, rarity, code, generation):
    values = set()
    for table in metadata()['affixes'].values():
        for entry in table.values():
            if not can_generate(entry, base_code, rarity):
                continue
            record = entry['game_definition']
            for slot in (1, 2, 3):
                value = record.get(f'mod{slot}param')
                if record.get(f'mod{slot}code') == code and type(value) is int and value > 0:
                    values.add(value)
    return frozenset(values)


def affixed_per_level_properties(facts):
    properties, consumed, gaps = {}, set(), []
    for key, (code, prop, op, scale) in SPECS.items():
        if key not in facts.stats:
            continue
        row = facts.stats[key]
        spec = metadata()['stats'].get(key.partition(':')[0], {})
        raw, level = row.get('raw'), row.get('viewer_level')
        denominator = 1 << scale
        if (
            facts.rarity not in ('magic', 'rare')
            or facts.socket_contents != 'empty'
            or spec.get('shift') != 0
            or spec.get('op') != op
            or spec.get('op_param') != scale
            or spec.get('op_base') != 'level'
            or row.get('status') != 'decoded'
            or type(raw) is not int
            or raw <= 0
            or raw % denominator == 0
            or type(level) is not int
            or not 1 <= level <= 99
            or row.get('per_level') != {'numerator': raw, 'denominator': denominator}
            or type(row.get('value')) is not int
            or row['value'] != raw * level // denominator
            or row.get('market_property') not in (None, prop)
            or raw not in eligible_coefficients(facts.base_code, facts.rarity, code, metadata_generation())
        ):
            gaps.append(f'Affix per-level coefficient {key} lacks a verified fractional market convention.')
            continue
        properties[prop] = raw / denominator
        consumed.add(key)
    return properties, consumed, gaps
