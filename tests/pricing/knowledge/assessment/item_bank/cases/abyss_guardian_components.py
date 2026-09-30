"""Loose Guardian's Light components require their own recipient, not inferred socketing."""

from dataclasses import replace

from dirty_equals import Contains, FunctionCheck, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item(
    'Colossal Jewel',
    'unique',
    "Guardian's Light",
    ((357, 0, 5), (358, 0, 5), (85, 0, 3), (80, 0, 15), (79, 0, 25), (201, 387 * 64 + 25, 1)),
)


def cases(
    build='abyss-warlock-build-guide',
    player_class='Warlock',
    prefix='abyss',
    recipients=((2, 'Harlequin Crest', 'Crown of Ages'), (3, 'Crown of Ages', 'Harlequin Crest')),
    keys=('357:0', '358:0', '85:0', '80:0', '79:0'),
):
    for variant, recipient, other in recipients:
        role = f'{build}-guardian-s-light-v{variant}-helmet-0-named-socket-jewel'
        context = {'player_class': player_class, 'player_items': [recipient]}
        rows = [
            ('minimum', ITEM, context, 'true', 'positive'),
            (
                'perfect-pierce',
                replace(
                    ITEM,
                    raw_stats=tuple(
                        (stat, layer, 10 if stat == 358 else value) for stat, layer, value in ITEM.raw_stats
                    ),
                ),
                context,
                'true',
                'positive',
            ),
            ('wrong-recipient', ITEM, {**context, 'player_items': [other]}, 'true', 'negative'),
            ('missing-recipient', ITEM, {**context, 'player_items': []}, 'true', 'negative'),
            (
                'merc-recipient',
                ITEM,
                {**context, 'player_items': [], 'mercenary_items': [recipient]},
                'true',
                'negative',
            ),
            ('unknown-recipient', ITEM, {'player_class': player_class}, 'true', 'unknown'),
            ('wrong-class', ITEM, {**context, 'player_class': 'Sorceress'}, 'false', 'negative'),
            ('unknown-class', ITEM, {'player_items': [recipient]}, 'unknown', 'unknown'),
            (
                'unread-pierce',
                replace(ITEM, raw_stats=tuple(row for row in ITEM.raw_stats if row[0] != 358)),
                context,
                'unknown',
                'unknown',
            ),
            ('unidentified', replace(ITEM, identified=False), context, 'false', 'negative'),
            ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown', 'unknown'),
        ]
        for label, item, loadout, truth, scenario in rows:
            if variant == 3 and build in ('abyss-warlock-build-guide', 'berserk-barbarian'):
                yield Case(
                    id=f'{prefix}/guardian-components/{variant}/{label}',
                    item=item,
                    context=loadout,
                    expected={'price_estimate': IsPartialDict(estimate_ist=None)},
                    covers=(role,),
                    scenario='negative',
                    absent_roles=(role,),
                    absent_configurations=(role + '-stats',),
                    report_contains=("Guardian's Light",),
                    evidence=('pricing/data/wp-a-builds.json',),
                )
                continue
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        rule_trace=IsPartialDict(truth=truth),
                        missing=Contains(FunctionCheck(lambda text: 'Only one Colossal Jewel' in text)),
                    )
                )
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            yield Case(
                id=f'{prefix}/guardian-components/{variant}/{label}',
                item=item,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=(role,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                absent_stat_configurations={'201:24793': (role + '-stats',)},
                report_contains=("Guardian's Light",),
                evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/uniqueitems.json'),
            )


CASES = tuple(cases())
