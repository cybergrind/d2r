"""Exact guide alternatives retain native identity and conditional stat benefits."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_void import RAW
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def cases():
    for slug, item, keys in (
        (
            'void',
            Item('Kriss', 'normal', 'Void', RAW, sockets=3, socket_contents='filled', runeword='Void'),
            ('127:0', '105:0', '357:0', '97:402'),
        ),
        ('arch-devil', Item('Kriss', 'magic', raw_stats=((83, 7, 2), (204, 5827, 82 << 8))), ('83:7',)),
    ):
        role = 'abyss-warlock-table-dagger-' + slug
        rows = [
            ('minimum', item, {'player_class': 'Warlock'}, 'true'),
            ('ethereal', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'true'),
            ('wrong-class', item, {'player_class': 'Paladin'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
        ]
        if slug == 'void':
            rows += [
                ('empty', replace(item, socket_contents='empty'), {'player_class': 'Warlock'}, 'false'),
                ('unknown-sockets', replace(item, sockets=None), {'player_class': 'Warlock'}, 'unknown'),
                ('blade', replace(item, base='Blade'), {'player_class': 'Warlock'}, 'true'),
            ]
            rows += [
                (q, replace(item, rarity=q), {'player_class': 'Warlock'}, 'true') for q in ('superior', 'low_quality')
            ]
        else:
            rows += [
                ('rare-equivalent', replace(item, rarity='rare'), {'player_class': 'Warlock'}, 'true'),
                (
                    'missing-prefix',
                    replace(item, raw_stats=((204, 5827, 82 << 8),), complete=True),
                    {'player_class': 'Warlock'},
                    'false',
                ),
                ('unread-charge', replace(item, raw_stats=((83, 7, 2),)), {'player_class': 'Warlock'}, 'unknown'),
                ('wrong-base', replace(item, base='Dagger'), {'player_class': 'Warlock'}, 'false'),
            ]
        for label, candidate, ctx, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if slug == 'arch-devil' and label == 'wrong-base':
                expected['roles'] = ~Contains(IsPartialDict(id=role))
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in keys}
                    )
                )
            yield Case(
                id=f'abyss/table-daggers/{slug}/{label}',
                item=candidate,
                context=ctx,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                absent_stat_configurations={'204:5827': (role + '-stats',), '204:5572': (role + '-stats',)},
                evidence=('pricing/data/appraisal-guide-sections.json',),
            )


CASES = tuple(cases())
