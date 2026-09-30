"""Abyss mana-support mercenary: low rolls, recipe and bearer boundaries."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'abyss-warlock-insight-act-2-might'
ITEM = Item(
    'Partizan',
    'normal',
    'Insight',
    (
        (151, 120, 12),
        (17, 0, 200),
        (18, 0, 200),
        (97, 9, 1),
        (119, 0, 180),
        (105, 0, 35),
        (0, 0, 5),
        (1, 0, 5),
        (2, 0, 5),
        (3, 0, 5),
        (21, 0, 9),
    ),
    runeword='Insight',
    sockets=4,
    socket_contents='filled',
)


def cases():
    context = {'player_class': 'Warlock', 'mercenary_type': 'Act 2 Might'}
    scenarios = (
        ('low-rolls', ITEM, context, 'positive'),
        ('ethereal-elite', replace(ITEM, base='Giant Thresher', ethereal=True), context, 'positive'),
        ('superior', replace(ITEM, rarity='superior'), context, 'positive'),
        ('low-quality', replace(ITEM, rarity='low_quality'), context, 'positive'),
        ('illegal-capacity', replace(ITEM, base='Bardiche'), context, 'negative'),
        ('wrong-merc', ITEM, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'negative'),
        ('unknown-merc', ITEM, {'player_class': 'Warlock'}, 'unknown'),
        ('empty-sockets', replace(ITEM, socket_contents='empty'), context, 'negative'),
    )
    scenarios += tuple(
        (quality + '-' + label, replace(ITEM, rarity=quality), ctx, scenario)
        for quality in ('superior', 'low_quality')
        for label, ctx, scenario in (
            ('wrong-merc', {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'negative'),
            ('unknown-merc', {'player_class': 'Warlock'}, 'unknown'),
        )
    )
    result = []
    for label, item, ctx, scenario in scenarios:
        expected = {
            'roles': Contains(
                IsPartialDict(
                    id=ROLE,
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
                        key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                        for key in ('151:120', '17:0', '97:9', '119:0', '0:0', '2:0', '21:0')
                    }
                )
            )
        result.append(
            Case(
                id='abyss/insight/' + label,
                item=item,
                context=ctx,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(ROLE,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (ROLE + '-stats',),
                absent_stat_configurations=dict.fromkeys(('105:0', '1:0', '3:0'), (ROLE + '-stats',)),
                report_contains=('Insight',),
                evidence=(
                    'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__abyss-warlock-build-guide.html/sections/39',
                ),
            )
        )
    return tuple(result)


CASES = cases()
