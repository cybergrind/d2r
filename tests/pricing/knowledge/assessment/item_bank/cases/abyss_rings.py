"""Source-specific Abyss rings: spell utility, affix minima and optional charges."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


RESISTS = (39, 41, 43, 45)
EXAMPLES = (
    (
        'soj',
        Item(
            'Ring',
            'unique',
            'The Stone of Jordan',
            ((127, 0, 1), (9, 0, 20 * 256), (77, 0, 25), (50, 0, 1), (51, 0, 12)),
        ),
        ('127:0', '9:0', '77:0'),
    ),
    (
        'bk',
        Item(
            'Ring',
            'unique',
            "Bul-Kathos' Wedding Band",
            ((127, 0, 1), (216, 0, 4 * 256), (60, 0, 3), (11, 0, 50 * 256)),
        ),
        ('127:0', '216:0'),
    ),
    (
        'opalvein',
        Item(
            'Ring',
            'unique',
            'Opalvein',
            ((105, 0, 10), (357, 0, 5), *((s, 0, 6) for s in RESISTS), (86, 0, 1), (138, 0, 1), (195, 25487, 2)),
        ),
        ('105:0', '357:0', '39:0', '41:0', '43:0', '45:0', '86:0', '138:0'),
    ),
    (
        'sling',
        Item(
            'Ring', 'unique', 'Sling', ((97, 411, 1), (105, 0, 10), (358, 0, 3), (1, 0, 10), (150, 0, 15), (80, 0, 10))
        ),
        ('97:411', '105:0', '358:0', '1:0', '80:0'),
    ),
    (
        'crafted',
        Item(
            'Ring',
            'crafted',
            'Bone Turn',
            ((105, 0, 10), *((s, 0, 8) for s in RESISTS), (60, 0, 1), (7, 0, 10 * 256), (0, 0, 1)),
        ),
        ('105:0', '39:0', '41:0', '43:0', '45:0', '7:0', '0:0'),
    ),
    (
        'rare',
        Item('Ring', 'rare', 'Corruption Eye', ((105, 0, 10), *((s, 0, 8) for s in RESISTS))),
        ('105:0', '39:0', '41:0', '43:0', '45:0'),
    ),
    (
        'magic',
        Item('Ring', 'magic', None, ((105, 0, 10), *((s, 0, 12) for s in RESISTS))),
        ('105:0', '39:0', '41:0', '43:0', '45:0'),
    ),
)


def cases():
    for slug, item, keys in EXAMPLES:
        role = (
            'abyss-warlock-build-guide-bk-ring-rings-utility-alternative'
            if slug == 'bk'
            else 'abyss-warlock-table-ring-' + slug
        )
        rows = [
            ('minimum', item, {'player_class': 'Warlock'}, 'true', keys),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false', ()),
            ('unknown-class', item, {}, 'unknown', ()),
            ('ethereal', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'false', ()),
            ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Warlock'}, 'unknown', ()),
            ('invalid-sockets', replace(item, sockets=1), {'player_class': 'Warlock'}, 'false', ()),
        ]
        if slug in ('crafted', 'rare', 'magic'):
            for label, raw, complete, truth in (
                ('below-fcr', tuple((s, p, 9 if s == 105 else v) for s, p, v in item.raw_stats), True, 'false'),
                (
                    'below-resist-tier',
                    tuple((s, p, (11 if slug == 'magic' else 7) if s == 39 else v) for s, p, v in item.raw_stats),
                    True,
                    'false',
                ),
                ('missing-resistance', tuple(t for t in item.raw_stats if t[0] != 39), True, 'false'),
                ('unknown-resistance', tuple(t for t in item.raw_stats if t[0] != 39), False, 'unknown'),
            ):
                rows.append(
                    (label, replace(item, raw_stats=raw, complete=complete), {'player_class': 'Warlock'}, truth, ())
                )
        if slug == 'crafted':
            rows.append(
                (
                    'optional-mf',
                    replace(item, raw_stats=(*item.raw_stats, (80, 0, 25))),
                    {'player_class': 'Warlock'},
                    'true',
                    (*keys, '80:0'),
                )
            )
        if slug == 'rare':
            for label, remaining in (('telekinesis', 32), ('depleted-telekinesis', 0)):
                rows.append(
                    (
                        label,
                        replace(
                            item, raw_stats=(*item.raw_stats, (0, 0, 20), (80, 0, 10), (204, 2757, 32 << 8 | remaining))
                        ),
                        {'player_class': 'Warlock'},
                        'true',
                        (*keys, '0:0', '80:0', *(('204:2757',) if remaining else ())),
                    )
                )
        if slug == 'opalvein':
            for label, bonus in (
                ('fire-variant', ((329, 0, 5),)),
                ('physical-variant', ((17, 0, 40), (18, 0, 40))),
                ('unknown-random-variant', ()),
            ):
                rows.append(
                    (
                        label,
                        replace(item, raw_stats=(*tuple(t for t in item.raw_stats if t[0] != 357), *bonus)),
                        {'player_class': 'Warlock'},
                        'true',
                        tuple(k for k in keys if k != '357:0'),
                    )
                )
        for label, candidate, context, truth, expected_keys in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in expected_keys}
                    )
                )
            excluded = dict.fromkeys(
                ('60:0', '150:0', '195:25487', '50:0', '51:0', '329:0', '17:0', '18:0', '97:43', '97:54'),
                (role + '-stats',),
            )
            if slug == 'rare' and label != 'telekinesis':
                excluded['204:2757'] = (role + '-stats',)
            report = ('2% Chance to cast level 15 Flame Wave on attack',) if slug == 'opalvein' else ('Ring',)
            yield Case(
                id=f'abyss/rings/{slug}/{label}',
                item=candidate,
                context=context,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                absent_stat_configurations=excluded,
                report_contains=report,
                evidence=(
                    'pricing/data/appraisal-guide-sections.json',
                    'third-parties/d2data/json/uniqueitems.json',
                    'third-parties/d2data/json/magicprefix.json',
                ),
            )


CASES = tuple(cases())
