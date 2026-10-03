"""Tal mastery rolls use set definitions, not extra random base staffmods."""

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


STATS = ((7, 0, 57 * 256), (9, 0, 77 * 256), (1, 0, 10), (105, 0, 20), (107, 61, 2), (107, 63, 2), (107, 65, 2))
CASES = tuple(
    Case(
        id=f'named-single-skill-bounds/tal/{skill}/{bonus}',
        item=Item(
            'Swirling Crystal',
            'set',
            "Tal Rasha's Lidless Eye",
            tuple((s, p, bonus if s == 107 and p == skill else v) for s, p, v in STATS),
            complete=True,
        ),
        context={},
        covers=("named:set:Tal Rasha's Lidless Eye",),
        scenario='positive' if bonus in (1, 2) else 'negative',
        expected={'assessment': IsPartialDict(contract=IsPartialDict(policy='named'))}
        if bonus in (1, 2)
        else {'assessment': IsPartialDict(contract=None)},
        report_contains=("Tal Rasha's Lidless Eye",),
        evidence=('third-parties/d2data/json/setitems.json',),
    )
    for skill in (61, 63, 65)
    for bonus in (1, 2, 3)
)
