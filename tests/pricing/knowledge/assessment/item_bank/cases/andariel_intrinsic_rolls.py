"""Native strength/leech rolls must survive socket insertion without becoming perfect."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.poison_andariel import ITEM
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem


def cases():
    for label, payload, total, intrinsic in (
        ('ral-perfect', SocketItem('Ral Rune'), 30, 30),
        ('fal-perfect', SocketItem('Fal Rune'), 40, 30),
        ('amethyst-perfect', SocketItem('Perfect Amethyst'), 40, 30),
        ('jewel-not-perfect', SocketItem('Jewel', ((0, 0, 5),), complete=True), 30, 25),
        ('jewel-incomplete', SocketItem('Jewel', ((0, 0, 5),)), 30, None),
    ):
        item = replace(
            ITEM,
            complete=True,
            sockets=1,
            socket_contents='filled',
            socket_items=(payload,),
            raw_stats=tuple((s, p, total if s == 0 else 10 if s == 60 else v) for s, p, v in ITEM.raw_stats),
        )
        proof = (
            {}
            if intrinsic is None
            else {
                'intrinsic_rolls': IsPartialDict(
                    {
                        '0:0': {'observed': total, 'intrinsic': intrinsic, 'socket': total - intrinsic},
                        '60:0': {'observed': 10, 'intrinsic': 10, 'socket': 0},
                    }
                ),
            }
        )
        yield Case(
            id=f'andariel-intrinsic/{label}',
            item=item,
            context={},
            scenario='unknown' if intrinsic is None else 'positive',
            covers=("named:unique:Andariel's Visage",),
            expected={'assessment': IsPartialDict(trade_tier=IsPartialDict(**proof))},
            report_contains=(f'item roll: {intrinsic} (25-30), sockets: +{total - intrinsic}',)
            if intrinsic is not None
            else (),
            report_absent=('item roll:',) if intrinsic is None else (),
            evidence=('third-parties/d2data/json/uniqueitems.json:/345', 'third-parties/d2data/json/gems.json'),
        )


CASES = tuple(cases())
