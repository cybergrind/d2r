"""Goldskin resistance armor and distinct Gold Find Barbarian player use."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item(
    'Full Plate Mail',
    'unique',
    'Goldskin',
    ((16, 0, 120), (79, 0, 100), (78, 0, 10), (89, 0, 2), *((stat, 0, 35) for stat in (39, 41, 43, 45))),
)


STRUCTURED = (
    ('berserk-barbarian', 'Barbarian', 4),
    ('blessed-hammer-paladin', 'Paladin', 2),
    ('double-throw-barbarian-guide', 'Barbarian', 4),
    ('dream-paladin', 'Paladin', 4),
    ('enchant-sorceress', 'Sorceress', 3),
    ('fissure-druid', 'Druid', 4),
    ('lightning-fury-amazon-guide', 'Amazon', 4),
    ('lightning-sorceress', 'Sorceress', 4),
    ('lightning-strike-amazon', 'Amazon', 4),
    ('poison-nova-necromancer', 'Necromancer', 4),
    ('summoner-necromancer-guide', 'Necromancer', 3),
)
TABLES = (
    ('fire-wall-sorceress-guide', 'Sorceress', 41),
    ('frozen-orb-meteor-sorceress', 'Sorceress', 40),
    ('frozen-orb-sorceress', 'Sorceress', 40),
    ('hydra-sorceress', 'Sorceress', 40),
)


def specs():
    for build, klass, index in STRUCTURED:
        yield (
            build + '-goldskin-early-merc-resistance-alternative',
            klass,
            False,
            f'pricing/data/wp-a-builds.json:/{build}/merc/Body Armor/early/{index}',
        )
    for build, klass, section in TABLES:
        yield (
            build + '-goldskin-merc-survival-gear',
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
            ('exceptional-upgrade', replace(ITEM, base='Chaos Armor'), context, 'positive'),
            ('elite-upgrade', replace(ITEM, base='Shadow Plate'), context, 'positive'),
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
                            for key in ('39:0', '41:0', '43:0', '45:0', '16:0', '79:0')
                        }
                    )
                )
            yield Case(
                id=f'goldskin-merc/{role}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                absent_stat_configurations=dict.fromkeys(('78:0', '89:0'), (config,)),
                report_contains=('Goldskin', 'Trade tier:', '(120-150%)'),
                evidence=(source, 'third-parties/d2data/json/uniqueitems.json:/91'),
            )


def player_cases():
    role = 'gold-find-barbarian-goldskin-caster-progression-alternative'
    config = role + '-stats'
    context = {'player_class': 'Barbarian'}
    for label, item, ctx, scenario in (
        ('native', ITEM, context, 'positive'),
        ('exceptional-upgrade', replace(ITEM, base='Chaos Armor'), context, 'positive'),
        ('elite-upgrade', replace(ITEM, base='Shadow Plate'), context, 'positive'),
        ('ethereal', replace(ITEM, ethereal=True), context, 'negative'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown'),
        ('wrong-class', ITEM, {'player_class': 'Sorceress'}, 'negative'),
        ('unknown-class', ITEM, {}, 'unknown'),
    ):
        expected = {
            'roles': Contains(
                IsPartialDict(
                    id=role,
                    side='player',
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
                        for key in ('79:0', '39:0', '41:0', '43:0', '45:0')
                    }
                )
            )
        yield Case(
            id=f'goldskin-player/{label}',
            item=item,
            context=ctx,
            covers=(role,),
            scenario=scenario,
            expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
            absent_configurations=() if scenario == 'positive' else (config,),
            absent_stat_configurations=dict.fromkeys(('16:0', '78:0', '89:0'), (config,)),
            report_contains=('Goldskin', 'Trade tier:', '(120-150%)'),
            evidence=(
                'pricing/data/wp-a-builds.json:/gold-find-barbarian/slots/Body Armor/2',
                'third-parties/d2data/json/uniqueitems.json:/91',
            ),
        )


CASES = (*cases(), *player_cases())
