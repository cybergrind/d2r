"""Distinct Echoing mercenary weapon uses, authored from the three guide setups."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


USES = (
    (0, 'Partizan', 'Act 2 Blessed Aim'),
    (1, 'Giant Thresher', 'Act 2 Prayer'),
    (2, 'Giant Thresher', 'Act 2 Prayer'),
)


def cases():
    for variant, base, mercenary in USES:
        role = f'echoing-{variant}-insight-merc'
        context = {'player_class': 'Warlock', 'mercenary_type': mercenary, 'mercenary_items': ['Cure']}
        item = Item(
            base,
            'normal',
            'Insight',
            ((151, 120, 12), (17, 0, 200), (18, 0, 200), (97, 9, 1), (119, 0, 180), (194, 0, 4)),
            ethereal=True,
            sockets=4,
            socket_contents='filled',
            runeword='Insight',
            socket_items=tuple(SocketItem(n) for n in ('Ral Rune', 'Tir Rune', 'Tal Rune', 'Sol Rune')),
        )
        rows = [(q, replace(item, rarity=q), context, True) for q in ('normal', 'superior', 'low_quality')]
        rows.extend(
            [
                ('wrong-aura', item, {**context, 'mercenary_type': 'Act 2 Might'}, False),
                ('unknown-aura', item, {**context, 'mercenary_type': None}, False),
                ('wrong-class', item, {**context, 'player_class': 'Paladin'}, False),
                ('unknown-class', item, {**context, 'player_class': None}, False),
                ('wrong-base', replace(item, base='Bardiche'), context, False),
                ('nonethereal', replace(item, ethereal=False), context, False),
                ('unknown-ethereal', replace(item, ethereal=None), context, False),
            ]
        )
        if variant:
            rows.extend(
                [
                    ('missing-cure', item, {**context, 'mercenary_items': []}, False),
                    ('player-cure', item, {**context, 'mercenary_items': [], 'player_items': ['Cure']}, False),
                    ('unknown-cure', item, {k: v for k, v in context.items() if k != 'mercenary_items'}, False),
                ]
            )
        for label, candidate, ctx, usable in rows:
            case = Case(
                id=f'echoing/insight/{variant}/{label}',
                item=candidate,
                context=ctx,
                covers=(role,),
                scenario='positive' if usable else 'unknown' if label.startswith('unknown') else 'negative',
                expected={
                    'assessment': IsPartialDict(
                        stat_evaluation=IsPartialDict(
                            annotations=IsPartialDict(
                                {
                                    k: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                                    for k in ('151:120', '17:0', '18:0', '97:9', '119:0')
                                }
                            )
                        )
                    )
                }
                if usable
                else {},
                absent_configurations=() if usable else (role + '-stats',),
                report_contains=('Setup: Cure in the mercenary setup',) if usable and variant else (),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/echoing-strike-warlock-guide/variants/{variant}',
                    'third-parties/d2data/json/runes.json:/Insight',
                ),
            )
            yield case
            if not usable:
                for quality in ('superior', 'low_quality'):
                    yield replace(case, id=case.id + '/' + quality, item=replace(candidate, rarity=quality))


CASES = tuple(cases())
