"""Native skill legality and missing market mappings remain separate gaps."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CASES = tuple(
    Case(
        id=f'named-oskill-bounds/widowmaker/{level}',
        item=Item(
            'Ward Bow',
            'unique',
            'Widowmaker',
            ((17, 0, 200), (18, 0, 200), (141, 0, 33), (115, 0, 1), (157, 0, 11), (97, 22, level)),
            complete=True,
        ),
        context={},
        covers=('named:unique:Widowmaker',),
        scenario='unknown' if level in (3, 5) else 'negative',
        expected={
            'assessment': IsPartialDict(
                contract=None,
                price_gaps=Contains(
                    'No verified market mapping for native stat 97:22.'
                    if level in (3, 5)
                    else 'Named roll 97:22 is outside its standalone integer range 3-5.'
                ),
            )
        },
        report_contains=('Widowmaker',),
        evidence=('third-parties/d2data/json/uniqueitems.json',),
    )
    for level in (2, 3, 5, 6)
)
