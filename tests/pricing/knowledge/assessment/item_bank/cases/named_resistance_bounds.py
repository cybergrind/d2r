"""Shared resistance rolls cannot be priced as independent component rolls."""

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


CASES = tuple(
    Case(
        id=f'named-resistance-bounds/kira/{index}',
        item=Item(
            'Tiara',
            'unique',
            "Kira's Guardian",
            ((31, 0, 100), (99, 0, 20), (153, 0, 1), *zip((39, 41, 43, 45), (0,) * 4, res, strict=True)),
            sockets=1 if rune else 0,
            socket_contents='filled' if rune else 'empty',
            socket_items=(SocketItem(rune, (), complete=True),) if rune else (),
            complete=True,
        ),
        context={},
        covers=("named:unique:Kira's Guardian",),
        scenario='positive' if valid else 'negative',
        expected={'assessment': IsPartialDict(contract=IsPartialDict(policy='named'))}
        if valid
        else {'assessment': IsPartialDict(contract=None)},
        report_contains=("Kira's Guardian",),
        evidence=('third-parties/d2data/json/uniqueitems.json',),
    )
    for index, (res, rune, valid) in enumerate(
        (
            ((50,) * 4, None, True),
            ((70,) * 4, None, True),
            ((49,) * 4, None, False),
            ((71,) * 4, None, False),
            ((60, 61, 60, 60), None, False),
            ((100, 70, 70, 70), 'Ral Rune', True),
            ((100, 69, 70, 70), 'Ral Rune', False),
            ((101, 71, 71, 71), 'Ral Rune', False),
        )
    )
)
