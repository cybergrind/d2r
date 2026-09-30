"""Defensive accessories retain minimum rolls without inventing active spirits."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CHARGES = ((226, 2, 15), (236, 5, 13), (246, 7, 11))
SPECS = (
    (
        'verdungo-s-hearty-cord-defensive-alternative',
        Item(
            'Mithril Coil',
            'unique',
            "Verdungo's Hearty Cord",
            ((36, 0, 10), (3, 0, 30), (99, 0, 10), (74, 0, 10), (16, 0, 90)),
        ),
        ('36:0', '3:0', '99:0', '74:0'),
        {36: 15, 3: 40, 74: 13, 16: 140},
    ),
    (
        'wisp-projector-find-absorb-alternative',
        Item(
            'Ring',
            'unique',
            'Wisp Projector',
            (
                (144, 0, 10),
                (80, 0, 10),
                *((204, skill * 64 + level, (count << 8) | count) for skill, level, count in CHARGES),
            ),
        ),
        ('144:0', '80:0'),
        {144: 20, 80: 20},
    ),
)


def cases(build='berserk-barbarian', player_class='Barbarian', prefix='berserk', specs=SPECS):
    context = {'player_class': player_class}
    for slug, item, keys, maxima in specs:
        role = build + '-' + slug
        rows = [
            ('minimum', item, context, 'true'),
            (
                'maximum',
                replace(item, raw_stats=tuple((s, layer, maxima.get(s, v)) for s, layer, v in item.raw_stats)),
                context,
                'true',
            ),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Paladin' if player_class == 'Sorceress' else 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('invalid-socket', replace(item, sockets=1), context, 'false'),
            ('unknown-count', replace(item, sockets=None), context, 'unknown'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
        ]
        if item.base == 'Ring':
            rows += [
                (
                    'depleted-spirits',
                    replace(
                        item,
                        raw_stats=tuple((s, layer, (v >> 8) << 8 if s == 204 else v) for s, layer, v in item.raw_stats),
                    ),
                    context,
                    'true',
                ),
                (
                    'unread-spirits',
                    replace(item, raw_stats=tuple(r for r in item.raw_stats if r[0] != 204)),
                    context,
                    'true',
                ),
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
                id=f'{prefix}/defensive-accessories/{slug}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                absent_stat_configurations=dict.fromkeys(
                    (f'204:{skill * 64 + level}' for skill, level, _ in CHARGES), (role + '-stats',)
                ),
                report_contains=('Trade tier:',) if candidate.identified else (),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/slots',
                    'third-parties/d2data/json/uniqueitems.json',
                ),
            )


CASES = tuple(cases())
