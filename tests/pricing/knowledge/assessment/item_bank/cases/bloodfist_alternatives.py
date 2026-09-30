"""Bloodfist defenses serve every listed use; attack bonuses have different recipients."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


BUILDS = (
    ('dream-paladin', 'Paladin', 3, ('93:0', '21:0')),
    ('fissure-druid', 'Druid', 3, ()),
    ('fist-of-the-heavens-paladin', 'Paladin', 2, ()),
    ('smite-paladin', 'Paladin', 0, ('93:0',)),
)
RAW = ((21, 0, 5), (7, 0, 40 * 256), (99, 0, 30), (16, 0, 10), (93, 0, 10))
ITEM = Item('Heavy Gloves', 'unique', 'Bloodfist', RAW, named_table_id=103)


def cases():
    for build, player_class, slot, attack_stats in BUILDS:
        role = build + '-bloodfist-caster-survival-alternative'
        config = role + '-stats'
        context = {'player_class': player_class}
        for label, item, ctx, truth in (
            ('minimum-enhanced-defense', ITEM, context, 'true'),
            ('maximum-enhanced-defense', replace(ITEM, raw_stats=(*RAW[:3], (16, 0, 20), RAW[4])), context, 'true'),
            ('exceptional-base', replace(ITEM, base='Sharkskin Gloves'), context, 'true'),
            ('elite-base', replace(ITEM, base='Vampirebone Gloves'), context, 'true'),
            ('ethereal', replace(ITEM, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown'),
            ('invalid-socket', replace(ITEM, sockets=1, raw_stats=(*RAW, (194, 0, 1))), context, 'false'),
            ('unknown-sockets', replace(ITEM, sockets=None, socket_contents='unknown'), context, 'unknown'),
            ('wrong-class', ITEM, {'player_class': 'Amazon'}, 'false'),
            ('unknown-class', ITEM, {}, 'unknown'),
            ('unidentified', replace(ITEM, identified=False), context, 'false'),
        ):
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config))
                            for key in ('7:0', '99:0', *attack_stats)
                        }
                    )
                )
            yield Case(
                id=f'bloodfist-alternatives/{build}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                absent_stat_configurations={key: (config,) for key in ('93:0', '21:0') if key not in attack_stats},
                report_contains=('Bloodfist', 'Trade tier:', '+40 to Life', '30% Faster Hit Recovery', '(10-20%)')
                if active
                else (),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/slots/Gloves/{slot}',
                    'third-parties/d2data/json/uniqueitems.json:/103',
                ),
            )


CASES = tuple(cases())
