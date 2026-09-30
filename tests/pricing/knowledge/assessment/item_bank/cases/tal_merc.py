"""Tal mercenary leech and gold-farming sockets use the actual child payload."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


HELM = Item(
    'Death Mask',
    'set',
    "Tal Rasha's Horadric Crest",
    ((60, 0, 10), (62, 0, 10), (7, 0, 60 << 8), (9, 0, 30 << 8), (39, 0, 15), (41, 0, 15), (43, 0, 15), (45, 0, 15)),
)
GOLD = replace(
    HELM,
    raw_stats=(*HELM.raw_stats, (79, 0, 30), (194, 0, 1)),
    sockets=1,
    socket_contents='filled',
    socket_items=(SocketItem('Jewel', ((79, 0, 30),), complete=True),),
)


def cases():
    result = []
    for role, build, item in (
        ('summoner-starter-tal-merc', 'summoner-necromancer-guide', HELM),
        ('gold-find-budget-tal-merc', 'gold-find-barbarian', GOLD),
    ):
        scenarios = [
            ('positive', item, {'mercenary_type': 'Act 2 Might'}, True),
            ('negative', item, {'mercenary_type': 'Act 3 Fire'}, False),
            ('unknown', item, {}, False),
        ]
        if item is GOLD:
            scenarios += [
                ('aggregate-only', replace(item, socket_items=()), {'mercenary_type': 'Act 2 Might'}, False),
                (
                    'non-gold-jewel',
                    replace(item, socket_items=(SocketItem('Jewel', ((0, 0, 1),), complete=True),)),
                    {'mercenary_type': 'Act 2 Might'},
                    False,
                ),
                (
                    'unknown-jewel',
                    replace(item, socket_items=(SocketItem('Jewel', ((79, 0, 30),), complete=False),)),
                    {'mercenary_type': 'Act 2 Might'},
                    False,
                ),
            ]
        for scenario, candidate, context, active in scenarios:
            config = role + '-stats'
            assessment = {'roles': Contains(IsPartialDict(id=role, build=build))}
            if active:
                keys = ('60:0', '7:0', '39:0') + (('79:0',) if item is GOLD else ())
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            result.append(
                Case(
                    id=f'tal-merc/{role}/{scenario}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**assessment)},
                    covers=(role,),
                    scenario=scenario if scenario in ('positive', 'negative', 'unknown') else 'negative',
                    absent_configurations=() if active else (config,),
                    absent_stat_configurations=dict.fromkeys(('62:0', '9:0'), (config,)),
                    report_contains=("Tal Rasha's Horadric Crest", 'Trade tier:'),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/variants/0/merc/Helmet',
                        "third-parties/d2data/json/setitems.json:/Tal Rasha's Horadric Crest",
                    ),
                )
            )
    return tuple(result)


CASES = cases()
