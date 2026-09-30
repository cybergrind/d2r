"""Cure's intrinsic support, without inferring Prayer or an Insight weapon."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


USES = (
    ('nova-sorceress-guide', 1, 'Diadem', 'Act 2 Might'),
    ('nova-sorceress-guide', 2, 'Diadem', 'Act 2 Might'),
    ('nova-sorceress-guide', 3, 'Diadem', 'Act 2 Might'),
    ('enchant-sorceress', 1, 'Demonhead', 'Act 2 Prayer'),
    ('enchant-sorceress', 2, 'Demonhead', 'Act 2 Prayer'),
)


def cases():
    for build, variant, base, merc in USES:
        for quality in ('normal', 'superior', 'low_quality'):
            role = f'{build}-{variant}-merc-cure'
            config = role + '-stats'
            item = Item(
                base,
                quality,
                'Cure',
                (
                    (151, 109, 1),
                    (45, 0, 40),
                    (110, 0, 50),
                    (76, 0, 5),
                    (99, 0, 20),
                    (16, 0, 75),
                    (3, 0, 10),
                    (194, 0, 3),
                ),
                ethereal=True,
                sockets=3,
                socket_contents='filled',
                runeword='Cure',
                socket_items=tuple(SocketItem(name) for name in ('Shael Rune', 'Io Rune', 'Tal Rune')),
            )
            context = {'player_class': 'Sorceress', 'mercenary_type': merc, 'mercenary_items': []}
            examples = [
                ('no-insight', item, context, 'true'),
                (
                    'maximum-rolls',
                    replace(
                        item,
                        raw_stats=tuple(
                            (stat, layer, 60 if stat == 45 else 100 if stat == 16 else value)
                            for stat, layer, value in item.raw_stats
                        ),
                    ),
                    context,
                    'true',
                ),
                ('unknown-weapon', item, {k: v for k, v in context.items() if k != 'mercenary_items'}, 'true'),
                ('wrong-mercenary', item, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'false'),
                ('unknown-mercenary', item, {k: v for k, v in context.items() if k != 'mercenary_type'}, 'unknown'),
                ('wrong-class', item, {**context, 'player_class': 'Paladin'}, 'false'),
                ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown'),
                ('nonethereal', replace(item, ethereal=False), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('wrong-base', replace(item, base='Crown'), context, 'false'),
            ]
            if build == 'nova-sorceress-guide':
                examples.append(('holy-freeze', item, {**context, 'mercenary_type': 'Act 2 Holy Freeze'}, 'true'))
                examples.append(('uncited-prayer', item, {**context, 'mercenary_type': 'Act 2 Prayer'}, 'false'))
            for label, candidate, ctx, truth in examples:
                expected = {
                    'roles': Contains(IsPartialDict(id=role, side='merc', rule_trace=IsPartialDict(truth=truth)))
                }
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(config))
                                for key in ('151:109', '45:0', '110:0', '76:0', '99:0')
                            }
                        )
                    )
                yield Case(
                    id=f'sorceress-cure/{role}/{quality}/{label}',
                    item=candidate,
                    context=ctx,
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    absent_configurations=() if truth == 'true' else (config,),
                    absent_stat_configurations=dict.fromkeys(('16:0', '3:0', '74:0', '60:0'), (config,)),
                    report_contains=('Cure', 'Level 1 Cleansing Aura', 'Shael, Io, Tal', '20% Faster Hit Recovery'),
                    report_absent=('Replenish Life', 'Life stolen per hit'),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/variants/{variant}',
                        'third-parties/d2data/json/runes.json:/Cure',
                        'third-parties/d2data/json/gems.json:/r13',
                        'third-parties/d2data/json/gems.json:/r16',
                        'third-parties/d2data/json/gems.json:/r07',
                    ),
                )


CASES = tuple(cases())
