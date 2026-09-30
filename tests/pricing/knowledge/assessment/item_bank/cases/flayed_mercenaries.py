"""Skin of the Flayed One supplies attack leech and regeneration to mercenaries."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item(
    'Demonhide Armor',
    'unique',
    'Skin of the Flayed One',
    ((16, 0, 150), (60, 0, 5), (74, 0, 15), (78, 0, 15), (252, 0, 10)),
)

STRUCTURED = (
    ('abyss-warlock-build-guide', 'Warlock', 2),
    ('berserk-barbarian', 'Barbarian', 3),
    ('double-throw-barbarian-guide', 'Barbarian', 3),
    ('dream-paladin', 'Paladin', 3),
    ('echoing-strike-warlock-guide', 'Warlock', 2),
    ('enchant-sorceress', 'Sorceress', 2),
    ('fire-warlock-guide', 'Warlock', 2),
    ('fissure-druid', 'Druid', 3),
    ('fist-of-the-heavens-paladin', 'Paladin', 2),
    ('lightning-fury-amazon-guide', 'Amazon', 3),
    ('lightning-sorceress', 'Sorceress', 3),
    ('lightning-strike-amazon', 'Amazon', 3),
    ('mirrored-blades-warlock-guide', 'Warlock', 2),
    ('poison-nova-necromancer', 'Necromancer', 3),
    ('summoner-necromancer-guide', 'Necromancer', 2),
)
TABLES = (
    ('blood-boil-warlock-guide', 'Warlock', 40),
    ('summoner-warlock-guide', 'Warlock', 40),
)


def specs():
    for build, klass, index in STRUCTURED:
        yield (
            build + '-skin-of-the-flayed-one-merc-native-alternative',
            klass,
            False,
            f'pricing/data/wp-a-builds.json:/{build}/merc/Body Armor/early/{index}',
        )
    for build, klass, section in TABLES:
        yield (
            build + '-skin-of-the-flayed-one-merc-survival-gear',
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
            ('upgraded', replace(ITEM, base='Scarab Husk'), context, 'positive'),
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
                        {key: IsPartialDict(configuration_ids=Contains(config)) for key in ('60:0', '74:0')}
                    )
                )
            yield Case(
                id=f'skin-of-the-flayed-one-merc/{role}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                absent_stat_configurations=dict.fromkeys(('252:0', '78:0', '16:0'), (config,)),
                report_contains=('Skin of the Flayed One', 'Trade tier:', '(150-190%)'),
                evidence=(source, 'third-parties/d2data/json/uniqueitems.json:/211'),
            )


CASES = tuple(cases())
