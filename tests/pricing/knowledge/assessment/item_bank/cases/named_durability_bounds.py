"""Steelgoad durability: the flat roll is added to a normal or ethereal base."""

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CASES = tuple(
    Case(
        id=f'named-durability-bounds/steelgoad/{ethereal}/{durability}',
        item=Item(
            'Voulge',
            'unique',
            'Steelgoad',
            (
                (112, 0, 96),
                (141, 0, 30),
                (19, 0, 30),
                (39, 0, 5),
                (41, 0, 5),
                (43, 0, 5),
                (45, 0, 5),
                (17, 0, 80),
                (18, 0, 80),
                (73, 0, durability),
            ),
            ethereal=ethereal,
            complete=True,
        ),
        context={},
        covers=('named:unique:Steelgoad',),
        scenario='positive' if index in (1, 2) else 'negative',
        expected={'assessment': IsPartialDict(contract=IsPartialDict(policy='named'))}
        if index in (1, 2)
        else {'assessment': IsPartialDict(contract=None)},
        report_contains=('Steelgoad',),
        evidence=('third-parties/d2data/json/uniqueitems.json', 'third-parties/d2data/json/weapons.json'),
    )
    for ethereal, values in ((False, (69, 70, 90, 91)), (True, (45, 46, 66, 67)))
    for index, durability in enumerate(values)
)
