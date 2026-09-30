"""Face of Horror strength and resistance benefits do not make flee universally desirable."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item(
    'Mask',
    'unique',
    'The Face of Horror',
    ((0, 0, 20), (112, 0, 64), (122, 0, 50), *((stat, 0, 10) for stat in (39, 41, 43, 45))),
)


STRUCTURED = (
    ('abyss-warlock-build-guide', 'Warlock', 2),
    ('berserk-barbarian', 'Barbarian', 2),
    ('double-throw-barbarian-guide', 'Barbarian', 2),
    ('echoing-strike-warlock-guide', 'Warlock', 2),
    ('enchant-sorceress', 'Sorceress', 2),
    ('fire-warlock-guide', 'Warlock', 2),
    ('fissure-druid', 'Druid', 2),
    ('fist-of-the-heavens-paladin', 'Paladin', 2),
    ('lightning-fury-amazon-guide', 'Amazon', 2),
    ('lightning-sorceress', 'Sorceress', 2),
    ('lightning-strike-amazon', 'Amazon', 2),
    ('mirrored-blades-warlock-guide', 'Warlock', 2),
    ('poison-nova-necromancer', 'Necromancer', 2),
    ('strafe-amazon', 'Amazon', 2),
    ('summoner-necromancer-guide', 'Necromancer', 2),
)
TABLES = (
    ('blood-boil-warlock-guide', 'Warlock', 40),
    ('summoner-warlock-guide', 'Warlock', 40),
)


def specs():
    for build, klass, index in STRUCTURED:
        yield (
            build + '-the-face-of-horror-merc-native-alternative',
            klass,
            False,
            f'pricing/data/wp-a-builds.json:/{build}/merc/Helmet/early/{index}',
        )
    for build, klass, section in TABLES:
        yield (
            build + '-the-face-of-horror-merc-survival-gear',
            klass,
            True,
            f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__{build}.html/sections/{section}',
        )


def cases():
    for role, klass, might, source in specs():
        context = {'player_class': klass, **({'mercenary_type': 'Act 2 Might'} if might else {})}
        examples = [
            ('native', ITEM, context, 'positive'),
            ('ethereal', replace(ITEM, ethereal=True), context, 'positive'),
            ('exceptional-upgrade', replace(ITEM, base='Death Mask'), context, 'positive'),
            ('elite-upgrade', replace(ITEM, base='Demonhead'), context, 'positive'),
            (
                'wrong-class',
                ITEM,
                {**context, 'player_class': 'Sorceress' if klass != 'Sorceress' else 'Paladin'},
                'negative',
            ),
            ('unknown-class', ITEM, {'mercenary_type': 'Act 2 Might'} if might else {}, 'unknown'),
        ]
        if might:
            examples.extend(
                (
                    ('wrong-mercenary', ITEM, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'negative'),
                    ('unknown-mercenary', ITEM, {'player_class': klass}, 'unknown'),
                    (
                        'empty-socket',
                        replace(ITEM, sockets=1, raw_stats=(*ITEM.raw_stats, (194, 0, 1))),
                        context,
                        'positive',
                    ),
                )
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
                            key: IsPartialDict(configuration_ids=Contains(config))
                            for key in ('0:0', '39:0', '41:0', '43:0', '45:0')
                        }
                    )
                )
            yield Case(
                id=f'the-face-of-horror-merc/{role}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                absent_stat_configurations=dict.fromkeys(('112:0', '122:0'), (config,)),
                report_contains=('The Face of Horror', 'Trade tier:', 'Hit Causes Monster to Flee'),
                evidence=(source, 'third-parties/d2data/json/uniqueitems.json:/78'),
            )


CASES = tuple(cases())
