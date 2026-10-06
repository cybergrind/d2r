"""Exclusive Rainbow Facet element/event identities from reviewed native tables."""

from functools import lru_cache

from pricing.knowledge.market_facet_catalog import VARIANTS


def catalog_identity(row):
    if row.get('category') != 'uniques' or row.get('name') != 'Rainbow Facet':
        return None
    basis = row.get('facet_basis', {}).get('identity', {})
    if basis.get('kind') != 'reviewed_facet_catalog_variant':
        return None
    for table, catalog_id, label, *_ in VARIANTS:
        if (
            basis.get('table_id') == table
            and row.get('catalog_id') == basis.get('catalog_id') == catalog_id
            and row.get('catalog_name') == basis.get('catalog_name') == 'Rainbow Facet: ' + label
        ):
            return table
    return None


@lru_cache(maxsize=1)
def variants():
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.mechanics.triggers import MARKET_FIELDS

    meta = metadata()
    skills = {row['name']: int(key) for key, row in meta['skills'].items()}
    result = []
    for table, _, _, element, event, skill, level in VARIANTS:
        stat = 197 if event == 'death-skill' else 199
        props = tuple(
            next(row['property_id'] for row in meta['stats'].values() if row['name'] == name)
            for name in (f'passive_{element}_mastery', f'passive_{element}_pierce')
        )
        result.append((table, props, f'{stat}:{skills[skill] * 64 + level}', MARKET_FIELDS.get((stat, skills[skill]))))
    return result


def identity(item):
    properties = item.get('properties', {})
    native = item.get('native_rolls', {})
    events = {k: v for k, v in native.items() if k.startswith(('197:', '199:'))}
    market_events = {p for _, _, _, p in variants() if p and properties.get(p) not in (None, 0)}
    rolls = {p for _, props, _, _ in variants() for p in props if properties.get(p) not in (None, 0)}
    matches = []
    for table, props, trigger, market in variants():
        if rolls != set(props):
            continue
        if not all(type(properties.get(p)) in (int, float) and 3 <= properties[p] <= 5 for p in props):
            continue
        if events and events != {trigger: 100}:
            continue
        if market_events and (market_events != {market} or properties.get(market) != 100):
            continue
        catalog = item.get('facet_table_id')
        if catalog is not None and catalog != table:
            continue
        if catalog == table or native.get(trigger) == 100 or (market and properties.get(market) == 100):
            matches.append(table)
    return matches[0] if len(matches) == 1 else None
