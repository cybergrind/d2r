"""Named armor comparisons require a total attainable at the captured ED roll."""

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CASES = tuple(
    Case(
        id=f'named-enhanced-defense-totals/shaftstop/{defense}',
        item=Item(
            'Mesh Armor',
            'unique',
            'Shaftstop',
            ((31, 0, defense), (16, 0, 200), (32, 0, 250), (36, 0, 30), (7, 0, 60 * 256)),
            complete=True,
        ),
        context={},
        covers=('named:unique:Shaftstop',),
        scenario='positive' if defense == 642 else 'negative',
        expected={'assessment': IsPartialDict(contract=IsPartialDict(policy='named'))}
        if defense == 642
        else {'assessment': IsPartialDict(contract=None)},
        report_contains=('Shaftstop',),
        evidence=('third-parties/d2data/json/uniqueitems.json', 'third-parties/d2data/json/armor.json'),
    )
    for defense in (641, 642, 643, 650)
)
