"""Native grimoire effects and observed Um totals remain distinct for Abyss."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


EXAMPLES = (
    (
        'mephistos',
        Item(
            'Occult Tome',
            'unique',
            "Ars Dul'Mephistos",
            (
                (83, 7, 2),
                (105, 0, 20),
                (99, 0, 30),
                (16, 0, 140),
                (358, 0, 10),
                (80, 0, 10),
                (17, 0, 70),
                (18, 0, 70),
                (119, 0, 50),
                (201, 3804, 15),
            ),
        ),
        ('83:7', '105:0', '99:0', '16:0', '358:0', '80:0'),
        '15% Chance to cast level 28 Blizzard when struck',
    ),
    (
        'diabolos',
        Item(
            'Blasphemous Grimoire',
            'unique',
            "Ars Al'Diabolos",
            (
                (188, 58, 2),
                (105, 0, 25),
                (16, 0, 170),
                (329, 0, 15),
                (89, 0, 5),
                (138, 0, 5),
                (39, 0, 20),
                (107, 401, 3),
                (201, 4929, 15),
            ),
        ),
        ('188:58', '105:0', '16:0', '138:0', '39:0'),
        '15% Chance to cast level 1 Terror when struck',
    ),
)


def cases():
    for slug, item, keys, trigger in EXAMPLES:
        role = 'abyss-warlock-table-grimoire-' + slug
        rows = [
            ('minimum', item, {'player_class': 'Warlock'}, 'true', keys),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false', ()),
            ('unknown-class', item, {}, 'unknown', ()),
            ('ethereal', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'false', ()),
            ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Warlock'}, 'unknown', ()),
            ('empty-socket', replace(item, sockets=1), {'player_class': 'Warlock'}, 'true', keys),
            ('unknown-sockets', replace(item, sockets=None), {'player_class': 'Warlock'}, 'unknown', ()),
            ('impossible-sockets', replace(item, sockets=2), {'player_class': 'Warlock'}, 'false', ()),
            ('unidentified', replace(item, identified=False), {'player_class': 'Warlock'}, 'false', ()),
        ]
        if slug == 'mephistos':
            socketed = replace(
                item,
                sockets=1,
                socket_contents='filled',
                socket_items=(SocketItem('Um Rune'),),
                raw_stats=(*item.raw_stats, (194, 0, 1)),
            )
            totals = (*socketed.raw_stats, *((s, 0, 22) for s in (39, 41, 43, 45)))
            for label, candidate, resists in (
                ('um-observed-totals', replace(socketed, raw_stats=totals), True),
                ('um-child-only', socketed, False),
                (
                    'unknown-child-observed-totals',
                    replace(socketed, raw_stats=totals, socket_contents='unknown', socket_items=()),
                    True,
                ),
                ('unknown-contents', replace(socketed, socket_contents='unknown', socket_items=()), False),
            ):
                rows.append(
                    (
                        label,
                        candidate,
                        {'player_class': 'Warlock'},
                        'true',
                        (*keys, *((f'{s}:0' for s in (39, 41, 43, 45)) if resists else ())),
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
                ('17:0', '18:0', '119:0', '201:3804', '201:4929', '329:0', '107:401'), (role + '-stats',)
            )
            if slug == 'mephistos' and label not in ('um-observed-totals', 'unknown-child-observed-totals'):
                excluded.update(dict.fromkeys(('39:0', '41:0', '43:0', '45:0'), (role + '-stats',)))
            yield Case(
                id=f'abyss/grimoires/{slug}/{label}',
                item=candidate,
                context=context,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                absent_stat_configurations=excluded,
                report_contains=(candidate.base, trigger, *(('Um',) if label.startswith('um-') else ())),
                evidence=(
                    'pricing/raw/mr/planners/gsg0p0l0.json',
                    'third-parties/d2data/json/uniqueitems.json',
                    'third-parties/d2data/json/gems.json',
                ),
            )


CASES = tuple(cases())
