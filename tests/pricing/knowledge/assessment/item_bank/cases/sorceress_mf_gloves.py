"""Three-piece Tal MF setups retain their distinct character breakpoints."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


TAL = ("Tal Rasha's Guardianship", "Tal Rasha's Fine-Spun Cloth", "Tal Rasha's Adjudication")
# Native unique104: MF25-40, gold200, attack25, light2. Capture selected stats only.
GLOVES = Item('Chain Gloves', 'unique', 'Chance Guards', ((80, 0, 25), (79, 0, 200), (19, 0, 25), (89, 0, 2)))
USES = (
    ('blizzard', 'blizzard-sorceress', 105, None),
    ('meteor', 'meteor-sorceress', 105, 60),
    ('lightning', 'lightning-sorceress', 117, None),
)


def cases():
    for slug, build, fcr, fhr in USES:
        role = f'{slug}-mf-chance-guards'
        config = role + '-stats'
        full = {'player_class': 'Sorceress', 'player_total_fcr': fcr, 'player_items': list(TAL)}
        if fhr is not None:
            full['player_total_fhr'] = fhr
        variants = [
            ('native-minimum-mf', GLOVES, full, 'positive', 'true', 'true', True),
            ('exceptional-base', replace(GLOVES, base='Heavy Bracers'), full, 'positive', 'true', 'true', True),
            ('elite-base', replace(GLOVES, base='Vambraces'), full, 'positive', 'true', 'true', True),
            ('fcr-short', GLOVES, {**full, 'player_total_fcr': fcr - 1}, 'negative', 'false', 'true', False),
            (
                'fcr-unknown',
                GLOVES,
                {k: v for k, v in full.items() if k != 'player_total_fcr'},
                'unknown',
                'unknown',
                'true',
                False,
            ),
            (
                'companions-unknown',
                GLOVES,
                {k: v for k, v in full.items() if k != 'player_items'},
                'unknown',
                'true',
                'unknown',
                True,
            ),
            (
                'merc-not-player-set',
                GLOVES,
                {**full, 'player_items': [], 'mercenary_items': list(TAL)},
                'negative',
                'true',
                'false',
                True,
            ),
            ('wrong-class', GLOVES, {**full, 'player_class': 'Druid'}, 'negative', 'false', 'true', False),
            ('mf-uncaptured', replace(GLOVES, raw_stats=GLOVES.raw_stats[1:]), full, 'unknown', 'true', 'true', False),
        ]
        for companion in TAL:
            variants.append(
                (
                    f'missing-{companion}',
                    GLOVES,
                    {**full, 'player_items': [n for n in TAL if n != companion]},
                    'negative',
                    'true',
                    'false',
                    True,
                )
            )
        if fhr is not None:
            variants.extend(
                (
                    ('fhr-short', GLOVES, {**full, 'player_total_fhr': 59}, 'negative', 'false', 'true', False),
                    (
                        'fhr-unknown',
                        GLOVES,
                        {k: v for k, v in full.items() if k != 'player_total_fhr'},
                        'unknown',
                        'unknown',
                        'true',
                        False,
                    ),
                )
            )
        for label, item, context, scenario, truth, dependency, annotated in variants:
            # This configuration describes the three-piece setup. Native MF
            # remains visible, but its setup-specific annotation needs companions.
            annotated = annotated and dependency == 'true'
            assessment = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        build=build,
                        rule_trace=IsPartialDict(truth=truth),
                        dependencies=Contains(IsPartialDict(status=dependency)),
                    )
                ),
                'trade_tier': IsPartialDict(tier='low'),
            }
            if annotated:
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            '80:0': IsPartialDict(configuration_ids=Contains(config)),
                        }
                    )
                )
            yield Case(
                id=f'sorceress-mf-gloves/{slug}/{label}',
                item=item,
                context=context,
                scenario=scenario,
                covers=(role,),
                expected={
                    'assessment': IsPartialDict(**assessment),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                absent_stat_configurations={'19:0': (config,), '79:0': (config,)},
                absent_configurations=() if annotated else (config,),
                report_contains=('Chance Guards', 'Trade tier: low'),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/variants/2',
                    'third-parties/d2data/json/uniqueitems.json:/104',
                ),
            )


CASES = tuple(cases())
