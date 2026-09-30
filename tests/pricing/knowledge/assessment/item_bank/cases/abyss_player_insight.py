"""Player caster Insight must not inherit physical mercenary stat priorities."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'abyss-warlock-player-insight-staff'
ITEM = Item(
    'Archon Staff',
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
        (138, 0, 2),
        (80, 0, 23),
    ),
    runeword='Insight',
    sockets=4,
    socket_contents='filled',
)


def cases():
    context = {'player_class': 'Warlock'}
    scenarios = (
        ('low-rolls', ITEM, context, 'positive'),
        ('normal-base', replace(ITEM, base='Battle Staff'), context, 'positive'),
        ('superior', replace(ITEM, rarity='superior'), context, 'positive'),
        ('low-quality', replace(ITEM, rarity='low_quality'), context, 'positive'),
        ('ethereal-casting', replace(ITEM, ethereal=True), context, 'positive'),
        ('illegal-capacity', replace(ITEM, base='Short Staff'), context, 'negative'),
        ('unknown-class', ITEM, {}, 'unknown'),
        ('wrong-class', ITEM, {'player_class': 'Paladin'}, 'negative'),
        ('empty', replace(ITEM, socket_contents='empty'), context, 'negative'),
    )
    scenarios += tuple(
        (quality + '-' + label, replace(ITEM, rarity=quality), ctx, scenario)
        for quality in ('superior', 'low_quality')
        for label, ctx, scenario in (
            ('wrong-class', {'player_class': 'Paladin'}, 'negative'),
            ('unknown-class', {}, 'unknown'),
        )
    )
    result = []
    for label, item, ctx, scenario in scenarios:
        expected = {
            'roles': Contains(
                IsPartialDict(
                    id=ROLE,
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
                        key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                        for key in ('151:120', '105:0', '0:0', '1:0', '2:0', '3:0', '138:0', '80:0')
                    }
                )
            )
        result.append(
            Case(
                id='abyss/player-insight/' + label,
                item=item,
                context=ctx,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(ROLE,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (ROLE + '-stats',),
                absent_stat_configurations=dict.fromkeys(('17:0', '18:0', '119:0', '97:9'), (ROLE + '-stats',)),
                report_contains=('Insight',),
                evidence=(
                    'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__abyss-warlock-build-guide.html/item_spans/13',
                ),
            )
        )
    return tuple(result)


CASES = cases()
