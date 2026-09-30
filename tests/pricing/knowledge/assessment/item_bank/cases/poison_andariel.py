"""Poison Nova's two mercenary helmet uses; socket completion stays separate."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item(
    'Demonhead',
    'unique',
    "Andariel's Visage",
    ((93, 0, 20), (60, 0, 8), (0, 0, 25), (127, 0, 2), (39, 0, -30), (16, 0, 100)),
    ethereal=True,
    owned_stats=((16, 0, 100),),
)
CONTEXT = {'player_class': 'Necromancer', 'mercenary_type': 'Act 2 Might'}


def cases():
    examples = (
        ('native-minimum', ITEM, CONTEXT, 'positive'),
        ('wrong-mercenary', ITEM, {**CONTEXT, 'mercenary_type': 'Act 5 Frenzy'}, 'negative'),
        ('wrong-class', ITEM, {**CONTEXT, 'player_class': 'Paladin'}, 'negative'),
        ('nonethereal', replace(ITEM, ethereal=False), CONTEXT, 'negative'),
        ('unknown-mercenary', ITEM, {'player_class': 'Necromancer'}, 'unknown'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), CONTEXT, 'unknown'),
    )
    for variant in (1, 2):
        role = f'poison-nova-necromancer-{variant}-merc-andariel-native'
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
                            for key in ('93:0', '60:0', '0:0', '127:0')
                        }
                    )
                )
            yield Case(
                id=f'poison-nova/andariel/{variant}/{label}',
                item=item,
                context=context,
                covers=(role,),
                scenario=scenario,
                expected={
                    'assessment': IsPartialDict(**expected),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                absent_configurations=() if scenario == 'positive' else (config,),
                absent_stat_configurations={'39:0': (config,)},
                report_contains=("Andariel's Visage", 'Trade tier:', '(100-150%)'),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/poison-nova-necromancer/variants/{variant}',
                    'third-parties/d2data/json/uniqueitems.json:/345',
                ),
            )


CASES = tuple(cases())
