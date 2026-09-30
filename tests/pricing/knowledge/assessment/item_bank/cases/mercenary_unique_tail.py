"""Fire Iron Wolf pre-fight support and Fissure starter survival alternatives."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


FIRE = SocketItem(
    'Jewel',
    ((48, 0, 17), (49, 0, 45), (333, 0, 3), (329, 0, 3), (197, 56 * 64 + 31, 100)),
    complete=True,
    name='Rainbow Facet',
    unique_table_id=394,
)
SUPPORT = (
    ('hexfire', 'Shamshir', 'Hexfire', ((126, 1, 3), (329, 0, 3), (333, 0, 3)), ('126:1', '329:0'), 156),
    (
        'ormus',
        'Dusk Shroud',
        "Ormus' Robes",
        ((105, 0, 20), (329, 0, 13), (330, 0, 10), (331, 0, 10), (333, 0, 3)),
        ('329:0',),
        358,
    ),
    (
        'lidless',
        'Grim Shield',
        'Lidless Wall',
        ((127, 0, 1), (105, 0, 20), (329, 0, 3), (333, 0, 3)),
        ('127:0', '329:0'),
        230,
    ),
)


def support_cases():
    context = {'player_class': 'Assassin', 'mercenary_type': 'Act 3 Fire'}
    for slug, base, name, stats, priorities, native_id in SUPPORT:
        role = 'dragon-talon-budget-' + slug + '-merc'
        config = role + '-stats'
        item = Item(base, 'unique', name, stats, sockets=1, socket_contents='filled', socket_items=(FIRE,))
        for label, observed, ctx, scenario, failed in (
            ('minimum-fire-facet', item, context, 'positive', None),
            ('ethereal', replace(item, ethereal=True), context, 'positive', None),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'positive', None),
            ('wrong-class', item, {**context, 'player_class': 'Druid'}, 'negative', -1),
            ('unknown-class', item, {'mercenary_type': 'Act 3 Fire'}, 'unknown', -1),
            (
                'unnamed-jewel',
                replace(item, socket_items=(replace(FIRE, name=None, unique_table_id=None),)),
                context,
                'negative',
                1,
            ),
            *(
                (
                    f'outside-{stat}-{value}',
                    replace(
                        item,
                        socket_items=(
                            replace(
                                FIRE,
                                raw_stats=tuple(
                                    (sid, layer, value if sid == stat else n) for sid, layer, n in FIRE.raw_stats
                                ),
                            ),
                        ),
                    ),
                    context,
                    'negative',
                    1,
                )
                for stat in (329, 333)
                for value in (2, 6)
            ),
            ('wrong-mercenary', item, {**context, 'mercenary_type': 'Act 3 Lightning'}, 'negative', 0),
            ('unknown-mercenary', item, {'player_class': 'Assassin'}, 'unknown', 0),
            (
                'wrong-jewel',
                replace(item, socket_items=(SocketItem('Jewel', ((93, 0, 15),), True),)),
                context,
                'negative',
                1,
            ),
            ('unread-jewel', replace(item, socket_items=()), context, 'unknown', 1),
            ('partial-jewel', replace(item, socket_items=(replace(FIRE, complete=False),)), context, 'unknown', 1),
            ('empty-socket', replace(item, socket_items=(), socket_contents='empty'), context, 'negative', 1),
        ):
            dependencies = [IsPartialDict(status='true'), IsPartialDict(status='true')]
            if failed is not None and failed >= 0:
                dependencies[failed] = IsPartialDict(status='unknown' if scenario == 'unknown' else 'false')
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        side='merc',
                        rule_trace=IsPartialDict(
                            truth=('unknown' if scenario == 'unknown' else 'false') if failed == -1 else 'true'
                        ),
                        dependencies=dependencies,
                    )
                )
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(config)) for key in priorities}
                    )
                )
            yield Case(
                id=f'merc-unique-tail/{slug}/{label}',
                item=observed,
                context=ctx,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                absent_stat_configurations=dict.fromkeys(('333:0', '105:0', '330:0', '331:0'), (config,)),
                report_contains=(
                    name,
                    'Trade tier:',
                    *(
                        (('Check' if scenario == 'unknown' else 'Needs') + ': Socket a Fire Rainbow Facet',)
                        if failed == 1
                        else ()
                    ),
                ),
                evidence=(
                    'pricing/data/wp-a-builds.json:/dragon-talon-assassin/variants/0',
                    f'third-parties/d2data/json/uniqueitems.json:/{native_id}',
                    'third-parties/d2data/json/uniqueitems.json:/394',
                ),
            )


def duriel_cases():
    role = 'fissure-starter-merc-duriel'
    config = role + '-stats'
    item = Item(
        'Cuirass',
        'unique',
        "Duriel's Shell",
        (
            (16, 0, 160),
            (0, 0, 15),
            (214, 0, 10),
            (216, 0, 8 * 256),
            (153, 0, 1),
            (39, 0, 20),
            (41, 0, 20),
            (43, 0, 50),
            (45, 0, 20),
        ),
    )
    for label, observed, context, scenario in (
        ('minimum-defense', item, {'player_class': 'Druid'}, 'positive'),
        ('ethereal', replace(item, ethereal=True), {'player_class': 'Druid'}, 'positive'),
        ('upgraded', replace(item, base='Great Hauberk'), {'player_class': 'Druid'}, 'positive'),
        ('wrong-class', item, {'player_class': 'Sorceress'}, 'negative'),
        ('unknown-class', item, {}, 'unknown'),
    ):
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
                    {
                        key: IsPartialDict(configuration_ids=Contains(config))
                        for key in ('153:0', '39:0', '41:0', '43:0', '45:0', '216:0', '0:0')
                    }
                )
            )
        yield Case(
            id=f'merc-unique-tail/duriel/{label}',
            item=observed,
            context=context,
            scenario=scenario,
            covers=(role,),
            expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
            absent_configurations=() if scenario == 'positive' else (config,),
            absent_stat_configurations={'16:0': (config,), '214:0': (config,)},
            report_contains=("Duriel's Shell", 'Trade tier:', '160-200'),
            evidence=(
                'pricing/data/wp-a-builds.json:/fissure-druid/variants/0',
                'third-parties/d2data/json/uniqueitems.json:/216',
            ),
        )


CASES = (*support_cases(), *duriel_cases())
