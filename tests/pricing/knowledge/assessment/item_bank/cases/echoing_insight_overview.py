"""General mana support is independent of the optional Cure healing combination."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'echoing-overview-insight-merc'
CONTEXT = {'player_class': 'Warlock', 'mercenary_type': 'Act 2 Prayer', 'mercenary_items': []}


def cases():
    for quality in ('normal', 'superior', 'low_quality'):
        item = Item(
            'Giant Thresher',
            quality,
            'Insight',
            ((151, 120, 12), (194, 0, 4)),
            ethereal=True,
            sockets=4,
            socket_contents='filled',
            runeword='Insight',
            socket_items=tuple(SocketItem(n) for n in ('Ral Rune', 'Tir Rune', 'Tal Rune', 'Sol Rune')),
        )
        rows = [
            ('without-cure', item, CONTEXT, True),
            ('with-cure', item, {**CONTEXT, 'mercenary_items': ['Cure']}, True),
            ('unknown-companions', item, {k: v for k, v in CONTEXT.items() if k != 'mercenary_items'}, True),
            ('nonethereal', replace(item, ethereal=False), CONTEXT, True),
            ('unknown-ethereal', replace(item, ethereal=None), CONTEXT, True),
            ('alternative-bill', replace(item, base='Bill'), CONTEXT, True),
            ('wrong-mercenary', item, {**CONTEXT, 'mercenary_type': 'Act 2 Might'}, False),
            ('unknown-mercenary', item, {**CONTEXT, 'mercenary_type': None}, False),
            ('wrong-class', item, {**CONTEXT, 'player_class': 'Paladin'}, False),
            ('impossible-bardiche', replace(item, base='Bardiche'), CONTEXT, False),
            ('illegal-spear', replace(item, base='War Pike'), CONTEXT, False),
            ('unidentified', replace(item, identified=False), CONTEXT, False),
        ]
        for label, candidate, context, usable in rows:
            yield Case(
                id=f'echoing/insight-overview/{quality}/{label}',
                item=candidate,
                context=context,
                covers=(ROLE,),
                scenario='unknown' if label.startswith('unknown') else 'positive' if usable else 'negative',
                expected={
                    'assessment': IsPartialDict(
                        stat_evaluation=IsPartialDict(
                            annotations=IsPartialDict(
                                {'151:120': IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))}
                            )
                        )
                    )
                }
                if usable
                else {},
                absent_configurations=() if usable else (ROLE + '-stats',),
                evidence=(
                    'pricing/raw/mr/guides__echoing-strike-warlock-guide.html:/sections/42',
                    'third-parties/d2data/json/runes.json:/Insight',
                ),
            )


CASES = tuple(cases())
