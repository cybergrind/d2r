"""Named socket counts are clamped, and must agree with captured totals."""

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CASES = tuple(
    Case(
        id=f'named-socket-bounds/heavens-light/{count}',
        item=Item(
            'Mighty Scepter',
            'unique',
            "Heaven's Light",
            (
                (17, 0, 300),
                (18, 0, 300),
                (93, 0, 20),
                (116, 0, 33),
                (89, 0, 3),
                (139, 0, 20),
                (136, 0, 33),
                (194, 0, count),
                (83, 3, 3),
            ),
            sockets=count,
            complete=True,
        ),
        context={},
        covers=("named:unique:Heaven's Light",),
        scenario='positive' if count in (1, 2) else 'negative',
        expected={'assessment': IsPartialDict(contract=IsPartialDict(policy='named'))}
        if count in (1, 2)
        else {'assessment': IsPartialDict(contract=None)},
        report_contains=("Heaven's Light", f'Sockets: {count} (1-2)' if count in (1, 2) else f'Sockets: {count} —'),
        evidence=('third-parties/d2data/json/uniqueitems.json', 'third-parties/d2data/json/weapons.json'),
    )
    for count in (0, 1, 2, 3)
)
