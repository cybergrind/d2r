"""Shared fixed native facets for explicitly reviewed non-equipment catalogs."""


def apply_fixed_facets(row, code, source, reason):
    from pricing.knowledge.market_mechanics import apply_expected, conflict

    for field, expected in (('base_code', code), ('rarity', 'normal')):
        if row.get(field) not in (None, expected):
            conflict(row, f'{reason} contradicts {field}.')
        else:
            row[field] = expected
            row.setdefault('facet_basis', {})[field] = dict(source)
    if '797' in row['properties'] and row['properties']['797'] != 'normal':
        conflict(row, f'{reason} rarity property is conflicting or malformed.')
    apply_expected(
        row,
        [('sockets', '402', 0), ('ethereal', '738', False), ('socket_contents', '934', 'empty')],
        source,
        reason,
    )
