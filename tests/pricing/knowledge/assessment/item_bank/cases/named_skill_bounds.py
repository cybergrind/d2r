"""Native class/tree skill endpoints must gate complete price comparisons."""

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CASES = tuple(
    Case(
        id=f'named-skill-bounds/{name}/{bonus}',
        item=Item(base, 'unique', name, (*other, (stat, layer, bonus)), complete=True),
        context={},
        covers=(f'named:unique:{name}',),
        scenario='positive' if low <= bonus <= high else 'negative',
        expected={'assessment': IsPartialDict(contract=IsPartialDict(policy='named'))}
        if low <= bonus <= high
        else {'assessment': IsPartialDict(contract=None)},
        report_contains=(name,),
        evidence=('third-parties/d2data/json/uniqueitems.json',),
    )
    for name, base, stat, layer, low, high, other in (
        ("Eschuta's Temper", 'Eldritch Orb', 83, 1, 1, 3, ((105, 0, 40), (329, 0, 20), (330, 0, 20), (1, 0, 30))),
        ("Death's Web", 'Unearthed Wand', 188, 17, 1, 2, ((127, 0, 2), (336, 0, 50), (86, 0, 12), (138, 0, 12))),
    )
    for bonus in (low - 1, low, high, high + 1)
)
