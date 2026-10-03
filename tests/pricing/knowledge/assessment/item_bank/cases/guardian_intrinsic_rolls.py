"""Guardian native ED, including ordinary rolls beneath the premium predicate."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.guardian_angel_mercenaries import ITEM
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem


def cases():
    for native, tier in ((180, 'low'), (187, 'low'), (200, 'high')):
        for rune, bonus in (('Pul Rune', 30), ('Ral Rune', 0)):
            item = replace(
                ITEM,
                ethereal=True,
                complete=True,
                sockets=1,
                socket_contents='filled',
                socket_items=(SocketItem(rune),),
                raw_stats=tuple((s, p, native + bonus if s == 16 else v) for s, p, v in ITEM.raw_stats),
            )
            yield Case(
                id=f'guardian-intrinsic/{native}/{rune}',
                item=item,
                context={},
                scenario='positive',
                covers=('named:unique:Guardian Angel',),
                expected={
                    'assessment': IsPartialDict(
                        trade_tier=IsPartialDict(
                            tier=tier,
                            intrinsic_rolls=IsPartialDict(
                                {
                                    '16:0': {
                                        'observed': native + bonus,
                                        'socket': bonus,
                                        'intrinsic': native,
                                    }
                                }
                            ),
                        )
                    )
                },
                report_contains=(f'item roll: {native} (180-200), sockets: +{bonus}',),
                evidence=('third-parties/d2data/json/uniqueitems.json:/218', 'third-parties/d2data/json/gems.json'),
            )


CASES = tuple(cases())
