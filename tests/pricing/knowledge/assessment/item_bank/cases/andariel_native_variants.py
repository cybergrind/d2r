"""Native mercenary helmet contributions, independently of guide socket jewels."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.poison_andariel import ITEM
from tests.pricing.knowledge.assessment.item_bank.models import Case


# Authored from the cited variant's mercenary type and Helmet row. A native
# helmet match does not certify the complete planner loadout or IAS breakpoint.
USES = (
    ('abyss-warlock-build-guide', (1, 2), 'Warlock', 'Act 2 Might'),
    ('blessed-hammer-paladin', (1, 3), 'Paladin', 'Act 2 Holy Freeze'),
    ('blizzard-sorceress', (1, 3), 'Sorceress', 'Act 2 Might'),
    ('fire-blast-assassin', (1,), 'Assassin', 'Act 2 Might'),
    ('fire-warlock-guide', (1, 2), 'Warlock', 'Act 2 Might'),
    ('fist-of-the-heavens-paladin', (2,), 'Paladin', 'Act 2 Might'),
    ('fist-of-the-heavens-paladin', (4,), 'Paladin', 'Act 2 Holy Freeze'),
    ('lightning-fury-amazon-guide', (1, 2), 'Amazon', 'Act 2 Might'),
    ('lightning-sentry-assassin', (1, 2), 'Assassin', 'Act 2 Holy Freeze'),
    ('lightning-sorceress', (1, 2), 'Sorceress', 'Act 2 Might'),
    ('meteor-sorceress', (1, 3), 'Sorceress', 'Act 2 Might'),
    ('wake-of-fire-assassin', (1,), 'Assassin', 'Act 2 Might'),
    ('double-throw-barbarian-guide', (1, 2), 'Barbarian', 'Act 1 Fire'),
    ('mirrored-blades-warlock-guide', (1, 2), 'Warlock', 'Act 2 Might'),
    ('strafe-amazon', (1, 2), 'Amazon', 'Act 2 Might'),
    ('summoner-necromancer-guide', (1, 2), 'Necromancer', 'Act 2 Might'),
)


def cases():
    for build, variants, klass, mercenary in USES:
        context = {'player_class': klass, 'mercenary_type': mercenary}
        examples = (
            ('minimum-rolls', ITEM, context, 'positive'),
            ('wrong-mercenary', ITEM, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'negative'),
            (
                'wrong-class',
                ITEM,
                {**context, 'player_class': 'Sorceress' if klass != 'Sorceress' else 'Paladin'},
                'negative',
            ),
            ('nonethereal', replace(ITEM, ethereal=False), context, 'negative'),
            ('unknown-mercenary', ITEM, {'player_class': klass}, 'unknown'),
            ('unknown-class', ITEM, {'mercenary_type': mercenary}, 'unknown'),
            ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown'),
        )
        for variant in variants:
            role = f'{build}-{variant}-merc-andariel-native'
            config = role + '-stats'
            for label, item, ctx, scenario in examples:
                expected = {
                    'roles': Contains(
                        IsPartialDict(
                            id=role,
                            side='merc',
                            rule_trace=IsPartialDict(
                                truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                            ),
                        )
                    ),
                    'trade_tier': IsPartialDict(status='reviewed'),
                }
                if scenario == 'positive':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(config))
                                for key in ('93:0', '60:0', '0:0', '127:0')
                            }
                        )
                    )
                yield Case(
                    id=f'andariel-native-variants/{role}/{label}',
                    item=item,
                    context=ctx,
                    covers=(role,),
                    scenario=scenario,
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    absent_configurations=() if scenario == 'positive' else (config,),
                    absent_stat_configurations={'39:0': (config,)},
                    report_contains=("Andariel's Visage", 'Trade tier:', '(100-150%)', 'Fire Resist -30%'),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/variants/{variant}',
                        'third-parties/d2data/json/uniqueitems.json:/345',
                    ),
                )


CASES = tuple(cases())
