"""Cleansing's own benefits do not prove the full Prayer/Insight healing setup."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


def cases():
    for variant in (1, 2):
        role = f'echoing-strike-warlock-guide-{variant}-merc-cure'
        context = {'player_class': 'Warlock', 'mercenary_type': 'Act 2 Prayer', 'mercenary_items': []}
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                'Grand Crown',
                quality,
                'Cure',
                ((151, 109, 1), (45, 0, 40), (110, 0, 50), (76, 0, 5), (99, 0, 20), (194, 0, 3)),
                ethereal=True,
                sockets=3,
                socket_contents='filled',
                runeword='Cure',
                socket_items=tuple(SocketItem(n) for n in ('Shael Rune', 'Io Rune', 'Tal Rune')),
            )
            rows = [
                ('without-insight', item, context, True),
                ('with-insight', item, {**context, 'mercenary_items': ['Insight']}, True),
                ('unknown-weapon', item, {k: v for k, v in context.items() if k != 'mercenary_items'}, True),
                ('wrong-mercenary', item, {**context, 'mercenary_type': 'Act 2 Might'}, False),
                ('unknown-mercenary', item, {**context, 'mercenary_type': None}, False),
                ('wrong-class', item, {**context, 'player_class': 'Paladin'}, False),
                ('nonethereal', replace(item, ethereal=False), context, False),
                ('unknown-ethereal', replace(item, ethereal=None), context, False),
                ('wrong-base', replace(item, base='Crown'), context, False),
            ]
            for label, candidate, ctx, usable in rows:
                yield Case(
                    id=f'echoing/cure/{variant}/{quality}/{label}',
                    item=candidate,
                    context=ctx,
                    covers=(role,),
                    scenario='unknown' if label.startswith('unknown') else 'positive' if usable else 'negative',
                    expected={
                        'assessment': IsPartialDict(
                            stat_evaluation=IsPartialDict(
                                annotations=IsPartialDict(
                                    {
                                        k: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                                        for k in ('151:109', '45:0', '110:0', '76:0', '99:0')
                                    }
                                )
                            )
                        )
                    }
                    if usable
                    else {},
                    absent_configurations=() if usable else (role + '-stats',),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/echoing-strike-warlock-guide/variants/{variant}',
                        'third-parties/d2data/json/runes.json:/Cure',
                    ),
                )


CASES = tuple(cases())
