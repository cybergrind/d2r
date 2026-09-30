"""Loose IAS/fire-resist jewels for six explicitly sourced mercenary helmet uses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = (
    ('lightning-sorceress', 'Sorceress', (('lightning-standard', 1), ('lightning-mf', 2))),
    ('blizzard-sorceress', 'Sorceress', (('blizzard-standard', 1), ('blizzard-set', 3))),
    ('blessed-hammer-paladin', 'Paladin', (('hammer-standard', 1), ('hammer-ubers', 3))),
)
RECIPIENT = "Andariel's Visage"


def jewel(resistance=30):
    return Item(
        'Jewel',
        'magic',
        None,
        ((93, 0, 15), (39, 0, resistance)),
        complete=True,
        affix_records=(('prefix', 375 if resistance <= 15 else 376), ('suffix', 171)),
    )


def cases():
    for guide, klass, uses in USES:
        roles = tuple(prefix + '-ias-fire-jewel' for prefix, _ in uses)
        configs = tuple(role + '-stats' for role in roles)
        context = {'player_class': klass, 'mercenary_items': [RECIPIENT]}
        item = jewel()
        examples = [
            ('perfect-ruby', item, context, 'positive', 'true', 'true'),
            ('minimum-ruby', jewel(16), context, 'positive', 'true', 'true'),
            ('minimum-garnet', jewel(5), context, 'positive', 'true', 'true'),
            ('wrong-helmet', item, {**context, 'mercenary_items': ['Vampire Gaze']}, 'negative', 'true', 'false'),
            (
                'player-helmet',
                item,
                {'player_class': klass, 'player_items': [RECIPIENT], 'mercenary_items': []},
                'negative',
                'true',
                'false',
            ),
            ('unknown-helmet', item, {'player_class': klass}, 'unknown', 'true', 'unknown'),
        ]
        for stat, name, record in ((93, 'ias', ('suffix', 171)), (39, 'fire-resistance', ('prefix', 376))):
            for complete, scenario, truth in ((True, 'negative', 'false'), (False, 'unknown', 'unknown')):
                candidate = replace(
                    item,
                    raw_stats=tuple(s for s in item.raw_stats if s[0] != stat),
                    complete=complete,
                    affix_records=tuple(a for a in item.affix_records if a != record) if complete else None,
                )
                examples.append(
                    (('absent-' if complete else 'unread-') + name, candidate, context, scenario, truth, 'true')
                )
        for label, candidate, ctx, scenario, truth, dependency in examples:
            expected = {
                'roles': Contains(
                    *(
                        IsPartialDict(
                            id=role,
                            side='merc',
                            rule_trace=IsPartialDict(truth=truth),
                            dependencies=Contains(IsPartialDict(status=dependency)),
                        )
                        for role in roles
                    )
                )
            }
            active = truth == dependency == 'true'
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in ('93:0', '39:0')}
                    )
                )
            result = {'assessment': IsPartialDict(**expected)}
            if label in ('perfect-ruby', 'minimum-ruby', 'minimum-garnet'):
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        IsPartialDict(
                            memory_stat=IsPartialDict(id=39),
                            roll_range=IsPartialDict(
                                min=5 if label == 'minimum-garnet' else 16, max=15 if label == 'minimum-garnet' else 30
                            ),
                            roll_quality_range=IsPartialDict(min=5, max=30),
                            roll_quality={'perfect-ruby': 'perfect', 'minimum-ruby': 'normal', 'minimum-garnet': 'low'}[
                                label
                            ],
                            roll_tier=2 if label == 'minimum-garnet' else 1,
                        )
                    )
                )
            yield Case(
                id=f'merc-ias-fire-jewels/{guide}/{label}',
                item=candidate,
                context=ctx,
                covers=roles,
                scenario=scenario,
                expected=result,
                absent_configurations=() if active else configs,
                report_contains=('Jewel', 'Increased Attack Speed', 'Fire Resist') if active else ('Jewel',),
                evidence=(
                    *(f'pricing/data/wp-a-variants/{guide}.json:/variants/{i}/merc/Helmet/0' for _, i in uses),
                    'third-parties/d2data/json/magicprefix.json:/375',
                    'third-parties/d2data/json/magicprefix.json:/376',
                    'third-parties/d2data/json/magicsuffix.json:/171',
                ),
            )


CASES = tuple(cases())
