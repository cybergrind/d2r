"""Native ranged alternatives preserve scaling, legal bases and socket uncertainty."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


BURIZA = Item(
    'Ballista',
    'unique',
    'Buriza-Do Kyanon',
    (
        (156, 0, 100),
        (2, 0, 35),
        (218, 0, 20),
        (93, 0, 80),
        (17, 0, 150),
        (18, 0, 150),
        (134, 0, 3),
        (54, 0, 32),
        (55, 0, 196),
        (56, 0, 200),
    ),
    named_table_id=198,
)
EAGLEHORN = Item(
    'Crusader Bow',
    'unique',
    'Eaglehorn',
    ((115, 0, 1), (224, 0, 12), (219, 0, 16), (17, 0, 200), (18, 0, 200), (83, 0, 1), (2, 0, 25)),
    named_table_id=265,
)


def cases():
    for original, suffix, position, keys in (
        (
            BURIZA,
            'buriza-do-kyanon-zeal-ranged-tail',
            4,
            ('156:0', '2:0', '218:0', '93:0', '17:0', '18:0', '134:0', '54:0', '55:0'),
        ),
        (EAGLEHORN, 'eaglehorn-weapon-tail-alternative', 6, ('115:0', '224:0', '219:0', '17:0', '18:0', '83:0', '2:0')),
    ):
        role = 'strafe-amazon-' + suffix
        config = role + '-stats'
        context = {'player_class': 'Amazon'}
        variants = [
            ('native', original, context, 'true'),
            ('level-99', replace(original, viewer_level=99), context, 'true'),
            (
                'open-socket',
                replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))),
                context,
                'true',
            ),
            (
                'illegal-two-sockets',
                replace(original, sockets=2, raw_stats=(*original.raw_stats, (194, 0, 2))),
                context,
                'false',
            ),
            ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), context, 'unknown'),
            ('illegal-ethereal', replace(original, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
            ('unidentified', replace(original, identified=False), context, 'false'),
            ('wrong-class', original, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
        ]
        if original is BURIZA:
            variants.extend(
                (
                    ('upgraded', replace(original, base='Colossus Crossbow'), context, 'true'),
                    (
                        'perfect-ed',
                        replace(
                            original,
                            raw_stats=tuple(
                                (s, layer, 200 if s in (17, 18) else value) for s, layer, value in original.raw_stats
                            ),
                        ),
                        context,
                        'true',
                    ),
                )
            )
        else:
            variants.append(
                (
                    'unread-scaling',
                    replace(original, raw_stats=tuple(row for row in original.raw_stats if row[0] not in (219, 224))),
                    context,
                    'true',
                )
            )
        for label, item, ctx, truth in variants:
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            observed_keys = tuple(k for k in keys if label != 'unread-scaling' or k not in ('219:0', '224:0'))
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(config)) for key in observed_keys}
                    )
                )
            absent = ['93:0'] if original is EAGLEHORN else []
            if label == 'unread-scaling':
                absent.extend(('219:0', '224:0'))
            yield Case(
                id=f'strafe-unique-ranged/{original.named_table_id}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                absent_stat_configurations=dict.fromkeys(absent, (config,)),
                report_contains=(original.name, 'Trade tier:') if active else (),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/strafe-amazon/slots/Weapon/{position}',
                    f'third-parties/d2data/json/uniqueitems.json:/{original.named_table_id}',
                ),
            )


CASES = tuple(cases())
