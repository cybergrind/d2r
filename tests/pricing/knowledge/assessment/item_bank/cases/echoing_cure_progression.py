"""Progression Cure supplies Cleansing independently of weapon and ethereal damage."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'echoing-progression-cure-merc'
CONTEXT = {'player_class': 'Warlock', 'mercenary_type': 'Act 2 Prayer', 'mercenary_items': []}


def cases():
    for quality in ('normal', 'superior', 'low_quality'):
        item = Item(
            'Grand Crown',
            quality,
            'Cure',
            ((151, 109, 1), (194, 0, 3)),
            ethereal=True,
            sockets=3,
            socket_contents='filled',
            runeword='Cure',
            socket_items=tuple(SocketItem(n) for n in ('Shael Rune', 'Io Rune', 'Tal Rune')),
        )
        rows = [
            ('without-insight', item, CONTEXT, True),
            ('with-insight', item, {**CONTEXT, 'mercenary_items': ['Insight']}, True),
            ('unknown-companions', item, {k: v for k, v in CONTEXT.items() if k != 'mercenary_items'}, True),
            ('nonethereal', replace(item, ethereal=False), CONTEXT, True),
            ('unknown-ethereal', replace(item, ethereal=None), CONTEXT, True),
            ('alternative-bone-visage', replace(item, base='Bone Visage'), CONTEXT, True),
            ('wrong-mercenary', item, {**CONTEXT, 'mercenary_type': 'Act 2 Might'}, False),
            ('unknown-mercenary', item, {**CONTEXT, 'mercenary_type': None}, False),
            ('wrong-class', item, {**CONTEXT, 'player_class': 'Paladin'}, False),
            ('impossible-cap', replace(item, base='Cap'), CONTEXT, False),
            ('illegal-shield', replace(item, base='Monarch'), CONTEXT, False),
            ('unidentified', replace(item, identified=False), CONTEXT, False),
        ]
        for label, candidate, context, usable in rows:
            yield Case(
                id=f'echoing/cure-progression/{quality}/{label}',
                item=candidate,
                context=context,
                covers=(ROLE,),
                scenario='unknown' if label.startswith('unknown') else 'positive' if usable else 'negative',
                expected={
                    'assessment': IsPartialDict(
                        stat_evaluation=IsPartialDict(
                            annotations=IsPartialDict(
                                {'151:109': IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))}
                            )
                        )
                    )
                }
                if usable
                else {},
                absent_configurations=() if usable else (ROLE + '-stats',),
                evidence=(
                    'pricing/raw/mr/guides__echoing-strike-warlock-guide.html:/sections/43',
                    'third-parties/d2data/json/runes.json:/Cure',
                ),
            )


CASES = tuple(cases())
