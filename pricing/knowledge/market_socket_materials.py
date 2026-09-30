"""Native fixed facets for catalog-identified loose rune/gem market listings."""

from pricing.knowledge.market_fixed_facets import apply_fixed_facets
from pricing.knowledge.socket_materials import SOURCE, SOURCE_SHA256, definitions


def apply_material_facts(row):
    # Imported locally to keep market_mechanics' dispatch dependency acyclic.
    from pricing.knowledge.market_mechanics import conflict

    category = row.get('category')
    if category not in ('runes', 'gems'):
        return False
    candidates = [
        (code, native)
        for code, native in definitions().items()
        if native['name'] == row.get('name') and (native['type'] == 'rune') == (category == 'runes')
    ]
    if len(candidates) != 1:
        conflict(row, 'Rune/gem catalog identity or grade is unverified.')
        return True
    code, _native = candidates[0]
    source = {
        'kind': 'native_socket_material',
        'path': str(SOURCE.relative_to(SOURCE.parents[3])),
        'sha256': SOURCE_SHA256,
        'locator': '/' + code,
    }
    apply_fixed_facets(row, code, source, 'Loose rune/gem catalog')
    return True
