"""Traderie omission semantics for triage; never applied to captured drops.

PLAN.md afternoon steering, 2026-10-03: sellers mark ethereal copies; absent
named sockets denote native sockets. Explicit values and variable native socket
rolls are preserved rather than guessed.
"""

from functools import lru_cache

from inventory_tracking.items.metadata import metadata, metadata_generation
from pricing.knowledge.definition_store import catalog
from pricing.knowledge.market_named_sockets import fixed_native_socket_count, single_socket_payload
from pricing.triage.listing_crafts import caster_amulet
from pricing.triage.named_base_levels import resolve as base_from_level


# Traderie catalog spellings versus the local game-definition names. These are
# identity aliases, not fuzzy matches; codes come from the selected metadata.
# Verified against d2data localestrings-eng.json and weapons/armor.json.
# Kurast Shield is deliberately excluded: 'Ancient Shield' is duplicated in
# native metadata and needs code-separated bands before introducing that alias.
BASE_ALIASES = {
    'Kris': 'Kriss',
    'Stiletto': 'Stilleto',
    'Mithril Point': 'Mithral Point',
    'Colossus Sword': 'Colossal Sword',
    'Large Siege Bow': 'Long Siege Bow',
    'Sabre': 'Saber',
    'Griffon Headdress': 'Griffon Headress',
    'Hierophant Trophy': 'Heirophant Trophy',
    'Ornate Plate': 'Ornate Armor',
}


@lru_cache(maxsize=2)
def alias_bases(generation):
    names = {base['name']: base for base in metadata()['bases'].values()}
    return {alias: names[name] for alias, name in BASE_ALIASES.items() if name in names}


def normalize(row):
    result = dict(row)
    if caster_amulet(row):
        result['rarity'] = 'crafted'
        result['facet_basis'] = {
            **result.get('facet_basis', {}),
            'rarity': {
                'kind': 'caster_amulet_recipe_signature',
                'reported': 'rare',
                'source': 'third-parties/d2data/json/cubemain.json',
            },
        }
    if row.get('category') == 'base':
        base = alias_bases(metadata_generation()).get(row.get('name'))
        if base and row.get('base_code') in (None, base['code']):
            result.update(name=base['name'], base_name=base['name'], base_code=base['code'])
    properties = row.get('properties', {})
    if result.get('ethereal') is None and '738' not in properties:
        result['ethereal'] = False
    quality = {'uniques': 'unique', 'sets': 'set'}.get(row.get('category'))
    variants = catalog().named_variants.get((quality, row.get('name')), ()) if quality else ()
    if code := base_from_level(result, variants):
        result['base_code'] = code
        result['facet_basis'] = {
            **result.get('facet_basis', {}),
            'base_code': {'kind': 'required_level_excludes_other_tiers', 'required_level': properties['796']},
        }
    if (
        quality
        and '402' not in properties
        and result.get('sockets') in (None, 0)
        and (proof := single_socket_payload(result, variants))
    ):
        result.update(sockets=1, socket_contents='filled')
        result['facet_basis'] = {**result.get('facet_basis', {}), 'sockets': proof}
    if quality and result.get('sockets') is None and '402' not in properties:
        count = fixed_native_socket_count(variants)
        if variants and all(v.get('game_definition') and 'sock' not in v['game_definition'].values() for v in variants):
            count = 0
        if count is not None:
            result['sockets'] = count
    clean_base = row.get('category') == 'base' and row.get('rarity') in ('normal', 'superior')
    if (
        (quality or clean_base)
        and result.get('sockets') is not None
        and result.get('socket_contents') in (None, 'unknown')
        and '934' not in properties
    ):
        result['socket_contents'] = 'empty'
    return result
