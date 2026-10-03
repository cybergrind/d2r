"""Griffon's total defense includes its base; ethereal scales only that base."""

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CASES = tuple(
    Case(
        id=f'named-flat-defense-bounds/griffon/{ethereal}/{defense}',
        item=Item(
            'Diadem',
            'unique',
            "Griffon's Eye",
            ((31, 0, defense), (105, 0, 25), (127, 0, 1), (330, 0, 15), (334, 0, 20)),
            ethereal=ethereal,
            complete=True,
        ),
        context={},
        covers=("named:unique:Griffon's Eye",),
        scenario='positive' if index in (1, 2) else 'negative',
        expected={'assessment': IsPartialDict(contract=IsPartialDict(policy='named'))}
        if index in (1, 2)
        else {'assessment': IsPartialDict(contract=None)},
        report_contains=("Griffon's Eye",),
        evidence=('third-parties/d2data/json/uniqueitems.json', 'third-parties/d2data/json/armor.json'),
    )
    for ethereal, values in ((False, (149, 150, 260, 261)), (True, (174, 175, 290, 291)))
    for index, defense in enumerate(values)
)
