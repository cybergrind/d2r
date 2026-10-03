"""Native Sharp charms across physical-attack builds; planner maxima are optional."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item
from tests.pricing.knowledge.assessment.item_bank.sharp_report_contracts import sharp_checks


SPECS = (
    ('double-throw-barbarian-guide', 'Barbarian', (('vita', 14), ('balance', 15), ('inertia', 16), ('plain', 17))),
    ('berserk-barbarian', 'Barbarian', (('vita', 16), ('balance', 14), ('plain', 18))),
    ('dream-paladin', 'Paladin', (('vita', 11), ('balance', 12))),
)


def cases():
    for build, klass, options in SPECS:
        for suffix, index in options:
            role = f'{build}-main-sharp-{suffix}'
            config = role + '-stats'
            secondary = {'vita': ((7, 0, 36 * 256),), 'balance': ((99, 0, 12),), 'inertia': ((96, 0, 7),), 'plain': ()}[
                suffix
            ]
            suffix_records = (
                () if suffix == 'plain' else (('suffix', {'vita': 338, 'balance': 265, 'inertia': 399}[suffix]),)
            )
            original = Item(
                'Grand Charm',
                'magic',
                raw_stats=((19, 0, 49), (22, 0, 7), *secondary),
                affix_records=(('prefix', 253), *suffix_records),
                complete=True,
            )
            context = {'player_class': klass}
            maximum_secondary = ((7, 0, 45 * 256),) if suffix == 'vita' else secondary
            maximum_suffix = (('suffix', 339),) if suffix == 'vita' else suffix_records
            variants = [
                ('minimum', original, context, 'true'),
                (
                    'maximum',
                    replace(
                        original,
                        raw_stats=((19, 0, 76), (22, 0, 10), *maximum_secondary),
                        affix_records=(('prefix', 253), *maximum_suffix),
                    ),
                    context,
                    'true',
                ),
                (
                    'fine-near-miss',
                    replace(
                        original,
                        raw_stats=((19, 0, 48), (22, 0, 6), *secondary),
                        affix_records=(('prefix', 252), *suffix_records),
                    ),
                    context,
                    'false',
                ),
                (
                    'steel-without-damage',
                    replace(
                        original, raw_stats=((19, 0, 88), *secondary), affix_records=(('prefix', 224), *suffix_records)
                    ),
                    context,
                    'false',
                ),
                (
                    'unread-attack-rating',
                    replace(original, raw_stats=((22, 0, 7), *secondary), complete=False),
                    context,
                    'unknown',
                ),
                (
                    'unread-damage',
                    replace(original, raw_stats=((19, 0, 49), *secondary), complete=False),
                    context,
                    'unknown',
                ),
                ('wrong-class', original, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', original, {}, 'unknown'),
                ('unidentified', replace(original, identified=False), context, 'false'),
            ]
            if secondary:
                variants.extend(
                    [
                        (
                            'absent-secondary',
                            replace(original, raw_stats=((19, 0, 49), (22, 0, 7)), affix_records=(('prefix', 253),)),
                            context,
                            'false',
                        ),
                        (
                            'unread-secondary',
                            replace(original, raw_stats=((19, 0, 49), (22, 0, 7)), complete=False),
                            context,
                            'unknown',
                        ),
                    ]
                )
            if suffix == 'vita':
                variants.extend(
                    [
                        (
                            'life35',
                            replace(
                                original,
                                raw_stats=((19, 0, 49), (22, 0, 7), (7, 0, 35 * 256)),
                                affix_records=(('prefix', 253), ('suffix', 337)),
                            ),
                            context,
                            'false',
                        ),
                        (
                            'life40',
                            replace(original, raw_stats=((19, 0, 49), (22, 0, 7), (7, 0, 40 * 256))),
                            context,
                            'true',
                        ),
                    ]
                )
            if suffix == 'plain':
                variants.append(
                    (
                        'optional-life',
                        replace(
                            original,
                            raw_stats=((19, 0, 49), (22, 0, 7), (7, 0, 20 * 256)),
                            affix_records=(('prefix', 253), ('suffix', 334)),
                        ),
                        context,
                        'true',
                    )
                )
            for label, record, raw in (
                ('ar-global-min', 218, ((19, 0, 6),)),
                ('ar-global-max', 226, ((19, 0, 132),)),
                ('ar-low-edge', 252, ((19, 0, 31), (22, 0, 4))),
                ('ar-neutral-edge', 252, ((19, 0, 32), (22, 0, 4))),
                ('damage-global-min', 251, ((19, 0, 10), (22, 0, 1))),
                ('damage-low-edge', 251, ((19, 0, 10), (22, 0, 2))),
                ('damage-neutral-edge', 251, ((19, 0, 10), (22, 0, 3))),
            ):
                variants.append(
                    (
                        label,
                        replace(
                            original, raw_stats=(*raw, *secondary), affix_records=(('prefix', record), *suffix_records)
                        ),
                        context,
                        'false',
                    )
                )
            if suffix == 'vita':
                variants.append(
                    (
                        'life-global-min',
                        replace(
                            original,
                            raw_stats=((19, 0, 49), (22, 0, 7), (7, 0, 5 * 256)),
                            affix_records=(('prefix', 253), ('suffix', 332)),
                        ),
                        context,
                        'false',
                    )
                )
            for label, item, ctx, truth in variants:
                checks = None
                if label in {
                    'minimum',
                    'maximum',
                    'wrong-class',
                    'unknown-class',
                    'life35',
                    'life40',
                    'life-global-min',
                }:
                    checks = sharp_checks(
                        role,
                        suffix,
                        truth,
                        ar=76 if label == 'maximum' else 49,
                        damage=10 if label == 'maximum' else 7,
                        life={'maximum': 45, 'life35': 35, 'life40': 40, 'life-global-min': 5}.get(label, 36),
                    )
                elif label.startswith('ar-'):
                    checks = sharp_checks(role, None, truth, ar=item.raw_stats[0][2])
                elif label.startswith('damage-'):
                    checks = sharp_checks(role, None, truth, damage=item.raw_stats[1][2])
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    keys = ['19:0', '22:0', *(f'{s}:{p}' for s, p, v in secondary)]
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict({k: IsPartialDict(configuration_ids=Contains(config)) for k in keys})
                    )
                yield Case(
                    id=f'main-sharp-charms/{build}/{suffix}/{label}',
                    report_checks=checks,
                    item=item,
                    context=ctx,
                    covers=(role,),
                    scenario='positive' if truth == 'true' else 'negative' if truth == 'false' else 'unknown',
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_configurations=() if truth == 'true' else (config,),
                    report_contains=('to Attack Rating', 'Maximum damage:') if truth == 'true' else (),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/slots/Charms/{index}',
                        'third-parties/d2data/json/magicprefix.json:/253',
                    ),
                )


CASES = tuple(cases())
