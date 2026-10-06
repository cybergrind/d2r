"""Captured drops and normalized listings share property IDs and triage selectors."""

from functools import lru_cache

from inventory_tracking.items.metadata import metadata, metadata_generation
from pricing.knowledge.material_items import MATERIAL_POTIONS
from pricing.knowledge.non_equipment_mechanics import BASE_NAMES, EXPECTED
from pricing.triage.charm_modifiers import poison_total, suffix
from pricing.triage.listing_defaults import normalize as listing_defaults


# Scalar native flags whose market facets are boolean in appraisal-properties.json:
# Indestructible, Cannot Be Frozen, Half Freeze Duration, Ignore Target Defense,
# Knockback and Prevent Monster Heal. Numeric text effects are not flags.
BOOLEAN_PROPERTIES = frozenset({'432', '591', '447', '553', '532', '531'})


@lru_cache(maxsize=2)
def base_families(generation):
    return {base['name'].casefold(): base['type'] for base in metadata()['bases'].values()}


@lru_cache(maxsize=2)
def bases_by_code(generation):
    return {base['code']: base for base in metadata()['bases'].values()}


@lru_cache(maxsize=2)
def unique_bases_by_name(generation):
    names = {}
    for base in metadata()['bases'].values():
        names.setdefault(base['name'].casefold(), []).append(base)
    return {name: rows[0] for name, rows in names.items() if len(rows) == 1}


def crafted_family(row):
    if row.get('rarity_basis') != 'verified_crafted_catalog':
        return None
    recipe = metadata().get('crafting_bases', {}).get(row.get('catalog_name') or row.get('name'), {})
    tiers = recipe.get('tiers', {})
    bases = bases_by_code(metadata_generation())
    families = {bases.get(base.get('code'), {}).get('type') for base in tiers.values()}
    return next(iter(families)) if len(families) == 1 and None not in families else None


AFFIXED = {'magic', 'rare', 'crafted'}
# Identity/scope fields and total defense are not modifier rolls. ED is a
# separate facet; all other observed properties remain in the base signature.
BASE_CONTEXT = {
    '797',
    '798',
    '799',
    '800',
    '1854',
    '796',
    '738',
    '402',
    '934',
    '1855',
    '425',
    '510',
    '930',
    '1216',
    '1940',
}


def base_modifiers(properties):
    values = {str(k): v for k, v in properties.items() if str(k) not in BASE_CONTEXT and v != 0}
    return None if any(v is None for v in values.values()) else dict(sorted(values.items()))


