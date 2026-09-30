"""Venom Ward has three distinct poison mitigation effects."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item(
    'Breast Plate',
    'unique',
    'Venom Ward',
    ((16, 0, 60), (45, 0, 90), (46, 0, 15), (110, 0, 50), (89, 0, 2)),
)


STRUCTURED = (
    ('enchant-sorceress', 'Sorceress', 6),
    ('fissure-druid', 'Druid', 7),
    ('fist-of-the-heavens-paladin', 'Paladin', 4),
    ('lightning-fury-amazon-guide', 'Amazon', 7),
    ('meteor-sorceress', 'Sorceress', 2),
    ('summoner-necromancer-guide', 'Necromancer', 6),
)
TABLES = (('summoner-warlock-guide', 'Warlock', 40),)


def specs():
    for build, klass, index in STRUCTURED:
        yield (
            build + '-venom ward-early-merc-resistance-alternative',
            klass,
            False,
            f'pricing/data/wp-a-builds.json:/{build}/merc/Body Armor/early/{index}',
        )
    for build, klass, section in TABLES:
        yield (
            build + '-venom-ward-merc-survival-gear',
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
            ('exceptional-upgrade', replace(ITEM, base='Cuirass'), context, 'positive'),
            ('elite-upgrade', replace(ITEM, base='Great Hauberk'), context, 'positive'),
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
                            for key in ('45:0', '46:0', '110:0', '16:0')
                        }
                    )
                )
            yield Case(
                id=f'venom-ward-merc/{role}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                absent_stat_configurations=dict.fromkeys(('89:0',), (config,)),
                report_contains=('Venom Ward', 'Trade tier:', '(60-100%)', 'Poison Resist +90%'),
                evidence=(source, 'third-parties/d2data/json/uniqueitems.json:/86'),
            )


CASES = tuple(cases())
