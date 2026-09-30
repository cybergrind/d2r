"""Named throwing weapons with distinct replenishment and repair policies."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        'wraith-flight',
        Item(
            'Ghost Glaive',
            'unique',
            'Wraith Flight',
            ((17, 0, 150), (18, 0, 150), (60, 0, 9), (138, 0, 15), (253, 0, 40)),
            ethereal=True,
        ),
        ('double-throw-barbarian-guide',),
        'Barbarian',
        ('weapon', 'off-hand'),
        ('17:0', '60:0', '138:0'),
        {17: 190, 18: 190, 60: 13},
    ),
    (
        'titan-s-revenge',
        Item(
            'Ceremonial Javelin',
            'unique',
            "Titan's Revenge",
            (
                (83, 0, 2),
                (188, 2, 2),
                (17, 0, 150),
                (18, 0, 150),
                (96, 0, 30),
                (253, 0, 30),
                (0, 0, 20),
                (2, 0, 20),
                (60, 0, 5),
            ),
        ),
        ('lightning-fury-amazon-guide', 'lightning-strike-amazon'),
        'Amazon',
        ('weapon',),
        ('83:0', '188:2', '96:0'),
        {17: 200, 18: 200, 60: 9},
    ),
    (
        'thunderstroke',
        Item(
            'Matriarchal Javelin',
            'unique',
            'Thunderstroke',
            ((188, 2, 2), (334, 0, 15), (93, 0, 15), (17, 0, 150), (18, 0, 150), (107, 20, 3)),
        ),
        ('lightning-fury-amazon-guide', 'lightning-strike-amazon'),
        'Amazon',
        ('weapon',),
        ('188:2', '334:0', '93:0'),
        {17: 200, 18: 200, 188: 4},
    ),
)


def cases():
    for slug, item, builds, klass, slots, keys, maxima in SPECS:
        roles = tuple(f'{build}-{slug}-{slot}-named-throwing-alternative' for build in builds for slot in slots)
        rows = [
            ('minimum', item, {'player_class': klass}, 'true'),
            (
                'maximum',
                replace(item, raw_stats=tuple((s, layer, maxima.get(s, v)) for s, layer, v in item.raw_stats)),
                {'player_class': klass},
                'true',
            ),
            (
                'opposite-ethereal',
                replace(item, ethereal=not item.ethereal),
                {'player_class': klass},
                'true' if slug == 'titan-s-revenge' else 'false',
            ),
            (
                'unknown-ethereal',
                replace(item, ethereal=None),
                {'player_class': klass},
                'true' if slug == 'titan-s-revenge' else 'unknown',
            ),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('socketed', replace(item, sockets=1), {'player_class': klass}, 'false'),
            ('unknown-sockets', replace(item, sockets=None), {'player_class': klass}, 'unknown'),
        ]
        if slug == 'titan-s-revenge':
            rows.append(('upgraded', replace(item, base='Matriarchal Javelin'), {'player_class': klass}, 'true'))
        if slug != 'thunderstroke':
            rows.append(
                (
                    'unread-replenishment',
                    replace(item, raw_stats=tuple(r for r in item.raw_stats if r[0] != 253)),
                    {'player_class': klass},
                    'unknown',
                )
            )
        for label, candidate, context, truth in rows:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*(r + '-stats' for r in roles))) for key in keys}
                    )
                )
            yield Case(
                id=f'throwing-sustain/{slug}/{label}',
                item=candidate,
                context=context,
                expected={'assessment': IsPartialDict(**expected)},
                covers=roles,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else tuple(r + '-stats' for r in roles),
                absent_stat_configurations={'107:20': tuple(r + '-stats' for r in roles)}
                if slug == 'thunderstroke'
                else {},
                report_contains=('Trade tier:',),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json',
                    *(f'pricing/data/wp-a-builds.json:/{build}/slots' for build in builds),
                ),
            )


CASES = tuple(cases())
