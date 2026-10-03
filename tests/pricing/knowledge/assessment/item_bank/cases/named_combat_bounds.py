"""Seraph's combat roll boundaries through complete appraisal."""

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


STATS = ((127, 0, 2), (188, 26, 2), (121, 0, 50), (122, 0, 50), (123, 0, 250), (124, 0, 250), (89, 0, 2))
CASES = tuple(
    Case(
        id=f'named-combat-bounds/seraph/{stat}/{amount}',
        item=Item(
            'Amulet',
            'unique',
            "Seraph's Hymn",
            tuple((s, p, amount if s == stat else v) for s, p, v in STATS),
            complete=True,
        ),
        context={},
        covers=("named:unique:Seraph's Hymn",),
        scenario='positive' if low <= amount <= high else 'negative',
        expected={'assessment': IsPartialDict(contract=IsPartialDict(policy='named'))}
        if low <= amount <= high
        else {'assessment': IsPartialDict(contract=None)},
        report_contains=("Seraph's Hymn",),
        evidence=('third-parties/d2data/json/uniqueitems.json',),
    )
    for stat, low, high in ((121, 25, 50), (122, 25, 50), (123, 150, 250), (124, 150, 250))
    for amount in (low - 1, low, high, high + 1)
)
