"""Remaining early mercenary gear, including the exact resistance rune fillers."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


RES = tuple((stat, 0, 30) for stat in (39, 41, 43, 45))
EXAMPLES = (
    (
        'hustle',
        213,
        Item(
            'Archon Plate',
            'normal',
            'Hustle (armor)',
            (
                (93, 0, 40),
                (96, 0, 65),
                (99, 0, 20),
                (2, 0, 10),
                (97, 29, 6),
                (39, 0, 10),
                (41, 0, 10),
                (43, 0, 10),
                (45, 0, 10),
            ),
            runeword='Hustle (armor)',
            sockets=3,
            socket_contents='filled',
        ),
        ('93:0', '96:0', '99:0', '2:0'),
        ('97:29',),
    ),
    (
        'bulwark',
        229,
        Item(
            'Death Mask',
            'normal',
            'Bulwark',
            ((60, 0, 4), (36, 0, 10), (34, 0, 7), (99, 0, 20), (74, 0, 30), (16, 0, 75), (76, 0, 5), (3, 0, 10)),
            runeword='Bulwark',
            sockets=3,
            socket_contents='filled',
        ),
        ('60:0', '36:0', '34:0', '99:0'),
        ('3:0',),
    ),
    (
        'undead-crown',
        230,
        Item(
            'Crown',
            'unique',
            'Undead Crown',
            ((60, 0, 5), (45, 0, 50), (118, 0, 1), (16, 0, 30), (122, 0, 50), (124, 0, 50), (97, 69, 3)),
        ),
        ('60:0', '45:0', '118:0', '122:0', '124:0'),
        ('97:69',),
    ),
    (
        'resistance-armor',
        217,
        Item(
            'Dusk Shroud',
            'normal',
            raw_stats=RES,
            sockets=4,
            socket_contents='filled',
            socket_items=tuple(SocketItem(name) for name in ('Ral Rune', 'Ort Rune', 'Thul Rune', 'Tal Rune')),
        ),
        ('39:0', '41:0', '43:0', '45:0'),
        (),
    ),
    (
        'resistance-mask',
        232,
        Item(
            'Mask',
            'normal',
            raw_stats=tuple(r for r in RES if r[0] != 43),
            sockets=3,
            socket_contents='filled',
            socket_items=tuple(SocketItem(name) for name in ('Ral Rune', 'Ort Rune', 'Tal Rune')),
        ),
        ('39:0', '41:0', '45:0'),
        (),
    ),
)


def cases():
    result = []
    for slug, span, item, keys, useless in EXAMPLES:
        role = 'zeal-paladin-early-merc-' + slug
        context = {'player_class': 'Paladin', 'mercenary_type': 'Act 5 Frenzy'}
        rows = [
            ('frenzy', 'positive', item, context),
            ('might', 'positive', item, {**context, 'mercenary_type': 'Act 2 Might'}),
            ('ethereal', 'positive', replace(item, ethereal=True), context),
            ('unknown-merc', 'unknown', item, {'player_class': 'Paladin'}),
            ('wrong-merc', 'negative', item, {**context, 'mercenary_type': 'Act 5 Bash'}),
            ('wrong-class', 'negative', item, {**context, 'player_class': 'Sorceress'}),
            ('unknown-sockets', 'unknown', replace(item, sockets=None), context),
        ]
        if slug.startswith('resistance-'):
            rows.extend(
                [
                    (
                        'different-base',
                        'negative',
                        replace(item, base='Archon Plate' if slug == 'resistance-armor' else 'Death Mask'),
                        context,
                    ),
                    (
                        'wrong-filler',
                        'negative',
                        replace(item, socket_items=(SocketItem('El Rune'), *item.socket_items[1:])),
                        context,
                    ),
                    ('unread-fillers', 'unknown', replace(item, socket_items=()), context),
                    ('empty', 'negative', replace(item, socket_contents='empty', socket_items=()), context),
                ]
            )
        elif item.runeword:
            rows.append(('wrong-sockets', 'negative', replace(item, sockets=2), context))
        for label, scenario, candidate, loadout in rows:
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        rule_trace=IsPartialDict(
                            truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario],
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
            if label == 'different-base':
                expected['roles'] = ~Contains(IsPartialDict(id=role))
            result.append(
                Case(
                    id=f'zeal/merc-tail/{slug}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    absent_stat_configurations=dict.fromkeys(useless, (role + '-stats',)),
                    report_contains=(candidate.name or candidate.base,),
                    evidence=(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        f'pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
