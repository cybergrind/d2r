"""Guardian Angel cap utility versus Paladin shield bonuses, including upgraded armor."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


CAPS = ('40:0', '42:0', '44:0', '46:0')
RAW = (
    (16, 0, 180),
    (83, 3, 1),
    (102, 0, 30),
    (20, 0, 20),
    (245, 0, 5),
    (89, 0, 4),
    *((s, 0, 15) for s in (40, 42, 44, 46)),
)


def cases():
    for build, klass, extra in (
        ('enchant-sorceress', 'Sorceress', {}),
        ('smite-paladin', 'Paladin', {'83:3': 'desirable', '20:0': 'desirable', '102:0': 'supporting'}),
    ):
        role = build + '-guardian-armor-alternative'
        config = role + '-stats'
        grades = {**dict.fromkeys(CAPS, 'desirable'), **extra}
        context = {'player_class': klass}
        for base, defense in (('Templar Coat', 770), ('Hellforge Plate', 1178)):
            original = Item(base, 'unique', 'Guardian Angel', (*RAW, (31, 0, defense)), named_table_id=218)
            rows = [
                ('minimum', original, context, 'true'),
                (
                    'maximum-ed',
                    replace(
                        original,
                        raw_stats=tuple(
                            (s, p, 200 if s == 16 else (825 if base == 'Templar Coat' else 1263) if s == 31 else v)
                            for s, p, v in original.raw_stats
                        ),
                    ),
                    context,
                    'true',
                ),
                ('ethereal', replace(original, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
                ('unidentified', replace(original, identified=False), context, 'false'),
                ('wrong-class', original, {'player_class': 'Barbarian'}, 'false'),
                ('unknown-class', original, {}, 'unknown'),
                (
                    'empty-socket',
                    replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))),
                    context,
                    'true',
                ),
                (
                    'um-socket',
                    replace(
                        original,
                        sockets=1,
                        socket_contents='filled',
                        socket_items=(SocketItem('Um Rune'),),
                        raw_stats=(*original.raw_stats, (194, 0, 1), *((s, 0, 15) for s in (39, 41, 43, 45))),
                    ),
                    context,
                    'true',
                ),
                ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), context, 'unknown'),
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
                present = {f'{s}:{p}' for s, p, _ in item.raw_stats}
                expected = {
                    'assessment': IsPartialDict(
                        roles=Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth))),
                        stat_evaluation=IsPartialDict(
                            annotations=IsPartialDict(
                                {
                                    k: IsPartialDict(
                                        contributions=Contains(
                                            IsPartialDict(configuration_id=config, role_id=role, desirability=v)
                                        )
                                    )
                                    for k, v in grades.items()
                                    if truth == 'true' and k in present
                                }
                            )
                        ),
                    ),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                }
                if label in ('minimum', 'maximum-ed'):
                    expected['extraction'] = IsPartialDict(
                        decoded_stats=Contains(
                            IsPartialDict(
                                memory_stat=IsPartialDict(id=16, layer=0),
                                roll_range=IsPartialDict(min=180, max=200),
                                roll_quality='perfect' if label == 'maximum-ed' else 'low',
                            )
                        )
                    )
                yield Case(
                    id=f'guardian-angel-player/{build}/{base}/{label}',
                    item=item,
                    context=ctx,
                    expected=expected,
                    covers=(role,),
                    scenario='unknown'
                    if truth == 'unknown' or label.startswith('unread')
                    else 'positive'
                    if truth == 'true'
                    else 'negative',
                    absent_configurations=(config,) if truth != 'true' else (),
                    absent_stat_configurations={
                        k: (config,)
                        for k in (
                            *grades,
                            '83:3',
                            '20:0',
                            '102:0',
                            '245:0',
                            '89:0',
                            '16:0',
                            '39:0',
                            '41:0',
                            '43:0',
                            '45:0',
                        )
                        if k not in grades or k not in present
                    },
                    report_contains=('Guardian Angel', 'Trade tier:', '(180-200%)')
                    if label == 'minimum'
                    else ('Sockets: 1 — Um',)
                    if label == 'um-socket'
                    else (),
                    detail_contains=('Raised caps need actual resistances from the full loadout',)
                    if truth == 'true'
                    else (),
                    evidence=(
                        'third-parties/d2data/json/uniqueitems.json:/218',
                        f'pricing/data/wp-a-builds.json:/{build}/slots/Body Armor/{4 if klass == "Sorceress" else 7}',
                    ),
                )


CASES = tuple(cases())
