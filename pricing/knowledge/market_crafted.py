"""Resolve verified crafted catalog identities without choosing equipment tiers."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.artifacts import read_artifact


CATALOG = Path(__file__).resolve().parents[1] / 'data/appraisal-traderie-catalog.json'
JEWELRY = {
    f'{recipe} {base}': base for recipe in ('Blood', 'Caster', 'Safety', 'Hit Power') for base in ('Ring', 'Amulet')
}


@lru_cache(maxsize=2)
def crafted_catalog(raw):
    rows = json.loads(raw)['items']
    return frozenset((str(r['id']), r['name']) for r in rows if r.get('type') == 'crafted'), hashlib.sha256(
        raw
    ).hexdigest()


def apply_crafted_facts(row):
    from pricing.knowledge.market_mechanics import SOURCE, apply_expected, conflict

    if row.get('category') != 'crafted':
        return
    try:
        identities, generation = crafted_catalog(read_artifact(CATALOG))
    except OSError, KeyError, TypeError, ValueError:
        return
    name = row.get('name')
    if (row.get('catalog_id'), name) not in identities:
        return
    properties = row['properties']
    if ('797' in properties and properties['797'] != 'crafted') or row.get('rarity') not in (None, 'crafted'):
        conflict(row, 'Crafted catalog contradicts supplied rarity.')
        return
    source = {'kind': 'crafted_catalog', 'path': 'pricing/data/appraisal-traderie-catalog.json', 'sha256': generation}
    row['rarity'] = 'crafted'
    row['rarity_basis'] = 'verified_crafted_catalog'
    row.setdefault('facet_basis', {})['rarity'] = source
    recipe_source = metadata().get('crafting_nonethereal', {}).get(name)
    if recipe_source:
        apply_expected(
            row,
            [('ethereal', '738', False)],
            {
                **recipe_source,
                'kind': 'crafted_output_mechanics',
                'reference': 'third-parties/D2MOO/source/D2Game/src/PLAYER/PlrTrade.cpp:787',
            },
            'verified crafting output mechanics',
        )
    base_name = JEWELRY.get(name)
    if base_name is None:
        recipe = metadata().get('crafting_bases', {}).get(name, {})
        tier = properties.get('930')
        target = recipe.get('tiers', {}).get(tier) if type(tier) is str else None
        if target:
            from pricing.knowledge.market_mechanics import apply_base_equipment_facts

            row.update(name=target['name'], catalog_name=name)
            apply_base_equipment_facts(row)
            if row.get('base_code') != target['code']:
                conflict(row, 'Crafted recipe base differs from equipment catalog.')
            row.setdefault('facet_basis', {})['craft_recipe'] = recipe['source']
        return
    candidates = [r for r in metadata()['bases'].values() if r['name'] == base_name and r['category'] == 'misc']
    if len(candidates) != 1:
        return
    code = candidates[0]['code']
    if row.get('base_code') not in (None, code):
        conflict(row, 'Crafted jewelry catalog contradicts supplied base.')
        return
    row.update(name=base_name, catalog_name=name, base_code=code)
    row['facet_basis']['base_code'] = {**source, 'base_metadata': 'inventory_tracking/items/data/item_metadata.json'}
    apply_expected(
        row,
        [('sockets', '402', 0), ('ethereal', '738', False), ('socket_contents', '934', 'empty')],
        SOURCE,
        'non-equipment base mechanics',
    )
