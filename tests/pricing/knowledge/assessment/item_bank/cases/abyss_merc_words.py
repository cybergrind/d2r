"""Abyss table runewords: native low rolls, legal quality and context boundaries."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.zeal_early_merc import EXAMPLES as EARLY
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_merc_tail import EXAMPLES as TAIL
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = [
    (
        slug,
        {'smoke': 98, 'lionheart': 99, 'temper': 113}[slug],
        replace(item, base={'smoke': 'Dusk Shroud', 'lionheart': 'Mage Plate', 'temper': 'Bone Visage'}[slug]),
        keys,
    )
    for slug, _, item, keys in EARLY
    if slug in ('smoke', 'lionheart', 'temper')
]
EXAMPLES += [(slug, 109, item, keys) for slug, _, item, keys, _ in TAIL if slug == 'bulwark']
EXAMPLES += [
    (
        'treachery',
        102,
        Item(
            'Mage Plate',
            'normal',
            'Treachery',
            ((93, 0, 45), (201, 267 * 64 + 15, 5), (99, 0, 20), (43, 0, 30), (83, 6, 2)),
            sockets=3,
            socket_contents='filled',
            runeword='Treachery',
        ),
        ('93:0', '201:17103', '99:0', '43:0'),
    ),
    (
        'duress',
        103,
        Item(
            'Wyrmhide',
            'normal',
            'Duress',
            (
                (136, 0, 15),
                (135, 0, 33),
                (17, 0, 10),
                (18, 0, 10),
                (16, 0, 150),
                (99, 0, 40),
                (39, 0, 15),
                (41, 0, 15),
                (43, 0, 45),
                (45, 0, 15),
            ),
            sockets=3,
            socket_contents='filled',
            runeword='Duress',
        ),
        ('136:0', '135:0', '17:0', '99:0'),
    ),
    (
        'fortitude',
        107,
        Item(
            'Sacred Armor',
            'normal',
            'Fortitude',
            (
                (17, 0, 300),
                (18, 0, 300),
                (16, 0, 200),
                (39, 0, 25),
                (41, 0, 25),
                (43, 0, 25),
                (45, 0, 25),
                (105, 0, 25),
            ),
            ethereal=True,
            sockets=4,
            socket_contents='filled',
            runeword='Fortitude',
        ),
        ('17:0', '16:0', '39:0'),
    ),
]


def cases():
    context = {'player_class': 'Warlock', 'mercenary_type': 'Act 2 Might'}
    for slug, span, item, keys in EXAMPLES:
        role = 'abyss-warlock-merc-table-' + slug
        rows = [('native-low', item, context, 'positive')]
        rows += [
            (quality, replace(item, rarity=quality), context, 'positive') for quality in ('superior', 'low_quality')
        ]
        rows += [
            ('wrong-merc', item, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'negative'),
            ('unknown-merc', item, {'player_class': 'Warlock'}, 'unknown'),
            ('wrong-class', item, {**context, 'player_class': 'Paladin'}, 'negative'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            ('empty', replace(item, socket_contents='empty'), context, 'negative'),
            (
                'wrong-base',
                replace(item, base='Cap' if slug in ('bulwark', 'temper') else 'Quilted Armor'),
                context,
                'negative',
            ),
            ('ethereal', replace(item, ethereal=True), context, 'positive'),
            (
                'unknown-ethereal',
                replace(item, ethereal=None),
                context,
                'unknown' if slug == 'fortitude' else 'positive',
            ),
        ]
        if slug == 'fortitude':
            rows.append(('nonethereal', replace(item, ethereal=False), context, 'negative'))
        for label, candidate, ctx, scenario in rows:
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
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            yield Case(
                id=f'abyss/merc-words/{slug}/{label}',
                item=candidate,
                context=ctx,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                absent_stat_configurations=dict.fromkeys(
                    {'treachery': ('83:6',), 'fortitude': ('105:0',)}.get(slug, ()), (role + '-stats',)
                ),
                report_contains=(item.name,),
                evidence=(
                    'pricing/data/appraisal-guide-sections.json:/sources/'
                    f'pricing~1raw~1mr~1guides__abyss-warlock-build-guide.html/item_spans/{span}',
                ),
            )


CASES = tuple(cases())
