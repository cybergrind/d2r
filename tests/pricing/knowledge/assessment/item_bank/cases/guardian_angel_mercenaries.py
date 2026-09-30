"""Guardian Angel raises mercenary resistance caps, not current resistance."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item(
    'Templar Coat',
    'unique',
    'Guardian Angel',
    (
        (16, 0, 180),
        (83, 3, 1),
        (102, 0, 30),
        (20, 0, 20),
        (245, 0, 5),
        (89, 0, 4),
        *((stat, 0, 15) for stat in (40, 42, 44, 46)),
    ),
)
STRUCTURED = (
    ('abyss-warlock-build-guide', 'Warlock', 4),
    ('berserk-barbarian', 'Barbarian', 5),
    ('blessed-hammer-paladin', 'Paladin', 5),
    ('double-throw-barbarian-guide', 'Barbarian', 5),
    ('dream-paladin', 'Paladin', 5),
    ('echoing-strike-warlock-guide', 'Warlock', 4),
    ('enchant-sorceress', 'Sorceress', 5),
    ('fire-warlock-guide', 'Warlock', 4),
    ('fissure-druid', 'Druid', 5),
    ('fist-of-the-heavens-paladin', 'Paladin', 4),
    ('lightning-fury-amazon-guide', 'Amazon', 5),
    ('lightning-sorceress', 'Sorceress', 5),
    ('lightning-strike-amazon', 'Amazon', 5),
    ('mirrored-blades-warlock-guide', 'Warlock', 4),
    ('poison-nova-necromancer', 'Necromancer', 5),
    ('strafe-amazon', 'Amazon', 5),
    ('summoner-necromancer-guide', 'Necromancer', 5),
)
TABLES = (
    ('blood-boil-warlock-guide', 'Warlock', 40),
    ('summoner-warlock-guide', 'Warlock', 40),
    ('zeal-paladin', 'Paladin', 44),
)


def specs():
    for build, klass, index in STRUCTURED:
        yield (
            build + '-guardian-angel-merc-native-alternative',
            klass,
            False,
            f'pricing/data/wp-a-builds.json:/{build}/merc/Body Armor/mid/{index}',
        )
    for build, klass, section in TABLES:
        yield (
            build + '-guardian-angel-merc-survival-gear',
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
            ('upgraded', replace(ITEM, base='Hellforge Plate'), context, 'positive'),
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
                            for key in ('40:0', '42:0', '44:0', '46:0')
                        }
                    )
                )
            yield Case(
                id=f'guardian-angel-merc/{role}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                absent_stat_configurations=dict.fromkeys(('83:3', '102:0', '20:0', '16:0'), (config,)),
                report_contains=('Guardian Angel', 'Trade tier:', '(180-200%)'),
                evidence=(source, 'third-parties/d2data/json/uniqueitems.json:/218'),
            )


CASES = tuple(cases())
