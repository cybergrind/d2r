"""Abyss amulet examples preserve skill tabs, cast tiers and charged-skill state."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    (
        'crafted',
        Item('Amulet', 'crafted', 'Entropy Gorget', ((83, 7, 2), (105, 0, 15), (27, 0, 4), (9, 0, 10 * 256))),
        ('83:7', '105:0', '27:0', '9:0'),
        15,
    ),
    ('rare', Item('Amulet', 'rare', 'Rare Amulet', ((83, 7, 2), (105, 0, 10))), ('83:7', '105:0'), 10),
    ('magic', Item('Amulet', 'magic', None, ((188, 58, 3), (105, 0, 10))), ('188:58', '105:0'), 10),
    (
        'entropy',
        Item(
            'Amulet',
            'unique',
            'Entropy Locket',
            ((357, 0, 5), (105, 0, 5), (41, 0, 25), (77, 0, 10), (35, 0, 8), (198, 25555, 4)),
        ),
        ('357:0', '105:0', '41:0', '77:0', '35:0'),
        None,
    ),
    (
        'beads',
        Item('Amulet', 'set', 'Telling of Beads', ((127, 0, 1), (43, 0, 18), (45, 0, 35), (78, 0, 8))),
        ('127:0', '43:0', '45:0'),
        None,
    ),
    (
        'maras',
        Item(
            'Amulet',
            'unique',
            "Mara's Kaleidoscope",
            (
                (127, 0, 2),
                (39, 0, 20),
                (41, 0, 20),
                (43, 0, 20),
                (45, 0, 20),
                (0, 0, 5),
                (1, 0, 5),
                (2, 0, 5),
                (3, 0, 5),
            ),
        ),
        ('127:0', '39:0', '41:0', '43:0', '45:0', '0:0', '1:0', '2:0', '3:0'),
        None,
    ),
)


def cases():
    for slug, item, keys, fcr in EXAMPLES:
        role = 'abyss-warlock-table-amulet-' + slug
        rows = [
            ('minimum', item, {'player_class': 'Warlock'}, 'true', keys),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false', ()),
            ('unknown-class', item, {}, 'unknown', ()),
            ('ethereal', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'false', ()),
            ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Warlock'}, 'unknown', ()),
            ('invalid-sockets', replace(item, sockets=1), {'player_class': 'Warlock'}, 'false', ()),
        ]
        if fcr:
            rows += [
                (
                    'below-fcr',
                    replace(item, raw_stats=tuple((i, p, fcr - 1 if i == 105 else v) for i, p, v in item.raw_stats)),
                    {'player_class': 'Warlock'},
                    'false',
                    (),
                ),
                (
                    'wrong-skill',
                    replace(
                        item,
                        raw_stats=((188, 56, 3) if slug == 'magic' else (83, 1, 2), *item.raw_stats[1:]),
                        complete=True,
                    ),
                    {'player_class': 'Warlock'},
                    'false',
                    (),
                ),
                (
                    'unknown-skill',
                    replace(item, raw_stats=item.raw_stats[1:]),
                    {'player_class': 'Warlock'},
                    'unknown',
                    (),
                ),
            ]
        if slug == 'crafted':
            rows.append(
                (
                    'affixes',
                    replace(
                        item,
                        raw_stats=(*item.raw_stats, (39, 0, 20), (41, 0, 20), (43, 0, 20), (45, 0, 20), (80, 0, 25)),
                    ),
                    {'player_class': 'Warlock'},
                    'true',
                    (*keys, '39:0', '41:0', '43:0', '45:0', '80:0'),
                )
            )
        if slug == 'rare':
            extra = ((39, 0, 20), (41, 0, 20), (43, 0, 20), (45, 0, 20), (0, 0, 30), (80, 0, 10))
            for label, remaining in (('teleport', 27), ('depleted-teleport', 0)):
                rows.append(
                    (
                        label,
                        replace(item, raw_stats=(*item.raw_stats, *extra, (204, 3459, 27 << 8 | remaining))),
                        {'player_class': 'Warlock'},
                        'true',
                        (*keys, '39:0', '41:0', '43:0', '45:0', '0:0', '80:0', *(('204:3459',) if remaining else ())),
                    )
                )
        if slug == 'maras':
            rows.append(('no-full-breakpoint', item, {'player_class': 'Warlock', 'player_total_fcr': 0}, 'true', keys))
        for label, candidate, context, truth, expected_keys in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in expected_keys}
                    )
                )
            excluded = (
                {'198:25555': (role + '-stats',)}
                if slug == 'entropy'
                else {'78:0': (role + '-stats',)}
                if slug == 'beads'
                else {}
            )
            if slug == 'rare':
                excluded['97:54'] = (role + '-stats',)
                if label != 'teleport':
                    excluded['204:3459'] = (role + '-stats',)
            report = ('4% Chance to cast level 19 Miasma Chain on striking',) if slug == 'entropy' else ('Amulet',)
            yield Case(
                id=f'abyss/amulets/{slug}/{label}',
                item=candidate,
                context=context,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                absent_stat_configurations=excluded,
                report_contains=report,
                evidence=('pricing/data/appraisal-guide-sections.json', 'third-parties/d2data/json/properties.json'),
            )


CASES = tuple(cases())
