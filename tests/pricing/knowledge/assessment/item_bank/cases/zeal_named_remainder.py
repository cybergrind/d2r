"""Named Zeal alternatives: socket preparation, repair and native upgrade chains."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


WORDS = (
    (
        'Rune Master',
        'Ettin Axe',
        60,
        ((17, 0, 300), (18, 0, 300), (44, 0, 5), (153, 0, 1), (152, 0, 1), (93, 0, 30), (141, 0, 40)),
        ('17:0', '18:0', '44:0', '153:0', '93:0', '141:0'),
    ),
    (
        'Herald of Zakarum',
        'Gilded Shield',
        69,
        (
            (83, 3, 2),
            (188, 24, 2),
            (16, 0, 150),
            (102, 0, 30),
            (20, 0, 30),
            (0, 0, 20),
            (3, 0, 20),
            (119, 0, 20),
            (39, 0, 50),
            (41, 0, 50),
            (43, 0, 50),
            (45, 0, 50),
        ),
        ('83:3', '188:24', '16:0', '102:0', '20:0', '0:0', '3:0', '119:0', '39:0', '41:0', '43:0', '45:0'),
    ),
    (
        'Stormshield',
        'Monarch',
        71,
        ((214, 0, 30), (36, 0, 35), (0, 0, 30), (152, 0, 1), (102, 0, 35), (41, 0, 25), (20, 0, 25), (43, 0, 60)),
        ('214:0', '36:0', '0:0', '102:0', '41:0', '20:0', '43:0'),
    ),
    (
        "Skullder's Ire",
        'Russet Armor',
        116,
        ((127, 0, 1), (240, 0, 10), (16, 0, 160), (35, 0, 10), (252, 0, 20)),
        ('127:0', '240:0', '16:0', '35:0', '252:0'),
    ),
)


def cases():
    result = []
    for name, base, span, raw, keys in WORDS:
        slug = name.lower().replace("'", '').replace(' ', '-')
        role = 'zeal-paladin-' + slug + '-named-alternative'
        item = Item(base, 'unique', name, raw)
        if name == 'Rune Master':
            item = replace(
                item,
                ethereal=True,
                sockets=5,
                socket_contents='filled',
                socket_items=(
                    SocketItem('Zod Rune'),
                    SocketItem('Lo Rune'),
                    SocketItem('Lo Rune'),
                    SocketItem('Jewel', ((17, 0, 40), (18, 0, 40), (93, 0, 15))),
                    SocketItem('Jewel', ((17, 0, 40), (18, 0, 40), (93, 0, 15))),
                ),
            )
        variants = [
            ('low-rolls', item, {'player_class': 'Paladin'}, 'positive'),
            ('unknown-class', item, {}, 'unknown'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'negative'),
        ]
        if name == 'Rune Master':
            variants += [
                ('nonethereal', replace(item, ethereal=False), {'player_class': 'Paladin'}, 'negative'),
                ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Paladin'}, 'unknown'),
                (
                    'needs-zod',
                    replace(
                        item,
                        raw_stats=((17, 0, 220), (18, 0, 220), (44, 0, 5), (153, 0, 1)),
                        socket_items=(),
                        socket_contents='empty',
                    ),
                    {'player_class': 'Paladin'},
                    'negative',
                ),
                (
                    'invalid-socket-count',
                    replace(item, sockets=2, socket_items=()),
                    {'player_class': 'Paladin'},
                    'negative',
                ),
            ]
            for count in (3, 4):
                children = (SocketItem('Zod Rune'), SocketItem('Lo Rune'), SocketItem('Lo Rune'))
                stats = ((17, 0, 220), (18, 0, 220), (44, 0, 5), (153, 0, 1), (152, 0, 1), (141, 0, 40))
                if count == 4:
                    children += (SocketItem('Jewel', ((17, 0, 40), (18, 0, 40), (93, 0, 15))),)
                    stats = (
                        (17, 0, 260),
                        (18, 0, 260),
                        (44, 0, 5),
                        (153, 0, 1),
                        (152, 0, 1),
                        (141, 0, 40),
                        (93, 0, 15),
                    )
                variants.append(
                    (
                        f'{count}-sockets',
                        replace(item, sockets=count, socket_items=children, raw_stats=stats),
                        {'player_class': 'Paladin'},
                        'positive',
                    )
                )
        elif name == 'Stormshield':
            variants.append(('ethereal', replace(item, ethereal=True), {'player_class': 'Paladin'}, 'negative'))
        else:
            repair = (152, 0, 1) if name == 'Herald of Zakarum' else (252, 0, 20)
            repaired = replace(
                item,
                ethereal=True,
                raw_stats=(*tuple(r for r in raw if r[0] != repair[0]), repair),
                sockets=1 if repair[0] == 152 else 0,
                socket_contents='filled' if repair[0] == 152 else 'empty',
                socket_items=(SocketItem('Zod Rune'),) if repair[0] == 152 else (),
            )
            no_repair = replace(
                repaired, raw_stats=tuple(r for r in repaired.raw_stats if r[0] != repair[0]), socket_items=()
            )
            variants += [
                ('ethereal-repaired', repaired, {'player_class': 'Paladin'}, 'positive'),
                ('unknown-repair', no_repair, {'player_class': 'Paladin'}, 'unknown'),
                ('absent-repair', replace(no_repair, complete=True), {'player_class': 'Paladin'}, 'negative'),
                (
                    'upgraded',
                    replace(item, base='Zakarum Shield' if name == 'Herald of Zakarum' else 'Balrog Skin'),
                    {'player_class': 'Paladin'},
                    'positive',
                ),
            ]
        for label, candidate, context, scenario in variants:
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        rule_trace=IsPartialDict(
                            truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                        ),
                    )
                )
            }
            if label == 'needs-zod':
                expected = {
                    'roles': Contains(
                        IsPartialDict(
                            id=role,
                            status='partial',
                            rule_trace=IsPartialDict(truth='true'),
                            socket_requirement=IsPartialDict(item='Zod Rune', confirmed=False, applicable=True),
                        )
                    )
                }
            active_keys = keys
            if label == '3-sockets':
                active_keys = tuple(key for key in keys if key != '93:0')
            if name == 'Herald of Zakarum' and label == 'wrong-base':
                expected = {'family': 'shield'}
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in active_keys}
                    )
                )
            result.append(
                Case(
                    id=f'zeal/named-remainder/{slug}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    report_contains=(name, 'Trade tier:', 'Socket requirement: Zod (not confirmed)')
                    if label == 'needs-zod'
                    else (name, 'Trade tier:'),
                    evidence=(
                        f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
