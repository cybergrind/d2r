"""Shaftstop's native survival contribution across the reviewed mercenary builds."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


BASE = Item(
    'Mesh Armor', 'unique', 'Shaftstop', ((16, 0, 180), (36, 0, 30), (7, 0, 60 * 256), (32, 0, 250)), ethereal=True
)
# Generic-name sources permit the upgrade chain; explicit Mesh Armor sources keep that base.
SPECS = (
    ('dream-paladin-1-merc-shaftstop', 'Paladin', 'Act 1 Cold', '/dream-paladin/variants/1', False, True),
    ('dream-paladin-2-merc-shaftstop', 'Paladin', 'Act 1 Cold', '/dream-paladin/variants/2', True, True),
    (
        'lightning-strike-amazon-1-merc-shaftstop',
        'Amazon',
        'Act 1 Cold',
        '/lightning-strike-amazon/variants/1',
        True,
        True,
    ),
    ('strafe-amazon-1-merc-shaftstop', 'Amazon', 'Act 2 Might', '/strafe-amazon/variants/1', False, False),
    ('strafe-amazon-2-merc-shaftstop', 'Amazon', 'Act 2 Might', '/strafe-amazon/variants/2', False, False),
)


def cases():
    for role, klass, merc, source, upgraded, ethereal in SPECS:
        context = {'player_class': klass, 'mercenary_type': merc}
        examples = (
            ('minimum-defense-roll', BASE, context, 'positive'),
            ('perfect-defense-roll', replace(BASE, raw_stats=((16, 0, 220), *BASE.raw_stats[1:])), context, 'positive'),
            ('wrong-mercenary', BASE, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'negative'),
            ('unknown-mercenary', BASE, {'player_class': klass}, 'unknown'),
            ('wrong-class', BASE, {**context, 'player_class': 'Sorceress'}, 'negative'),
            ('unknown-class', BASE, {'mercenary_type': merc}, 'unknown'),
            ('nonethereal', replace(BASE, ethereal=False), context, 'negative' if ethereal else 'positive'),
            ('unknown-ethereal', replace(BASE, ethereal=None), context, 'unknown'),
            ('upgraded', replace(BASE, base='Boneweave'), context, 'positive' if upgraded else 'negative'),
        )
        for label, item, ctx, scenario in examples:
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
                        {
                            '36:0': IsPartialDict(configuration_ids=Contains(config)),
                            '7:0': IsPartialDict(configuration_ids=Contains(config)),
                        }
                    )
                )
            yield Case(
                id=f'shaftstop-merc/{role}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                absent_stat_configurations={'16:0': (config,)},
                report_contains=('Shaftstop', 'Trade tier:', '(180-220%)'),
                evidence=('pricing/data/wp-a-builds.json:' + source, 'third-parties/d2data/json/uniqueitems.json:/215'),
            )


CASES = tuple(cases())
