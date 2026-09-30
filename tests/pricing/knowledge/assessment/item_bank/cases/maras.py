"""Mara's shared native stats with independently reviewed variant cast budgets."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item(
    'Amulet',
    'unique',
    "Mara's Kaleidoscope",
    (
        (127, 0, 2),
        (0, 0, 5),
        (1, 0, 5),
        (2, 0, 5),
        (3, 0, 5),
        (39, 0, 20),
        (41, 0, 20),
        (43, 0, 20),
        (45, 0, 20),
    ),
    complete=True,
)
# FCR values come from the cited variant's purpose/prose, not the generic
# class breakpoint paragraph or a generated predicate/maximum planner roll.
VARIANTS = (
    ('abyss-warlock-build-guide', 1, 'Warlock', 125),
    ('blessed-hammer-paladin', 1, 'Paladin', 125),
    ('blizzard-sorceress', 1, 'Sorceress', 105),
    ('echoing-strike-warlock-guide', 1, 'Warlock', 125),
    ('echoing-strike-warlock-guide', 2, 'Warlock', 125),
    ('echoing-strike-warlock-guide', 3, 'Warlock', None),
    ('fissure-druid', 3, 'Druid', None),
    ('lightning-sentry-assassin', 1, 'Assassin', 65),
    ('lightning-sorceress', 1, 'Sorceress', 117),
    ('summoner-necromancer-guide', 1, 'Necromancer', 125),
    ('summoner-necromancer-guide', 2, 'Necromancer', 75),
)
ALTERNATIVES = ('fire-wall-sorceress-guide', 'frozen-orb-meteor-sorceress', 'frozen-orb-sorceress', 'hydra-sorceress')


def cases():
    specs = [
        (f'{build}-{index}-maras', build, klass, fcr, f'pricing/data/wp-a-builds.json:/{build}/variants/{index}')
        for build, index, klass, fcr in VARIANTS
    ]
    specs.extend(
        (
            build + '-mara-s-kaleidoscope-caster-core-gear',
            build,
            'Sorceress',
            None,
            'pricing/raw/mr/guides__' + build + '.html:gear-options',
        )
        for build in ALTERNATIVES
    )
    result = []
    for role, build, klass, fcr, evidence in specs:
        if fcr is not None:
            contexts = (
                ('positive', {'player_class': klass, 'player_total_fcr': fcr}),
                ('negative', {'player_class': klass, 'player_total_fcr': fcr - 1}),
                ('unknown', {'player_class': klass}),
            )
        else:
            contexts = (
                ('positive', {'player_class': klass}),
                ('negative', {'player_class': 'Barbarian'}),
                ('unknown', {}),
            )
        for scenario, context in contexts:
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        build=build,
                        rule_trace=IsPartialDict(
                            truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                        ),
                    )
                ),
                'trade_tier': IsPartialDict(tier='med'),
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in ('127:0', '39:0')}
                    )
                )
            result.append(
                Case(
                    id='maras/' + role + '/' + scenario,
                    item=ITEM,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    report_contains=("Mara's Kaleidoscope", 'Trade tier: mid', 'Fire Resist +20% (20-30%)'),
                    evidence=(evidence, 'third-parties/d2data/json/uniqueitems.json:/272'),
                )
            )
    return tuple(result)


CASES = cases()
