"""Angelic attack-rating pairs, including builds that use two rings."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = (
    ('double-throw-barbarian-guide', 'Barbarian', 2),
    ('strafe-amazon', 'Amazon', 2),
    ('echoing-strike-warlock-guide', 'Warlock', 1),
    ('dragon-talon-assassin', 'Assassin', 1),
    ('berserk-barbarian', 'Barbarian', 1),
    ('zeal-paladin', 'Paladin', 1),
)
ITEMS = (
    ('ring', Item('Ring', 'set', 'Angelic Halo', ((7, 0, 20 << 8), (74, 0, 6), (224, 0, 24)))),
    ('amulet', Item('Amulet', 'set', 'Angelic Wings', ((114, 0, 20), (7, 0, 75 << 8)))),
)


def cases():
    result = []
    for build, klass, ring_count in USES:
        for suffix, item in ITEMS:
            role = build + '-angelic-' + suffix
            config = role + '-stats'
            has_stats = suffix == 'ring' or build == 'zeal-paladin'
            full = ['Angelic Wings'] + ['Angelic Halo'] * ring_count
            for scenario, context in (
                ('positive', {'player_class': klass, 'player_items': full}),
                ('negative', {'player_class': klass, 'player_items': [item.name] * 2, 'mercenary_items': full}),
                ('unknown', {'player_class': klass}),
            ):
                role_expected = IsPartialDict(
                    id=role,
                    build=build,
                    dependencies=Contains(
                        IsPartialDict(
                            status={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario],
                        )
                    ),
                )
                expected = {
                    'roles': Contains(role_expected),
                    'trade_tier': IsPartialDict(status='reviewed', tier='low'),
                }
                if scenario == 'positive' and has_stats:
                    keys = ('224:0',) if suffix == 'ring' else ('7:0', '114:0')
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(config)) for key in keys}
                        )
                    )
                case = Case(
                    id=f'angelic/{build}/{suffix}/{scenario}',
                    item=item,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role, f'named:set:{item.name}'),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' and has_stats else (config,),
                    absent_stat_configurations={'224:0': (config,)} if suffix == 'amulet' else {},
                    report_contains=(item.name, 'Trade tier: low'),
                    evidence=(
                        'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/sections/32'
                        if build == 'zeal-paladin'
                        else f'pricing/data/wp-a-variants/{build}.json:/variants/0',
                        f'third-parties/d2data/json/setitems.json:/{item.name}',
                        f'pricing/knowledge/assessment/rules/named_tier_reviews.json:/rows/set:{item.name}',
                    ),
                )
                result.append(case)
                if scenario == 'positive' and ring_count == 2:
                    result.append(
                        replace(
                            case,
                            id=f'angelic/{build}/{suffix}/missing-second-ring',
                            scenario='negative',
                            context={'player_class': klass, 'player_items': ['Angelic Wings', 'Angelic Halo']},
                            expected={
                                'assessment': IsPartialDict(
                                    roles=Contains(
                                        IsPartialDict(
                                            id=role,
                                            dependencies=Contains(IsPartialDict(status='false')),
                                        )
                                    )
                                )
                            },
                            absent_configurations=(config,),
                        )
                    )
                if scenario == 'positive' and suffix == 'ring':
                    result.append(
                        replace(
                            case,
                            id=f'angelic/{build}/{suffix}/uncaptured-ar',
                            scenario='negative',
                            item=replace(item, raw_stats=((7, 0, 20 << 8), (74, 0, 6))),
                            expected={'assessment': IsPartialDict(roles=Contains(role_expected))},
                            absent_configurations=() if build == 'zeal-paladin' else (config,),
                            absent_stat_configurations={'224:0': (config,)},
                        )
                    )
    for case in tuple(result):
        if case.scenario != 'positive' or not case.id.startswith('angelic/zeal-paladin/'):
            continue
        role = case.covers[0]
        config = role + '-stats'
        result.append(
            replace(
                case,
                id=case.id.removesuffix('/positive') + '/wrong-class',
                scenario='negative',
                context={**case.context, 'player_class': 'Sorceress'},
                expected={
                    'assessment': IsPartialDict(
                        roles=Contains(
                            IsPartialDict(
                                id=role,
                                rule_trace=IsPartialDict(truth='false'),
                            )
                        )
                    )
                },
                absent_configurations=(config,),
            )
        )
        # Three equipped objects are only two distinct pieces when rings repeat.
        third_bonus = (80, 0, 50) if case.item.base == 'Ring' else (127, 0, 1)
        result.append(
            replace(
                case,
                id=case.id.removesuffix('/positive') + '/two-rings-not-three-pieces',
                scenario='negative',
                context={**case.context, 'player_items': ['Angelic Wings', 'Angelic Halo', 'Angelic Halo']},
                item=replace(case.item, raw_stats=(*case.item.raw_stats, third_bonus)),
                absent_stat_configurations={**case.absent_stat_configurations, f'{third_bonus[0]}:0': (config,)},
            )
        )
        if case.item.base == 'Amulet':
            result.append(
                replace(
                    case,
                    id=case.id.removesuffix('/positive') + '/uncaptured-life',
                    scenario='negative',
                    item=replace(case.item, raw_stats=((114, 0, 20),)),
                    expected={
                        'assessment': IsPartialDict(
                            roles=Contains(IsPartialDict(id=role)),
                            stat_evaluation=IsPartialDict(
                                annotations=IsPartialDict(
                                    {
                                        '114:0': IsPartialDict(configuration_ids=Contains(config)),
                                    }
                                )
                            ),
                        )
                    },
                    absent_stat_configurations={'7:0': (config,), '224:0': (config,)},
                )
            )
    return tuple(result)


CASES = cases()
