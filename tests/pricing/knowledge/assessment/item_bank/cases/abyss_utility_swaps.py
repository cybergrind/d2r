"""Abyss prebuff and travel alternatives do not require perfect example rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CTA = Item(
    'Crystal Sword',
    'normal',
    'Call to Arms',
    ((97, 149, 1), (97, 155, 2), (97, 146, 1), (127, 0, 1), (93, 0, 40), (17, 0, 250), (18, 0, 250)),
    sockets=5,
    socket_contents='filled',
    runeword='Call to Arms',
)
STAFF = Item('Long Staff', 'magic', raw_stats=((204, 54 * 64 + 6, (52 << 8) | 1),))


def cases():
    for slug, item, keys in [('cta', CTA, ('97:149', '97:155', '127:0')), ('teleport', STAFF, ('204:3462',))]:
        role = 'abyss-warlock-player-utility-' + slug
        rows = [
            ('minimum', item, {'player_class': 'Warlock'}, 'positive', 'true'),
            ('ethereal', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'positive', 'true'),
            ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Warlock'}, 'positive', 'true'),
            ('wrong-class', item, {'player_class': 'Paladin'}, 'negative', 'false'),
            ('unknown-class', item, {}, 'unknown', 'unknown'),
        ]
        if slug == 'cta':
            rows += [
                (q, replace(item, rarity=q), {'player_class': 'Warlock'}, 'positive', 'true')
                for q in ('superior', 'low_quality')
            ]
            rows += [
                ('empty', replace(item, socket_contents='empty'), {'player_class': 'Warlock'}, 'negative', 'false'),
                ('unknown-sockets', replace(item, sockets=None), {'player_class': 'Warlock'}, 'unknown', 'unknown'),
                ('wrong-base', replace(item, base='Broad Sword'), {'player_class': 'Warlock'}, 'negative', 'false'),
                ('unread-shouts', replace(item, raw_stats=()), {'player_class': 'Warlock'}, 'unknown', 'unknown'),
                (
                    'missing-orders',
                    replace(item, raw_stats=((97, 155, 2),), complete=True),
                    {'player_class': 'Warlock'},
                    'negative',
                    'false',
                ),
            ]
        else:
            rows += [
                ('rare', replace(item, rarity='rare'), {'player_class': 'Warlock'}, 'positive', 'true'),
                (
                    'depleted',
                    replace(item, raw_stats=((204, 3462, 52 << 8),)),
                    {'player_class': 'Warlock'},
                    'negative',
                    'true',
                ),
                (
                    'ethereal-depleted',
                    replace(item, ethereal=True, raw_stats=((204, 3462, 52 << 8),)),
                    {'player_class': 'Warlock'},
                    'negative',
                    'true',
                ),
                ('unread-charges', replace(item, raw_stats=()), {'player_class': 'Warlock'}, 'unknown', 'unknown'),
                (
                    'wrong-charge',
                    replace(item, raw_stats=((204, 48 * 64 + 6, (52 << 8) | 1),), complete=True),
                    {'player_class': 'Warlock'},
                    'negative',
                    'false',
                ),
            ]
        for label, candidate, context, scenario, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            yield Case(
                id=f'abyss/utility-swaps/{slug}/{label}',
                item=candidate,
                context=context,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                absent_stat_configurations=dict.fromkeys(('17:0', '18:0', '93:0', '97:146'), (role + '-stats',)),
                evidence=('pricing/raw/mr/planners/x2cpo0l5.json',),
            )


CASES = tuple(cases())
