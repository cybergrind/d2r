"""Poison Nova's linked 15 IAS / 30 fire jewel, not a parent-total guess."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


CONTEXT = {'player_class': 'Necromancer', 'mercenary_type': 'Act 2 Might'}
ITEM = Item(
    'Demonhead',
    'unique',
    "Andariel's Visage",
    ((93, 0, 35), (39, 0, 0), (60, 0, 8), (0, 0, 25), (127, 0, 2), (16, 0, 100)),
    ethereal=True,
    sockets=1,
    socket_contents='filled',
    socket_items=(SocketItem('Jewel', ((93, 0, 15), (39, 0, 30)), complete=True),),
    owned_stats=((16, 0, 100),),
)


def cases():
    examples = (
        ('linked-jewel-low-native', ITEM, CONTEXT, 'positive'),
        ('wrong-mercenary', ITEM, {**CONTEXT, 'mercenary_type': 'Act 5 Frenzy'}, 'negative'),
        ('unknown-mercenary', ITEM, {'player_class': 'Necromancer'}, 'unknown'),
        ('nonethereal', replace(ITEM, ethereal=False), CONTEXT, 'negative'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), CONTEXT, 'unknown'),
        ('missing-child', replace(ITEM, socket_items=()), CONTEXT, 'unknown'),
        ('ral-not-jewel', replace(ITEM, socket_items=(SocketItem('Ral Rune'),)), CONTEXT, 'negative'),
        (
            'ruby-damage-not-fire',
            replace(ITEM, socket_items=(SocketItem('Jewel', ((93, 0, 15), (17, 0, 40), (18, 0, 40)), True),)),
            CONTEXT,
            'negative',
        ),
        (
            'fire-one-short',
            replace(ITEM, socket_items=(SocketItem('Jewel', ((93, 0, 15), (39, 0, 29)), True),)),
            CONTEXT,
            'negative',
        ),
        (
            'partial-child',
            replace(ITEM, socket_items=(SocketItem('Jewel', ((93, 0, 15),)),)),
            CONTEXT,
            'unknown',
        ),
    )
    for variant in (1, 2):
        planner_profile = 0 if variant == 1 else 2
        role = f'poison-nova-necromancer-{variant}-merc-andariel-ias-fire'
        config = role + '-stats'
        for label, item, context, scenario in examples:
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        side='merc',
                        rule_trace=IsPartialDict(
                            truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                        ),
                    )
                ),
                'trade_tier': IsPartialDict(status='reviewed'),
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config))
                            for key in ('93:0', '60:0', '0:0', '127:0', '39:0')
                        }
                    )
                )
            yield Case(
                id=f'poison-nova/andariel-socketed/{variant}/{label}',
                item=item,
                context=context,
                expected={
                    'assessment': IsPartialDict(**expected),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                covers=(role,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (config,),
                report_contains=("Andariel's Visage", 'Trade tier:')
                + (('Mercenary Andariel helmet with IAS/fire-resistance jewel',) if scenario == 'positive' else ()),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/poison-nova-necromancer/variants/{variant}',
                    'pricing/raw/mr/planners/bv7710o1.json:/data/planner/items/17',
                    'pricing/raw/mr/planners/bv7710o1.json:/data/planner/items/18',
                    f'pricing/raw/mr/planners/bv7710o1.json:/data/planner/profiles/{planner_profile}/mercItems/head',
                ),
            )


CASES = tuple(cases())
