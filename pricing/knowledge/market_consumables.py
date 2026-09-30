"""Exact ordinary-potion catalogs; quest potions and thrown weapons stay separate."""

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.policies.consumables import SOURCE, SOURCE_SHA256, definitions
from pricing.knowledge.market_fixed_facets import apply_fixed_facets


def apply_potion_facts(row):
    if row.get('category') != 'misc':
        return False
    native = definitions(read_artifact(SOURCE))
    candidates = [code for code, item in native.items() if item['name'] == row.get('name')]
    if len(candidates) != 1:
        return False
    code = candidates[0]
    apply_fixed_facets(
        row,
        code,
        {
            'kind': 'native_ordinary_potion',
            'path': str(SOURCE.relative_to(SOURCE.parents[3])),
            'sha256': SOURCE_SHA256,
            'locator': '/' + code,
        },
        'Ordinary potion catalog',
    )
    return True
