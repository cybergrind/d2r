"""Fixed named stats cannot be treated as newly discovered variable rolls."""

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CASES = tuple(
    Case(
        id=f'named-fixed-bonuses/{name}/{stat}/{delta}',
        item=Item(
            base, 'unique', name, tuple((s, p, v + delta if s == stat else v) for s, p, v in stats), complete=True
        ),
        context={},
        covers=(f'named:unique:{name}',),
        scenario='positive' if delta == 0 else 'negative',
        expected={'assessment': IsPartialDict(contract=IsPartialDict(policy='named'))}
        if delta == 0
        else {'assessment': IsPartialDict(contract=None)},
        report_contains=(name,),
        evidence=('third-parties/d2data/json/uniqueitems.json',),
    )
    for name, base, stats, keys in (
        (
            "Death's Fathom",
            'Dimensional Shard',
            ((83, 1, 3), (331, 0, 30), (105, 0, 20), (39, 0, 40), (41, 0, 40)),
            (83, 105),
        ),
        (
            "Mara's Kaleidoscope",
            'Amulet',
            ((127, 0, 2), *((s, 0, 5) for s in (0, 1, 2, 3)), *((s, 0, 30) for s in (39, 41, 43, 45))),
            (127, 0, 1, 2, 3),
        ),
    )
    for stat in keys
    for delta in (-1, 0, 1)
)
