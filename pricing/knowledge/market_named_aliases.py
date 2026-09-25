"""Reviewed market-catalog aliases, never generic article or variant stripping."""

# Cached Traderie catalog IDs/names checked against local unique definitions.
# Renewed and Latent Sunders have their own IDs and must remain distinct.
ORIGINAL_SUNDERS = {
    '1363635173': 'Flame Rift',
    '849307965': 'Crack of the Heavens',
    '21102838': 'Cold Rupture',
    '1283013862': 'Rotting Fissure',
    '374110750': 'Bone Break',
    '1731212580': 'Black Cleft',
}


def canonicalize_named_catalog(row):
    if row.get('category') not in ('unique', 'uniques'):
        return
    catalog_id = row.get('catalog_id')
    name = ORIGINAL_SUNDERS.get(catalog_id)
    if name is None or row.get('name') != 'The ' + name:
        return
    row['catalog_name'] = row['name']
    row['name'] = name
    row.setdefault('facet_basis', {})['identity'] = {
        'kind': 'reviewed_named_catalog_alias',
        'catalog_id': catalog_id,
        'catalog_name': row['catalog_name'],
        'catalog_path': 'pricing/data/appraisal-trade-catalog.json',
        'definition_name': name,
        'reviewed_at': '2026-09-25',
    }
