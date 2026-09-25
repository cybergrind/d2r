"""Normalize completed-runeword identity from catalog and explicit base selectors."""

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.definition_store import catalog
from pricing.knowledge.market_base_catalog import equipment_base
from pricing.knowledge.market_mechanics import (
    apply_bow_ethereal,
    apply_ordinary_sword_ethereal,
    conflict,
    is_nondurable_bow,
    is_nondurable_sword,
)


def definitions():
    return catalog().runewords


def normalize_runeword(row):
    definition = next((d for name, d in definitions().items() if name.casefold() == row['name'].casefold()), None)
    if not definition:
        return row
    row['name'] = definition['name']
    # Rarity and filled socket count are intrinsic to an identified completed
    # recipe. Ethereal requires explicit listing evidence or verified base mechanics.
    row.update(rarity='runeword', rarity_basis='named_catalog_category')
    row.pop('base_rarity', None)
    if '1281' in row.get('properties', {}):
        quality = row['properties']['1281']
        if type(quality) is str and quality in ('normal', 'superior', 'low quality'):
            row['base_rarity'] = quality
        else:
            conflict(row, 'Runeword base quality selector is invalid.')
    bases = {b['name']: b['code'] for b in metadata()['bases'].values()}
    selectors = [p for p in row.get('raw_properties', []) if p.get('property', '').startswith('Base Item (')]
    names = {p.get('string') for p in selectors}
    if len(names) == 1:
        code = bases.get(next(iter(names)))
        if code in definition['base_codes']:
            row['base_code'] = code
            row['base_selector_properties'] = [str(p['property_id']) for p in selectors]
            resolved = equipment_base(next(iter(names)))
            if resolved and resolved[0]['base_code'] == code:
                base, source = resolved
                details = base.get('details', {})
                if is_nondurable_bow(details.get('item_type'), details.get('no_durability')):
                    apply_bow_ethereal(row, source)
                elif is_nondurable_sword(details.get('item_type'), details.get('no_durability')):
                    apply_ordinary_sword_ethereal(row, source)
            row.setdefault('sockets', len(definition['runes']))
            if row['socket_contents'] == 'unknown':
                row['socket_contents'] = 'filled'
                row['socket_contents_basis'] = 'identified_completed_recipe'
    return row
