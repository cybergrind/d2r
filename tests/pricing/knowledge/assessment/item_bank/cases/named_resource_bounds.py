"""Legal native resource rolls are required for named price comparisons."""

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CASES = tuple(
    Case(
        id=f'named-resource-bounds/{name}/{stat}/{amount}',
        item=Item(base, 'unique', name, (*other, (stat, 0, amount)), complete=True),
        context={},
        covers=(f'named:unique:{name}',),
        scenario='positive' if low <= amount <= high else 'negative',
        expected={'assessment': IsPartialDict(contract=IsPartialDict(policy='named'))}
        if low <= amount <= high
        else {'assessment': IsPartialDict(contract=None)},
        report_contains=(name,),
        evidence=('third-parties/d2data/json/uniqueitems.json',),
    )
    for name, base, stat, low, high, other in (
        ("Eschuta's Temper", 'Eldritch Orb', 1, 20, 30, ((83, 1, 3), (105, 0, 40), (329, 0, 20), (330, 0, 20))),
        ("Death's Web", 'Unearthed Wand', 86, 7, 12, ((127, 0, 2), (336, 0, 50), (188, 17, 2), (138, 0, 12))),
        ("Death's Web", 'Unearthed Wand', 138, 7, 12, ((127, 0, 2), (336, 0, 50), (188, 17, 2), (86, 0, 12))),
    )
    for amount in (low - 1, low, high, high + 1)
)
