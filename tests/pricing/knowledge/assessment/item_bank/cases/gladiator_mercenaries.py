"""Gladiator mercenary flat reductions, recovery and chill protection."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item(
    'Wire Fleece',
    'unique',
    "The Gladiator's Bane",
    ((16, 0, 150), (34, 0, 15), (35, 0, 15), (99, 0, 30), (110, 0, 50), (153, 0, 1), (78, 0, 20)),
)


STRUCTURED = (
    ('berserk-barbarian', 'Barbarian', 3),
    ('blessed-hammer-paladin', 'Paladin', 3),
    ('blizzard-sorceress', 'Sorceress', 2),
    ('double-throw-barbarian-guide', 'Barbarian', 3),
    ('dream-paladin', 'Paladin', 3),
    ('enchant-sorceress', 'Sorceress', 3),
    ('fissure-druid', 'Druid', 3),
    ('lightning-fury-amazon-guide', 'Amazon', 3),
    ('lightning-sorceress', 'Sorceress', 3),
    ('lightning-strike-amazon', 'Amazon', 3),
    ('meteor-sorceress', 'Sorceress', 3),
    ('poison-nova-necromancer', 'Necromancer', 3),
    ('strafe-amazon', 'Amazon', 3),
    ('summoner-necromancer-guide', 'Necromancer', 3),
)
TABLES = (('zeal-paladin', 'Paladin', 44),)


def specs():
    for build, klass, index in STRUCTURED:
        yield (
            build + '-the-gladiator-s-bane-merc-native-alternative',
            klass,
            False,
            f'pricing/data/wp-a-builds.json:/{build}/merc/Body Armor/mid/{index}',
        )
    for build, klass, section in TABLES:
        yield (
            build + '-the-gladiator-s-bane-merc-survival-gear',
            klass,
            True,
            f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__{build}.html/sections/{section}',
        )


def cases():
    for role, klass, might, source in specs():
        context = {'player_class': klass, **({'mercenary_type': 'Act 2 Might'} if might else {})}
        examples = [
            ('minimum-defense-roll', ITEM, context, 'positive'),
            ('ethereal', replace(ITEM, ethereal=True), context, 'positive'),
            (
                'perfect-reductions',
                replace(
                    ITEM,
                    raw_stats=tuple(
                        (stat, layer, 20 if stat in (34, 35) else value) for stat, layer, value in ITEM.raw_stats
                    ),
                ),
                context,
                'positive',
            ),
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
                            for key in ('34:0', '35:0', '99:0', '110:0', '153:0')
                        }
                    )
                )
            yield Case(
                id=f'the-gladiator-s-bane-merc/{role}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                absent_stat_configurations=dict.fromkeys(('78:0', '16:0'), (config,)),
                report_contains=("The Gladiator's Bane", 'Trade tier:', '(150-200%)', 'Cannot Be Frozen'),
                evidence=(source, 'third-parties/d2data/json/uniqueitems.json:/250'),
            )


CASES = tuple(cases())
