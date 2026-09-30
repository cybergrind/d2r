"""Reaper's Toll belongs to the cited Act 2 branches, not every table column."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.zeal_reapers import BASE
from tests.pricing.knowledge.assessment.item_bank.models import Case


USES = (
    ('dream-paladin', 'Paladin', 'mid', 0, 'Might'),
    ('dream-paladin', 'Paladin', 'end', 0, 'Might'),
    ('fissure-druid', 'Druid', 'mid', 0, 'Might'),
    ('fissure-druid', 'Druid', 'end', 1, 'Might'),
    ('fissure-druid', 'Druid', 'end', 1, 'Defiance'),
    ('strafe-amazon', 'Amazon', 'end', 1, 'Might'),
)


def cases():
    for build, klass, tier, index, aura in USES:
        role = f'{build}-reaper-{tier}-act-2-{aura.lower()}-named-merc-weapon'
        config = role + '-stats'
        context = {'player_class': klass, 'mercenary_type': 'Act 2 ' + aura}
        for label, item, ctx, scenario in (
            ('native-minimum', BASE, context, 'positive'),
            ('ethereal', replace(BASE, ethereal=True), context, 'positive'),
            ('unknown-ethereal', replace(BASE, ethereal=None), context, 'positive'),
            ('empty-socket', replace(BASE, sockets=1), context, 'positive'),
            ('impossible-sockets', replace(BASE, sockets=2), context, 'negative'),
            ('unknown-sockets', replace(BASE, sockets=None), context, 'unknown'),
            ('wrong-class', BASE, {**context, 'player_class': 'Sorceress'}, 'negative'),
            ('unknown-class', BASE, {'mercenary_type': 'Act 2 ' + aura}, 'unknown'),
            ('wrong-mercenary', BASE, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'negative'),
            ('unknown-mercenary', BASE, {'player_class': klass}, 'unknown'),
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
                            for key in ('17:0', '198:5569', '60:0', '141:0')
                        }
                    )
                )
            yield Case(
                id=f'reaper-merc-alternative/{role}/{label}',
                item=item,
                context=ctx,
                scenario=scenario,
                covers=(role,),
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                report_contains=("The Reaper's Toll", 'Trade tier:', 'Decrepify', '190-240'),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/merc/Weapon/{tier}/{index}',
                    'third-parties/d2data/json/uniqueitems.json:/326',
                ),
            )


CASES = tuple(cases())
