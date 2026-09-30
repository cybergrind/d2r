"""Rockfleece native damage reduction and strength across reviewed alternatives."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.rockstopper_mercenaries import TABLES
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item('Field Plate', 'unique', 'Rockfleece', ((16, 0, 100), (36, 0, 10), (34, 0, 5), (0, 0, 5), (91, 0, -10)))
STRUCTURED = (
    ('abyss-warlock-build-guide', 'Warlock', 3),
    ('berserk-barbarian', 'Barbarian', 5),
    ('blessed-hammer-paladin', 'Paladin', 3),
    ('blizzard-sorceress', 'Sorceress', 2),
    ('double-throw-barbarian-guide', 'Barbarian', 5),
    ('dream-paladin', 'Paladin', 5),
    ('echoing-strike-warlock-guide', 'Warlock', 3),
    ('enchant-sorceress', 'Sorceress', 4),
    ('fire-blast-assassin', 'Assassin', 2),
    ('fire-warlock-guide', 'Warlock', 3),
    ('fissure-druid', 'Druid', 5),
    ('fist-of-the-heavens-paladin', 'Paladin', 3),
    ('gold-find-barbarian', 'Barbarian', 2),
    ('lightning-fury-amazon-guide', 'Amazon', 5),
    ('lightning-sentry-assassin', 'Assassin', 2),
    ('lightning-sorceress', 'Sorceress', 5),
    ('lightning-strike-amazon', 'Amazon', 5),
    ('mirrored-blades-warlock-guide', 'Warlock', 3),
    ('nova-sorceress-guide', 'Sorceress', 2),
    ('poison-nova-necromancer', 'Necromancer', 5),
    ('strafe-amazon', 'Amazon', 2),
    ('summoner-necromancer-guide', 'Necromancer', 4),
)


def specs():
    for build, klass, index in STRUCTURED:
        yield (
            build + '-early-merc-rockfleece',
            klass,
            False,
            f'pricing/data/wp-a-builds.json:/{build}/merc/Body Armor/early/{index}',
        )
    for build, klass, section in TABLES:
        if build == 'zeal-paladin':
            continue  # Existing Zeal bank covers its separately reviewed armor alternative.
        yield (
            build + '-rockfleece-merc-survival-gear',
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
            ('exceptional-upgrade', replace(ITEM, base='Sharktooth Armor'), context, 'positive'),
            ('elite-upgrade', replace(ITEM, base='Kraken Shell'), context, 'positive'),
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
                        {key: IsPartialDict(configuration_ids=Contains(config)) for key in ('36:0', '34:0', '0:0')}
                    )
                )
            yield Case(
                id=f'rockfleece-merc/{role}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                absent_stat_configurations={'16:0': (config,)},
                report_contains=('Rockfleece', 'Trade tier:', '(100-130%)'),
                evidence=(source, 'third-parties/d2data/json/uniqueitems.json:/89'),
            )


CASES = tuple(cases())
