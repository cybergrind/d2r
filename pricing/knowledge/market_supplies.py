"""Only individual native scrolls have a reviewed supply listing-unit mapping."""

from pricing.knowledge.assessment.policies.supplies import SCROLLS, SOURCE, SOURCE_SHA256, definitions
from pricing.knowledge.market_fixed_facets import apply_fixed_facets


def apply_scroll_facts(row):
    if row.get('category') != 'misc':
        return False
    matches = [code for code, native in definitions().items() if code in SCROLLS and native['name'] == row.get('name')]
    if len(matches) != 1:
        return False
    code = matches[0]
    apply_fixed_facets(
        row,
        code,
        {
            'kind': 'native_single_scroll',
            'path': str(SOURCE.relative_to(SOURCE.parents[3])),
            'sha256': SOURCE_SHA256,
            'locator': '/' + code,
        },
        'Ordinary single-scroll catalog',
    )
    return True
