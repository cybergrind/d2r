"""Native low-roll Rockstopper utility, with source-specific mercenary context."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item(
    'Sallet',
    'unique',
    'Rockstopper',
    ((16, 0, 160), (36, 0, 10), (99, 0, 30), (39, 0, 20), (41, 0, 20), (43, 0, 20), (3, 0, 15)),
)
# Reviewed source entries, not a list discovered from production profile predicates.
STRUCTURED = (
    ('abyss-warlock-build-guide', 'Warlock', 6),
    ('berserk-barbarian', 'Barbarian', 5),
    ('blessed-hammer-paladin', 'Paladin', 6),
    ('blizzard-sorceress', 'Sorceress', 4),
    ('double-throw-barbarian-guide', 'Barbarian', 6),
    ('dream-paladin', 'Paladin', 6),
    ('echoing-strike-warlock-guide', 'Warlock', 6),
    ('enchant-sorceress', 'Sorceress', 6),
    ('fire-blast-assassin', 'Assassin', 5),
    ('fire-warlock-guide', 'Warlock', 6),
    ('fissure-druid', 'Druid', 6),
    ('fist-of-the-heavens-paladin', 'Paladin', 6),
    ('lightning-fury-amazon-guide', 'Amazon', 6),
    ('lightning-sentry-assassin', 'Assassin', 5),
    ('lightning-sorceress', 'Sorceress', 6),
    ('lightning-strike-amazon', 'Amazon', 6),
    ('meteor-sorceress', 'Sorceress', 5),
    ('mirrored-blades-warlock-guide', 'Warlock', 6),
    ('nova-sorceress-guide', 'Sorceress', 5),
    ('poison-nova-necromancer', 'Necromancer', 6),
    ('strafe-amazon', 'Amazon', 6),
    ('summoner-necromancer-guide', 'Necromancer', 6),
)
TABLES = (
    ('blood-boil-warlock-guide', 'Warlock', 40),
    ('summoner-warlock-guide', 'Warlock', 40),
    ('fire-wall-sorceress-guide', 'Sorceress', 41),
    ('frozen-orb-meteor-sorceress', 'Sorceress', 40),
    ('frozen-orb-sorceress', 'Sorceress', 40),
    ('hydra-sorceress', 'Sorceress', 40),
    ('zeal-paladin', 'Paladin', 44),
)


def specs():
    for build, klass, index in STRUCTURED:
        yield (
            build + '-rockstopper-mid-merc-resistance-alternative',
            klass,
            False,
            f'pricing/data/wp-a-builds.json:/{build}/merc/Helmet/mid/{index}',
        )
    for build, klass, section in TABLES:
        yield (
            build + '-rockstopper-merc-survival-gear',
            klass,
            True,
            f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__{build}.html/sections/{section}',
        )


def cases():
    for role, klass, might, source in specs():
        context = {'player_class': klass, **({'mercenary_type': 'Act 2 Might'} if might else {})}
        examples = [
            ('minimum-rolls', ITEM, context, 'positive'),
            ('ethereal', replace(ITEM, ethereal=True), context, 'positive'),
            ('upgraded', replace(ITEM, base='Hydraskull'), context, 'positive'),
            (
                'wrong-class',
                ITEM,
                {
                    'player_class': 'Sorceress' if klass != 'Sorceress' else 'Paladin',
                    **({'mercenary_type': 'Act 2 Might'} if might else {}),
                },
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
                            for key in ('36:0', '99:0', '39:0', '41:0', '43:0')
                        }
                    )
                )
            yield Case(
                id=f'rockstopper-merc/{role}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                absent_stat_configurations={'3:0': (config,), '16:0': (config,)},
                report_contains=('Rockstopper', 'Trade tier:', '(160-220%)'),
                evidence=(source, 'third-parties/d2data/json/uniqueitems.json:/202'),
            )


CASES = tuple(cases())
