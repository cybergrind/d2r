"""Caster mercenary Insight: native legality and conditional mana priorities."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# Authored from the cited variant mercenary rows, independent of executable rules.
USES = (
    ('lightning-starter', 'lightning-sorceress', 0, 'Act 2 Holy Freeze'),
    ('nova-starter', 'nova-sorceress-guide', 0, 'Act 2 Holy Freeze'),
    ('nova-standard', 'nova-sorceress-guide', 1, 'Act 2 Might'),
    ('nova-mf', 'nova-sorceress-guide', 2, 'Act 2 Holy Freeze'),
    ('blizzard-starter', 'blizzard-sorceress', 0, 'Act 2 Might'),
    ('blizzard-mf', 'blizzard-sorceress', 2, 'Act 2 Might'),
    ('poison-starter', 'poison-nova-necromancer', 0, 'Act 2 Might'),
    ('poison-budget', 'poison-nova-necromancer', 4, 'Act 2 Might'),
    ('hammer-starter', 'blessed-hammer-paladin', 0, 'Act 2 Holy Freeze'),
    ('hammer-standard', 'blessed-hammer-paladin', 1, 'Act 2 Holy Freeze'),
    ('hammer-mf', 'blessed-hammer-paladin', 2, 'Act 2 Holy Freeze'),
    ('hammer-ubers', 'blessed-hammer-paladin', 3, 'Act 2 Holy Freeze'),
)


def cases():
    result = []
    for prefix, build, variant, mercenary in USES:
        role = prefix + '-insight-merc'
        config = role + '-mana-stats'
        for quality in ('normal', 'superior', 'low_quality'):
            for scenario in ('positive', 'negative', 'unknown'):
                expected = {
                    'roles': Contains(
                        IsPartialDict(
                            id=role,
                            rule_trace=IsPartialDict(truth='false' if scenario == 'negative' else 'true'),
                        )
                    )
                }
                if scenario == 'positive':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {'151:120': IsPartialDict(configuration_ids=Contains(config), desirability='desirable')}
                        )
                    )
                result.append(
                    Case(
                        id=f'insight-mana/{prefix}/{quality}/{scenario}',
                        item=Item(
                            'Bardiche' if scenario == 'negative' else 'Bill',
                            quality,
                            'Insight',
                            ((151, 120, 12), (17, 0, 200), (18, 0, 200)),
                            ethereal=quality == 'superior',
                            sockets=4,
                            socket_contents='filled',
                            runeword='Insight',
                        ),
                        context={} if scenario == 'unknown' else {'mercenary_type': mercenary},
                        expected={'assessment': IsPartialDict(**expected)},
                        covers=(role,),
                        scenario=scenario,
                        report_contains=('Insight', 'Meditation'),
                        absent_configurations=() if scenario == 'positive' else (config,),
                        absent_stat_configurations={'17:0': (config,), '18:0': (config,)},
                        evidence=(
                            f'pricing/data/wp-a-builds.json:/{build}/variants/{variant}/merc',
                            'third-parties/d2data/json/runes.json:/Insight',
                        ),
                    )
                )
    return tuple(result)


CASES = cases()
