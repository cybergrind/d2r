"""Native Gaze alternatives for Smite and Strafe, separate from socket readiness."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.vampire_gaze_setups import BASE
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem


SPECS = (
    ('smite-paladin-1-merc-gaze-native', 'Paladin', '/smite-paladin/variants/1', True),
    ('smite-paladin-2-merc-gaze-native', 'Paladin', '/smite-paladin/variants/2', True),
    ('strafe-amazon-1-merc-gaze-native', 'Amazon', '/strafe-amazon/variants/1', False),
    ('strafe-amazon-2-merc-gaze-native', 'Amazon', '/strafe-amazon/variants/2', False),
)


def cases():
    item = replace(BASE, ethereal=True)
    for role, klass, source, require_ethereal in SPECS:
        context = {'player_class': klass, 'mercenary_type': 'Act 2 Might'}
        examples = (
            ('minimum-native-rolls', item, context, 'positive'),
            ('nonethereal', replace(item, ethereal=False), context, 'negative' if require_ethereal else 'positive'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('wrong-mercenary', item, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'negative'),
            ('unknown-mercenary', item, {'player_class': klass}, 'unknown'),
            ('wrong-class', item, {**context, 'player_class': 'Sorceress'}, 'negative'),
            ('unknown-class', item, {'mercenary_type': 'Act 2 Might'}, 'unknown'),
            ('different-upgraded-base', replace(item, base='Bone Visage'), context, 'negative'),
            (
                'linked-ias-not-native',
                replace(
                    item,
                    sockets=1,
                    socket_contents='filled',
                    raw_stats=(*item.raw_stats, (93, 0, 15), (194, 0, 1)),
                    socket_items=(SocketItem('Jewel', ((93, 0, 15),), complete=True),),
                ),
                context,
                'positive',
            ),
        )
        for label, candidate, ctx, scenario in examples:
            config = role + '-stats'
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        side='merc',
                        rule_trace=IsPartialDict(
                            truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                        ),
                    )
                )
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(config)) for key in ('60:0', '36:0', '35:0')}
                    )
                )
            yield Case(
                id=f'vampire-gaze-native/{role}/{label}',
                item=candidate,
                context=ctx,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                absent_stat_configurations={'62:0': (config,), '93:0': (config,)},
                report_contains=('Vampire Gaze', 'Trade tier:'),
                evidence=('pricing/data/wp-a-builds.json:' + source, 'third-parties/d2data/json/uniqueitems.json:/208'),
            )


CASES = tuple(cases())
