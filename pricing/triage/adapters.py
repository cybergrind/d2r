"""Captured drops and normalized listings share property IDs and triage selectors."""

from functools import lru_cache

from inventory_tracking.items.metadata import metadata, metadata_generation
from pricing.knowledge.non_equipment_mechanics import BASE_NAMES, EXPECTED


@lru_cache(maxsize=2)
def base_families(generation):
    return {base['name'].casefold(): base['type'] for base in metadata()['bases'].values()}


AFFIXED = {'magic', 'rare', 'crafted'}


def base_facets(properties, rarity, sockets, contents):
    enhanced = [properties[p] for p in ('425', '510') if type(properties.get(p)) in (int, float)]
    return {
        'base_ed': max(enhanced) if enhanced else 0 if rarity == 'normal' else None,
        'empty_sockets': (
            True
            if sockets == 0 or contents == 'empty'
            else None
            if contents is None or contents == 'unknown'
            else not contents
        ),
    }


def expanded_properties(properties):
    properties = dict(properties)
    resistances = ('427', '428', '426', '401')
    if '441' not in properties and all(type(properties.get(k)) in (int, float) for k in resistances):
        properties['441'] = min(properties[k] for k in resistances)
    if type(properties.get('441')) in (int, float):
        for key in resistances:
            properties.setdefault(key, properties['441'])
    return properties


def from_drop(observation):
    from pricing.knowledge.assessment.adapters.capture import bases_by_code, normalize
    from pricing.knowledge.assessment.policies.quest_materials import NAMES
    from pricing.knowledge.socket_materials import TYPES

    facts = normalize(observation)
    facets = {field: getattr(facts, field) for field, _, _ in EXPECTED}
    if facts.base_name in BASE_NAMES:
        for field, _, value in EXPECTED:
            if facets[field] is None:
                facets[field] = value
    properties = expanded_properties(facts.properties)
    defense = facts.stats.get('31:0', {})
    if (
        bases_by_code().get(facts.base_code, {}).get('category') == 'armor'
        and defense.get('status') == 'decoded'
        and type(defense.get('value')) in (int, float)
    ):
        properties['1855'] = defense['value']
    category = {'unique': 'uniques', 'set': 'sets'}.get(facts.rarity, facts.rarity)
    name = facts.base_name if facts.rarity in AFFIXED else facts.name
    if facts.runeword:
        category, name = 'runewords', facts.runeword
    elif facts.rarity not in AFFIXED | {'unique', 'set'}:
        category = (
            'runes'
            if facts.item_type == 'rune'
            else 'gems'
            if facts.item_type in TYPES
            else 'misc'
            if facts.item_type == 'ques'
            else 'base'
        )
        name = NAMES.get(facts.base_code, name)
    return {
        'category': category,
        'name': name,
        'family': facts.item_type,
        'properties': properties,
        'ethereal': facets['ethereal'],
        'sockets': facets['sockets'],
        'base_name': facts.base_name,
        'base_code': facts.base_code,
        'identified': facts.identified,
        'rarity': facts.rarity,
        'socket_contents': facets['socket_contents'],
        'quantity': 1,
        **base_facets(facts.properties, facts.rarity, facets['sockets'], facets['socket_contents']),
    }


def from_listing(row):
    known_base = str(row.get('base_name') or row['name']).casefold() in base_families(metadata_generation())
    category = row.get('rarity') if row.get('rarity') in AFFIXED else row['category']
    if row['category'] == 'charms' and row['name'] in ('Small Charm', 'Large Charm', 'Grand Charm'):
        category = row.get('rarity') or 'magic'
    return {
        'category': category,
        'name': row['name'],
        'family': row.get('item_type')
        or base_families(metadata_generation()).get(str(row.get('base_name') or row['name']).casefold()),
        'properties': expanded_properties(row.get('properties', {})),
        'ethereal': row.get('ethereal'),
        'sockets': row.get('sockets'),
        'base_name': row.get('base_name') or (row['name'] if known_base else None),
        'base_code': row.get('base_code'),
        'quantity': row.get('amount', 1),
        'rarity': row.get('rarity'),
        'socket_contents': row.get('socket_contents'),
        **base_facets(row.get('properties', {}), row.get('rarity'), row.get('sockets'), row.get('socket_contents')),
    }
