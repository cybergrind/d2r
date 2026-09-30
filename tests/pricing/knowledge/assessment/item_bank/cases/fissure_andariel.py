"""Fissure's actual IAS/damage jewel and mercenary companion requirements."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.summoner_andariel import CHILD, ITEM
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem


CONTEXT = {'player_class': 'Druid', 'mercenary_type': 'Act 2 Might', 'mercenary_items': ['Infinity', 'Fortitude']}


def socketed(stats):
    child = SocketItem('Jewel', stats, True)
    native = tuple(row for row in ITEM.raw_stats if row[0] not in (17, 18, 93, 39))
    totals = {93: 20, 39: -30}
    for stat, _, value in stats:
        totals[stat] = totals.get(stat, 0) + value
    return replace(ITEM, socket_items=(child,), raw_stats=(*native, *((s, 0, v) for s, v in totals.items())))


def cases():
    examples = (
        ('minimum-ruby', ITEM, CONTEXT, 'positive', None),
        ('perfect-ruby', socketed(((93, 0, 15), (17, 0, 40), (18, 0, 40))), CONTEXT, 'positive', None),
        ('holy-freeze', ITEM, {**CONTEXT, 'mercenary_type': 'Act 2 Holy Freeze'}, 'positive', None),
        ('nonethereal', replace(ITEM, ethereal=False), CONTEXT, 'positive', None),
        ('unknown-ethereal', replace(ITEM, ethereal=None), CONTEXT, 'positive', None),
        ('fire-ruby', socketed(((93, 0, 15), (39, 0, 30))), CONTEXT, 'negative', 3),
        ('below-ruby', socketed(((93, 0, 15), (17, 0, 30), (18, 0, 30))), CONTEXT, 'negative', 3),
        ('invalid-ed', socketed(((93, 0, 15), (17, 0, 41), (18, 0, 41))), CONTEXT, 'negative', 3),
        ('invalid-ias', socketed(((93, 0, 16), (17, 0, 40), (18, 0, 40))), CONTEXT, 'negative', 3),
        ('missing-max-ed', socketed(((93, 0, 15), (17, 0, 31))), CONTEXT, 'negative', 3),
        ('unread-child', replace(ITEM, socket_items=()), CONTEXT, 'unknown', 3),
        ('partial-child', replace(ITEM, socket_items=(replace(CHILD, complete=False),)), CONTEXT, 'unknown', 3),
        ('empty-socket', replace(ITEM, socket_contents='empty', socket_items=()), CONTEXT, 'negative', 3),
        ('wrong-mercenary', ITEM, {**CONTEXT, 'mercenary_type': 'Act 5 Frenzy'}, 'negative', 0),
        ('unknown-mercenary', ITEM, {k: v for k, v in CONTEXT.items() if k != 'mercenary_type'}, 'unknown', 0),
        ('missing-infinity', ITEM, {**CONTEXT, 'mercenary_items': ['Fortitude']}, 'negative', 1),
        ('missing-fortitude', ITEM, {**CONTEXT, 'mercenary_items': ['Infinity']}, 'negative', 2),
        ('unknown-companions', ITEM, {k: v for k, v in CONTEXT.items() if k != 'mercenary_items'}, 'unknown', 1),
        ('wrong-class', ITEM, {**CONTEXT, 'player_class': 'Sorceress'}, 'negative', 'class'),
        ('unknown-class', ITEM, {k: v for k, v in CONTEXT.items() if k != 'player_class'}, 'unknown', 'class'),
    )
    for variant, source_index in (('standard', 1), ('magic-find', 2)):
        role = f'fissure-merc-{variant}-andariel'
        config = role + '-stats'
        for label, item, context, scenario, failed in examples:
            truth = 'unknown' if scenario == 'unknown' else 'false'
            role_result = {
                'id': role,
                'side': 'merc',
                'rule_trace': IsPartialDict(truth=truth if failed == 'class' else 'true'),
            }
            if failed != 'class':
                dependencies = [IsPartialDict(status='true') for _ in range(4)]
                if failed is not None:
                    dependencies[failed] = IsPartialDict(status=truth)
                if label == 'unknown-companions':
                    dependencies[2] = IsPartialDict(status='unknown')
                role_result['dependencies'] = dependencies
            expected = {'roles': Contains(IsPartialDict(**role_result)), 'trade_tier': IsPartialDict(status='reviewed')}
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config))
                            for key in ('60:0', '0:0', '93:0', '17:0', '18:0')
                        }
                    )
                )
            yield Case(
                id=f'fissure-andariel/{variant}/{label}',
                item=item,
                context=context,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                absent_stat_configurations={'39:0': (config,), '16:0': (config,)},
                report_contains=("Andariel's Visage", 'Trade tier:'),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/fissure-druid/variants/{source_index}',
                    'third-parties/d2data/json/uniqueitems.json:/345',
                    'third-parties/d2data/json/magicprefix.json:/198',
                ),
            )


CASES = tuple(cases())
