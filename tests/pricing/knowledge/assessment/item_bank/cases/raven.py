"""Raven Frost build uses: hit-based attacks and Smite have distinct recipients."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item(
    'Ring',
    'unique',
    'Raven Frost',
    (
        (153, 0, 1),
        (148, 0, 20),
        (9, 0, 40 << 8),
        (2, 0, 15),
        (19, 0, 150),
    ),
)
# Each list refers to exact cached variant indices. Smite does not use AR;
# the documented FoH Tri-Brid uses FoH/Holy Bolt, Blessed Hammer and Smite, none of which use AR.
USES = (
    ('berserk-barbarian', 'Barbarian', (1,), True),
    ('blessed-hammer-paladin', 'Paladin', (3,), False),
    ('dragon-talon-assassin', 'Assassin', (0, 1), True),
    ('dream-paladin', 'Paladin', (0, 1, 2), True),
    ('fist-of-the-heavens-paladin', 'Paladin', (3,), False),
    ('lightning-fury-amazon-guide', 'Amazon', (1, 2, 3), True),
    ('lightning-strike-amazon', 'Amazon', (1, 2), True),
    ('mirrored-blades-warlock-guide', 'Warlock', (1, 2), True),
    ('smite-paladin', 'Paladin', (1, 2), False),
    ('strafe-amazon', 'Amazon', (1, 2), True),
)


def cases():
    result = []
    for build, klass, variants, attack_rating in USES:
        for index in variants:
            role = f'{build}-{index}-raven-frost'
            for scenario, context in (
                ('positive', {'player_class': klass}),
                ('negative', {'player_class': 'Druid'}),
                ('unknown', {}),
            ):
                expected = {
                    'trade_tier': IsPartialDict(tier='med'),
                    'roles': Contains(
                        IsPartialDict(
                            id=role,
                            build=build,
                            rule_trace=IsPartialDict(
                                truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                            ),
                        )
                    ),
                }
                if scenario == 'positive':
                    keys = ('153:0', '2:0', '19:0') if attack_rating else ('153:0', '2:0')
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                        )
                    )
                result.append(
                    Case(
                        id='raven/' + role + '/' + scenario,
                        item=ITEM,
                        context=context,
                        expected={'assessment': IsPartialDict(**expected)},
                        covers=(role,),
                        scenario=scenario,
                        absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                        absent_stat_configurations={} if attack_rating else {'19:0': (role + '-stats',)},
                        report_contains=('Raven Frost', 'Trade tier: mid', '15 (15-20)', '150 (150-250)'),
                        evidence=(
                            f'pricing/data/wp-a-builds.json:/{build}/variants/{index}',
                            'third-parties/d2data/json/uniqueitems.json:/275',
                        ),
                    )
                )
    return tuple(result)


CASES = cases()
