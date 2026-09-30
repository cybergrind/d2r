"""Arachnid caster-table alternatives: skill/FCR utility, not passive Venom."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


GROUPS = (
    ('Warlock', 'caster-core-gear', (('blood-boil-warlock-guide', 29), ('summoner-warlock-guide', 29))),
    (
        'Sorceress',
        'caster-core-gear',
        (
            ('fire-wall-sorceress-guide', 30),
            ('frozen-orb-meteor-sorceress', 29),
            ('frozen-orb-sorceress', 29),
            ('hydra-sorceress', 29),
        ),
    ),
    ('Necromancer', 'summoner-caster-gear', (('summoner-necromancer-guide', 33),)),
)


def cases():
    for player_class, suffix, sources in GROUPS:
        roles = tuple(f'{guide}-arachnid-mesh-{suffix}' for guide, _ in sources)
        context = {'player_class': player_class}
        item = Item(
            'Spiderweb Sash',
            'unique',
            'Arachnid Mesh',
            raw_stats=(
                (16, 0, 90),
                (105, 0, 20),
                (127, 0, 1),
                (77, 0, 5),
                (150, 0, 10),
                (204, 17795, (11 << 8) | 11),
            ),
        )
        examples = (
            ('minimum-defense', item, context, 'true', 'positive'),
            (
                'maximum-defense',
                replace(item, raw_stats=((16, 0, 120), *item.raw_stats[1:])),
                context,
                'true',
                'positive',
            ),
            (
                'depleted-venom',
                replace(item, raw_stats=(*item.raw_stats[:-1], (204, 17795, 11 << 8))),
                context,
                'true',
                'positive',
            ),
            ('unidentified', replace(item, identified=False), context, 'false', 'negative'),
            ('ethereal', replace(item, ethereal=True), context, 'false', 'negative'),
            ('unread-ethereal', replace(item, ethereal=None), context, 'unknown', 'unknown'),
            ('invalid-socket', replace(item, sockets=1), context, 'false', 'negative'),
            ('unread-sockets', replace(item, sockets=None), context, 'unknown', 'unknown'),
            ('wrong-class', item, {'player_class': 'Barbarian'}, 'false', 'negative'),
            ('unread-class', item, {}, 'unknown', 'unknown'),
        )
        for label, candidate, loadout, truth, scenario in examples:
            expected = {
                'roles': Contains(*(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles))
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(*(role + '-stats' for role in roles)))
                            for key in ('127:0', '105:0', '77:0', '16:0')
                        }
                    )
                )
            yield Case(
                id=f'arachnid-caster-alternative/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario=scenario,
                covers=roles,
                expected={'assessment': IsPartialDict(**expected)},
                absent_stat_configurations={
                    key: tuple(role + '-stats' for role in roles) for key in ('150:0', '204:17795')
                },
                report_contains=('Arachnid Mesh',),
                evidence=(
                    *(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        f'pricing~1raw~1mr~1guides__{guide}.html/sections/{section}'
                        for guide, section in sources
                    ),
                    'third-parties/d2data/json/uniqueitems.json:/373',
                ),
            )


def breakpoint_cases():
    item = Item(
        'Spiderweb Sash',
        'unique',
        'Arachnid Mesh',
        raw_stats=(
            (16, 0, 90),
            (105, 0, 20),
            (127, 0, 1),
            (77, 0, 5),
            (150, 0, 10),
            (204, 17795, (11 << 8) | 11),
        ),
    )
    for build, fcr, fhr in (
        ('blizzard-sorceress', 105, None),
        ('meteor-sorceress', 63, 60),
        ('lightning-sorceress', 117, None),
    ):
        role = build.split('-')[0] + '-standard-arachnid'
        context = {'player_class': 'Sorceress', 'player_total_fcr': fcr}
        if fhr is not None:
            context['player_total_fhr'] = fhr
        examples = [
            ('at-breakpoint', context, 'true', 'positive'),
            ('below-cast-breakpoint', dict(context, player_total_fcr=fcr - 1), 'false', 'negative'),
            ('unknown-cast-total', {k: v for k, v in context.items() if k != 'player_total_fcr'}, 'unknown', 'unknown'),
        ]
        if fhr is not None:
            examples.extend(
                (
                    ('below-recovery-breakpoint', dict(context, player_total_fhr=fhr - 1), 'false', 'negative'),
                    (
                        'unknown-recovery-total',
                        {k: v for k, v in context.items() if k != 'player_total_fhr'},
                        'unknown',
                        'unknown',
                    ),
                    ('optional-faster-cast', dict(context, player_total_fcr=105), 'true', 'positive'),
                )
            )
        for label, loadout, truth, scenario in examples:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                            for key in ('105:0', '127:0', '77:0')
                        }
                    )
                )
            yield Case(
                id=f'arachnid-caster-alternative/{build}/{label}',
                item=item,
                context=loadout,
                scenario=scenario,
                covers=(role,),
                expected={'assessment': IsPartialDict(**expected)},
                absent_stat_configurations=dict.fromkeys(('16:0', '150:0', '204:17795'), (role + '-stats',)),
                report_contains=('Arachnid Mesh',),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/variants/1',
                    'third-parties/d2data/json/uniqueitems.json:/373',
                ),
            )


CASES = (*cases(), *breakpoint_cases())
