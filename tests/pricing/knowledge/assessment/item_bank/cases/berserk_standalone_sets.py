"""Standalone set alternatives do not assume fillers or companion set pieces."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        'immortal-king-s-will-equipment-tail-alternative',
        Item('Avenger Guard', 'set', "Immortal King's Will", ((188, 34, 2), (79, 0, 37), (80, 0, 25)), sockets=2),
        ('188:34', '79:0', '80:0'),
        80,
        40,
    ),
    (
        'trang-oul-s-girth-boots-belts-alternative',
        Item('Troll Belt', 'set', "Trang-Oul's Girth", ((153, 0, 1), (7, 0, 66 * 256), (9, 0, 25 * 256), (74, 0, 5))),
        ('153:0', '7:0', '9:0', '74:0'),
        9,
        50 * 256,
    ),
)


def cases():
    context = {'player_class': 'Barbarian', 'player_items': []}
    for slug, item, keys, variable, maximum in SPECS:
        role = 'berserk-barbarian-' + slug
        rows = [
            ('minimum-alone', item, context, 'true'),
            (
                'maximum',
                replace(
                    item, raw_stats=tuple((s, layer, maximum if s == variable else v) for s, layer, v in item.raw_stats)
                ),
                context,
                'true',
            ),
            ('unknown-companions', item, {'player_class': 'Barbarian'}, 'true'),
            ('invalid-count', replace(item, sockets=1), context, 'false'),
            ('unknown-count', replace(item, sockets=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
        ]
        if item.sockets == 2:
            rows += [
                ('exceptional', replace(item, base='Slayer Guard'), context, 'true'),
                ('elite', replace(item, base='Guardian Crown'), context, 'true'),
                ('unknown-fillers', replace(item, socket_contents='unknown'), context, 'true'),
            ]
        for label, candidate, loadout, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            yield Case(
                id=f'berserk/standalone-sets/{slug}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                report_contains=('Trade tier:',) if candidate.identified else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/berserk-barbarian/slots',
                    'third-parties/d2data/json/setitems.json',
                ),
            )


CASES = tuple(cases())
