"""Exact reviewed material identities; set and portal catalogs remain separate."""

from pricing.knowledge.assessment.policies.quest_materials import SOURCE, SOURCE_SHA256, TRADEABLE, definitions
from pricing.knowledge.market_fixed_facets import apply_fixed_facets


def apply_quest_material_facts(row):
    if row.get('category') != 'misc':
        return False
    matches = [
        code for code, native in definitions().items() if code in TRADEABLE and native['market_name'] == row.get('name')
    ]
    if len(matches) != 1:
        return False
    code = matches[0]
    apply_fixed_facets(
        row,
        code,
        {
            'kind': 'native_recipe_material',
            'path': str(SOURCE.relative_to(SOURCE.parents[3])),
            'sha256': SOURCE_SHA256,
            'locator': '/' + code,
        },
        'Reviewed recipe-material catalog',
    )
    return True
