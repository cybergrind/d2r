"""Cold duration legality is distinct from missing market duration evidence."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CASES = tuple(
    Case(
        id=f'named-elemental-bounds/eye-of-etlich/{frames}',
        item=Item(
            'Amulet',
            'unique',
            'The Eye of Etlich',
            ((32, 0, 40), (89, 0, 5), (127, 0, 1), (60, 0, 7), (54, 0, 2), (55, 0, 5), (56, 0, frames)),
            complete=True,
        ),
        context={},
        covers=('named:unique:The Eye of Etlich',),
        scenario='unknown' if 50 <= frames <= 250 else 'negative',
        expected={
            'assessment': IsPartialDict(
                contract=None,
                price_gaps=Contains(
                    'No verified market mapping for native stat 56:0.'
                    if 50 <= frames <= 250
                    else 'Named roll 56:0 has invalid cold duration or is outside its native frame range 50-250.'
                ),
            )
        },
        report_contains=('The Eye of Etlich',),
        evidence=('third-parties/d2data/json/uniqueitems.json', 'third-parties/d2data/json/properties.json'),
    )
    for frames in (49, 50, 51, 249, 250, 251)
)
