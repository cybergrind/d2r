"""Fathom's native cold endpoints and impossible empty-socket totals."""

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CASES = tuple(
    Case(
        id=f'fathom-roll-bounds/{cold}',
        item=Item(
            'Dimensional Shard',
            'unique',
            "Death's Fathom",
            ((83, 1, 3), (331, 0, cold), (105, 0, 20), (39, 0, 40), (41, 0, 40)),
            complete=True,
        ),
        context={},
        covers=("named:unique:Death's Fathom",),
        scenario='positive' if cold in (15, 30) else 'negative',
        expected={'assessment': IsPartialDict(contract=IsPartialDict(properties=IsPartialDict({'747': cold})))}
        if cold in (15, 30)
        else {'assessment': IsPartialDict(contract=None)},
        report_contains=("Death's Fathom",),
        evidence=('third-parties/d2data/json/uniqueitems.json:/354',),
    )
    for cold in (14, 15, 30, 31, 40)
)