def base_facets(properties, rarity, sockets, contents, *, base=None):
    properties = expanded_properties(properties)
    base = base or {}
    if rarity in ('normal', 'superior') and contents == 'empty':
        if base.get('category') == 'weapons':
            # Traderie property551 is the total Two-Hand Damage header, not
            # an affix. Keep it in observed properties, outside the modifier key.
            properties.pop('551', None)
        # Empty clean armor cannot roll flat-defense affixes. Sellers also use
        # property399 for its total; retain conflicting dual-field evidence.
        defense = properties.get('399')
        if (
            base.get('category') == 'armor'
            and type(defense) in (int, float)
            and properties.get('1855', defense) == defense
        ):
            properties.pop('399')
        if '446' in properties:
            native_block = base.get('native_block')
            if native_block is not None and properties['446'] == native_block:
                properties.pop('446')
        inherent = base.get('undead_damage_bonus')
        if inherent and properties.get('538') == inherent:
            properties.pop('538')
    enhanced_ids = {'armor': ('425',), 'weapons': ('510',)}.get(base.get('category'), ('425', '510'))
    enhanced = [properties[p] for p in enhanced_ids if p in properties]
    unreadable_enhancement = any(type(value) not in (int, float) for value in enhanced)
    modifiers = base_modifiers(properties)
    if modifiers is not None:
        # Shields can carry innate weapon damage; it is not superior armor ED.
        for prop in {'425', '510'} - set(enhanced_ids):
            if prop in properties:
                if type(properties[prop]) not in (int, float):
                    modifiers = None
                    break
                if properties[prop] != 0:
                    modifiers[prop] = properties[prop]
    ed = None if unreadable_enhancement else max(enhanced) if enhanced else 0 if rarity == 'normal' else None
    if (
        not enhanced
        and rarity == 'superior'
        and contents == 'empty'
        and base.get('category') == 'weapons'
        and type(properties.get('423')) is int
        and 1 <= properties['423'] <= 3
        and type(properties.get('937')) is int
        and 10 <= properties['937'] <= 15
    ):
        # Native qualityitems.json row 5: att + dur%, with no third modifier.
        # This pair proves zero ED; either bonus alone leaves ED unknown.
        ed = 0
    return {
        'base_ed_grade': 'perfect' if ed == 15 else 'ordinary' if ed is not None and 0 <= ed < 15 else None,
        'base_modifiers': modifiers,
        'base_ed': ed,
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
    # Native flags assert presence with integer 1. Never coerce arbitrary
    # nonzero payloads or numeric stats merely because their value is one.
    for prop in BOOLEAN_PROPERTIES:
        if type(properties.get(prop)) is int and properties[prop] == 1:
            properties[prop] = True
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
    from pricing.triage.jewel_level import required_level

    facts = normalize(observation)
    facets = {field: getattr(facts, field) for field, _, _ in EXPECTED}
    if facts.base_name in BASE_NAMES:
        for field, _, value in EXPECTED:
            if facets[field] is None:
                facets[field] = value
    base = bases_by_code().get(facts.base_code, {})
    if (
        base.get('max_sockets') == 0
        and facets['sockets'] in (None, 0)
        and facets['socket_contents'] in (None, 'unknown', 'empty')
    ):
        # A verified zero-capacity base supplies mechanics, not a guess about capture flags.
        facets.update(sockets=0, socket_contents='empty')
    properties = expanded_properties(facts.properties)
    if (poison := poison_total(facts)) is not None:
        properties.setdefault('518', poison)
    if (level := required_level(facts)) is not None:
        properties['796'] = level
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
            if facts.item_type == 'ques' or facts.base_code in MATERIAL_POTIONS
            else 'base'
        )
        name = NAMES.get(facts.base_code, name)
    return {
        'category': category,
        'name': name,
        'family': facts.item_type,
        'properties': properties,
        'native_rolls': {
            key: row['value']
            for key, row in facts.stats.items()
            if row.get('status') == 'decoded' and type(row.get('value')) in (int, float)
        },
        'charm_suffix': suffix(facts.base_name, properties),
        'ethereal': facets['ethereal'],
        'sockets': facets['sockets'],
        'base_name': facts.base_name,
        'base_code': facts.base_code,
        'identified': facts.identified,
        'item_level': facts.item_level,
        'rarity': facts.rarity,
        'socket_contents': facets['socket_contents'],
        'quantity': observation.get('item', {}).get('quantity', 1) if category in {'runes', 'gems', 'misc'} else 1,
        **base_facets(
            facts.properties,
            facts.rarity,
            facets['sockets'],
            facets['socket_contents'],
            base=bases_by_code().get(facts.base_code),
        ),
    }


def from_listing(row):
    from pricing.triage.facet_identity import catalog_identity

    row = listing_defaults(row)
    base = bases_by_code(metadata_generation()).get(row.get('base_code'), {})
    if (
        not row.get('base_code')
        and row['category'] == 'base'
        and (not row.get('base_name') or row['base_name'].casefold() == row['name'].casefold())
    ):
        base = unique_bases_by_name(metadata_generation()).get(row['name'].casefold(), {})
    base_name = row.get('base_name') or base.get('name') or row['name']
    known_base = str(base_name).casefold() in base_families(metadata_generation())
    category = row.get('rarity') if row.get('rarity') in AFFIXED else row['category']
    if category == 'base' and row.get('rarity') is None:
        from pricing.triage.unknown_affixed import proven

        if proven(row, base):
            category = 'affixed_unknown'
    if row['category'] == 'charms' and row['name'] in ('Small Charm', 'Large Charm', 'Grand Charm'):
        category = row.get('rarity') or 'magic'
    return {
        'category': category,
        'name': row['name'],
        'facet_table_id': catalog_identity(row),
        'family': (
            base.get('type')
            or row.get('item_type')
            or base_families(metadata_generation()).get(str(base_name).casefold())
            or crafted_family(row)
        ),
        'properties': expanded_properties(row.get('properties', {})),
        'charm_suffix': suffix(base_name, expanded_properties(row.get('properties', {}))),
        'ethereal': row.get('ethereal'),
        'sockets': row.get('sockets'),
        'base_name': base_name if known_base else None,
        'base_code': row.get('base_code') or base.get('code'),
        'quantity': row.get('amount', 1),
        'rarity': row.get('rarity'),
        'socket_contents': row.get('socket_contents'),
        **base_facets(
            row.get('properties', {}), row.get('rarity'), row.get('sockets'), row.get('socket_contents'), base=base
        ),
    }
