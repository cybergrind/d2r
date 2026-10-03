"""Reviewed scalar and compound roll identities shared by evidence and captures."""

from math import isfinite

from inventory_tracking.items.metadata import combine_enhanced_damage, metadata
from pricing.knowledge.assessment.mechanics.waterwalk_defense import (
    VARIANT_MODE as WATERWALK_MODE,
    valid_total_defense as valid_waterwalk_defense,
)
from pricing.knowledge.assessment.policies.trade_base_defense import MODE as BASE_MODE
from pricing.knowledge.assessment.policies.trade_choices import MODE as CHOICE_MODE
from pricing.knowledge.assessment.policies.trade_defense import MODE, valid_total_defense
from pricing.knowledge.assessment.property_equivalence import (
    ALL_ATTRIBUTES,
    ALL_RESISTANCES,
    ATTRIBUTES,
    ELEMENTAL_RESISTANCES,
    canonical_properties,
)


ENHANCED_DAMAGE_KEYS = ('17:0', '18:0')
ENHANCED_DAMAGE_PROPERTY = '510'  # Decoder's equal min/max ED facet, not base physical damage.
ALL_ATTRIBUTE_KEYS = ('0:0', '1:0', '2:0', '3:0')
ALL_RESISTANCE_KEYS = ('39:0', '41:0', '43:0', '45:0')
COMPOUNDS = {
    'enhanced_damage': (ENHANCED_DAMAGE_KEYS, ENHANCED_DAMAGE_PROPERTY),
    'all_resistances': (ALL_RESISTANCE_KEYS, ALL_RESISTANCES),
    'all_attributes': (ALL_ATTRIBUTE_KEYS, ALL_ATTRIBUTES),
}


def market_mapping(review):
    if review.get('property_choice') not in (None, CHOICE_MODE):
        raise ValueError('Unsupported trade property choice')
    mapping = dict(review.get('market_stat_properties', {}))
    specs = metadata()['stats']
    total_defense = review.get('total_defense')
    base_defense = review.get('base_defense')
    if base_defense not in (None, BASE_MODE) or (
        base_defense and (mapping.get('31:0') != '1855' or total_defense or review.get('compound_stats'))
    ):
        raise ValueError('Unverified base-defense trade representation')
    if total_defense not in (None, MODE, WATERWALK_MODE) or (total_defense and mapping.get('31:0') != '1855'):
        raise ValueError('Unverified total-defense trade representation')
    for key, prop in mapping.items():
        if (total_defense in (MODE, WATERWALK_MODE) or base_defense == BASE_MODE) and (key, prop) == ('31:0', '1855'):
            continue
        stat, parameter = key.split(':')
        if not isinstance(prop, str) or not prop or parameter != '0' or specs.get(stat, {}).get('property_id') != prop:
            raise ValueError('Unverified trade evidence native mapping')
    compounds = review.get('compound_stats', [])
    if len(compounds) != len(set(compounds)) or set(compounds) - COMPOUNDS.keys():
        raise ValueError('Unsupported trade compound roll')
    for compound in compounds:
        keys, prop = COMPOUNDS[compound]
        if set(keys) & mapping.keys():
            raise ValueError('Compound trade roll cannot override scalar mapping')
        mapping.update(dict.fromkeys(keys, prop))
    if set(mapping) != set(review['material_stats']):
        raise ValueError('Missing trade evidence native mapping')
    return mapping


def valid_market_compounds(review, properties):
    for compound, combined, members in (
        ('all_resistances', ALL_RESISTANCES, ELEMENTAL_RESISTANCES),
        ('all_attributes', ALL_ATTRIBUTES, ATTRIBUTES),
    ):
        if compound in review.get('compound_stats', []):
            try:
                canonical_properties({key: properties[key] for key in (members | {combined}) & properties.keys()})
            except ValueError:
                return False
    return True


def _values(keys, facts):
    result = []
    for key in keys:
        row = facts.stats.get(key, {})
        value = row.get('value')
        if row.get('status') != 'decoded' or type(value) not in (int, float) or not isfinite(value):
            return None
        result.append(value)
    return result


def valid_compounds(review, facts, *, market_properties=None):
    mode = review.get('total_defense')
    validators = {MODE: valid_total_defense, WATERWALK_MODE: valid_waterwalk_defense}
    if mode and (mode not in validators or not validators[mode](facts, market_properties=market_properties)):
        return False
    for compound in review.get('compound_stats', []):
        if compound not in COMPOUNDS:
            return False
        keys, prop = COMPOUNDS[compound]
        values = _values(keys, facts)
        if values is None:
            return False
        if compound in ('all_resistances', 'all_attributes'):
            specs = metadata()['stats']
            actual = {specs[key.split(':')[0]]['property_id']: value for key, value in zip(keys, values, strict=True)}
            if actual != canonical_properties({prop: values[0]}):
                return False
        else:
            rows = [
                {
                    'status': 'decoded',
                    'value': value,
                    'memory_stat': {'id': int(key.split(':')[0]), 'layer': 0, 'raw': value},
                }
                for key, value in zip(keys, values, strict=True)
            ]
            _, facet = combine_enhanced_damage(rows)
            if not facet or facet['property_id'] != prop:
                return False
    return True
