"""Source-authored Warlock book rolls and Fire Warlock contribution boundaries."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


# Each tuple: role suffix, title, base, native ID, base max+1, min-roll stats,
# independently verified variable bounds, desired/supporting stats, excluded effects, caveat.
BOOKS = (
    (
        'ars-al-diabolos',
        "Ars Al'Diabolos",
        'Blasphemous Grimoire',
        408,
        149,
        (
            (188, 58, 2),
            (201, 77 * 64 + 1, 15),
            (105, 0, 25),
            (16, 0, 170),
            (329, 0, 15),
            (89, 0, 5),
            (138, 0, 5),
            (39, 0, 20),
            (107, 401, 3),
        ),
        {
            (16, 0): (170, 200),
            (329, 0): (15, 25),
            (89, 0): (5, 10),
            (138, 0): (5, 10),
            (39, 0): (20, 30),
            (107, 401): (3, 5),
        },
        ('188:58', '105:0', '329:0', '107:401'),
        ('138:0', '39:0', '16:0'),
        ('201:4929', '89:0'),
        'Terror requires a when-struck proc',
    ),
    (
        'ars-dul-mephistos',
        "Ars Dul'Mephistos",
        'Occult Tome',
        410,
        142,
        (
            (83, 7, 2),
            (201, 59 * 64 + 28, 15),
            (105, 0, 20),
            (99, 0, 30),
            (17, 0, 70),
            (18, 0, 70),
            (119, 0, 50),
            (16, 0, 140),
            (358, 0, 10),
            (80, 0, 10),
        ),
        {
            (105, 0): (20, 30),
            (17, 0): (70, 115),
            (119, 0): (50, 70),
            (16, 0): (140, 170),
            (358, 0): (10, 20),
            (80, 0): (10, 25),
        },
        ('83:7', '105:0', '99:0'),
        ('16:0', '80:0'),
        ('17:0', '18:0', '119:0', '358:0', '201:3804'),
        'Blizzard requires a when-struck proc',
    ),
    (
        'ars-tor-baalos',
        "Ars Tor'Baalos",
        'Blasphemous Compendium',
        409,
        147,
        (
            (188, 56, 2),
            (201, 87 * 64 + 1, 15),
            (107, 374, 2),
            (107, 380, 2),
            (107, 379, 2),
            (107, 381, 2),
            (16, 0, 120),
            (216, 0, 12 * 256),
            (36, 0, 5),
        ),
        {
            (107, 374): (2, 3),
            (107, 380): (2, 4),
            (107, 379): (2, 3),
            (107, 381): (2, 3),
            (16, 0): (120, 150),
            (36, 0): (5, 10),
        },
        ('216:0', '36:0'),
        ('188:56', '107:374', '107:380', '107:379', '107:381', '16:0'),
        ('201:5569',),
        'do not directly raise Chaos fire skill levels',
    ),
)


def cases():
    context = {'player_class': 'Warlock'}
    for suffix, name, base, native, base_defense, stats, rolls, desirable, supporting, excluded, caveat in BOOKS:
        role = 'fire-warlock-guide-' + suffix + '-caster-utility-alternative'
        config = role + '-stats'
        grades = {**dict.fromkeys(desirable, 'desirable'), **dict.fromkeys(supporting, 'supporting')}

        def with_defense(values, base_defense=base_defense):
            ed = next(v for s, p, v in values if (s, p) == (16, 0))
            return (*values, (31, 0, base_defense * (100 + ed) // 100))

        original = Item(base, 'unique', name, with_defense(stats), named_table_id=native)
        rows = [('minimum', original, context, 'true')]
        for pair, (_, high) in rolls.items():
            changed = tuple((s, p, high if (s, p) == pair or (pair == (17, 0) and s == 18) else v) for s, p, v in stats)
            rows.append(
                (f'maximum-{pair[0]}-{pair[1]}', replace(original, raw_stats=with_defense(changed)), context, 'true')
            )
        rows += [
            ('ethereal', replace(original, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
            ('unidentified', replace(original, identified=False), context, 'false'),
            ('wrong-class', original, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
            ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), context, 'unknown'),
            (
                'empty-socket',
                replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))),
                context,
                'true',
            ),
            (
                'unknown-filler',
                replace(original, sockets=1, socket_contents='unknown', raw_stats=(*original.raw_stats, (194, 0, 1))),
                context,
                'true',
            ),
            (
                'ort-socket',
                replace(
                    original,
                    sockets=1,
                    socket_contents='filled',
                    socket_items=(SocketItem('Ort Rune'),),
                    raw_stats=(*original.raw_stats, (194, 0, 1), (41, 0, 35)),
                ),
                context,
                'true',
            ),
            (
                'invalid-two-sockets',
                replace(original, sockets=2, raw_stats=(*original.raw_stats, (194, 0, 2))),
                context,
                'false',
            ),
            ('unread-all', replace(original, raw_stats=()), context, 'true'),
        ]
        for key in grades:
            pair = tuple(map(int, key.split(':')))
            rows.append(
                (
                    'unread-' + key,
                    replace(original, raw_stats=tuple(s for s in original.raw_stats if s[:2] != pair)),
                    context,
                    'true',
                )
            )
        for label, item, ctx, truth in rows:
            active = truth == 'true'
            captured = {f'{s}:{p}' for s, p, _ in item.raw_stats}
            assessment = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(
                                contributions=Contains(
                                    IsPartialDict(configuration_id=config, role_id=role, desirability=grade)
                                )
                            )
                            for key, grade in grades.items()
                            if key in captured
                        }
                    )
                )
            checks = []
            if label == 'minimum' or label.startswith('maximum-'):
                checks = [name, 'Trade tier:', *[f'({lo}-{hi}' for lo, hi in rolls.values()]]
                if native == 409:
                    checks.append('+120 to Life')
            if label == 'ort-socket':
                checks.append('Sockets: 1 — Ort')
            expected = {'assessment': IsPartialDict(**assessment), 'price_estimate': IsPartialDict(estimate_ist=None)}
            if label == 'minimum' or label.startswith('maximum-'):
                values = {(s, p): value for s, p, value in item.raw_stats}
                expected['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *[
                            IsPartialDict(
                                **(
                                    {'memory_stats': Contains(IsPartialDict(id=sid, layer=layer))}
                                    if sid == 17
                                    else {'memory_stat': IsPartialDict(id=sid, layer=layer)}
                                ),
                                roll_range=IsPartialDict(min=low, max=high),
                                roll_quality='perfect' if values[sid, layer] == high else 'low',
                            )
                            for (sid, layer), (low, high) in rolls.items()
                        ]
                    )
                )
            yield Case(
                id='fire-books/' + suffix + '/' + label,
                item=item,
                context=ctx,
                expected=expected,
                covers=(role,),
                scenario='unknown'
                if truth == 'unknown' or label.startswith('unread')
                else 'positive'
                if active
                else 'negative',
                absent_configurations=() if active else (config,),
                absent_stat_configurations={
                    key: (config,) for key in (*grades, *excluded) if key not in captured or key in excluded
                },
                report_contains=tuple(checks),
                detail_contains=(caveat,) if active else (),
                evidence=(
                    f'third-parties/d2data/json/uniqueitems.json:/{native}',
                    'third-parties/d2data/json/skills.json',
                    'pricing/data/wp-a-builds.json:/fire-warlock-guide/slots',
                ),
            )


CASES = tuple(cases())
