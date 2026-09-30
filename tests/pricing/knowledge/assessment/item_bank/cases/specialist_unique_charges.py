"""Specific charged skills, rather than item identity, enable specialist utility."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


PRISON = 88 * 64 + 33
LIFE_TAP = 82 * 64 + 12
TELEPORT = 54 * 64 + 1
DECREPIFY = 87 * 64 + 3
BOOTS = Item(
    'Boneweave Boots',
    'unique',
    'Marrowwalk',
    (
        (16, 0, 170),
        (96, 0, 20),
        (27, 0, 10),
        (118, 0, 1),
        (0, 0, 10),
        (2, 0, 17),
        (204, PRISON, (13 << 8) | 1),
        (204, LIFE_TAP, (10 << 8) | 10),
    ),
    named_table_id=370,
)
AXE = Item(
    'Bearded Axe',
    'unique',
    'Spellsteel',
    (
        (91, 0, -60),
        (9, 0, 100 * 256),
        (35, 0, 12),
        (105, 0, 10),
        (17, 0, 165),
        (18, 0, 165),
        (27, 0, 25),
        (204, TELEPORT, (20 << 8) | 1),
        (204, DECREPIFY, (30 << 8) | 1),
    ),
    named_table_id=135,
)


def remaining(item, layers, value):
    return replace(
        item,
        raw_stats=tuple(
            (s, layer, (raw & ~255) | value if s == 204 and layer in layers else raw)
            for s, layer, raw in item.raw_stats
        ),
    )


def cases():
    for role, original, klass, keys, locator in (
        (
            'meteor-sorceress-marrowwalk-qualified-equipment',
            BOOTS,
            'Sorceress',
            ('204:5665', '96:0', '0:0', '2:0', '27:0', '118:0', '16:0'),
            '/meteor-sorceress/slots/Boots/3',
        ),
        (
            'strafe-amazon-spellsteel-qualified-equipment',
            AXE,
            'Amazon',
            ('204:3457', '204:5571', '105:0', '9:0', '35:0', '27:0'),
            '/strafe-amazon/slots/Weapon-Swap/4',
        ),
    ):
        context = {'player_class': klass}
        config = role + '-stats'
        layers = (PRISON,) if original is BOOTS else (TELEPORT, DECREPIFY)
        variants = [
            ('one-charge', original, context, 'true', 'true', keys),
            ('exhausted', remaining(original, layers, 0), context, 'true', 'false', ()),
            (
                'unknown-charges',
                replace(
                    original,
                    raw_stats=tuple(row for row in original.raw_stats if row[0] != 204 or row[1] not in layers),
                ),
                context,
                'true',
                'unknown',
                (),
            ),
            ('wrong-class', original, {'player_class': 'Druid'}, 'false', None, ()),
            ('unknown-class', original, {}, 'unknown', None, ()),
            ('unidentified', replace(original, identified=False), context, 'false', None, ()),
            (
                'unknown-sockets',
                replace(original, sockets=None, socket_contents='unknown'),
                context,
                'unknown',
                None,
                (),
            ),
        ]
        if original is BOOTS:
            variants.extend(
                (
                    ('ethereal', replace(original, ethereal=True), context, 'false', None, ()),
                    ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown', None, ()),
                    (
                        'illegal-socket',
                        replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))),
                        context,
                        'false',
                        None,
                        (),
                    ),
                )
            )
        else:
            variants.extend(
                (
                    (
                        'teleport-only',
                        remaining(original, (DECREPIFY,), 0),
                        context,
                        'true',
                        'true',
                        tuple(k for k in keys if k != '204:5571'),
                    ),
                    (
                        'decrepify-only',
                        remaining(original, (TELEPORT,), 0),
                        context,
                        'true',
                        'true',
                        tuple(k for k in keys if k != '204:3457'),
                    ),
                    ('ethereal-finite-charges', replace(original, ethereal=True), context, 'true', 'true', keys),
                    ('upgraded', replace(original, base='Silver-edged Axe'), context, 'true', 'true', keys),
                    (
                        'open-socket',
                        replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))),
                        context,
                        'true',
                        'true',
                        keys,
                    ),
                    (
                        'illegal-two-sockets',
                        replace(original, sockets=2, raw_stats=(*original.raw_stats, (194, 0, 2))),
                        context,
                        'false',
                        None,
                        (),
                    ),
                )
            )
        for label, item, ctx, truth, dependency, expected_keys in variants:
            active = truth == dependency == 'true'
            expected_role = {'id': role, 'rule_trace': IsPartialDict(truth=truth)}
            if dependency is not None:
                expected_role['dependencies'] = Contains(IsPartialDict(status=dependency))
            expected = {'roles': Contains(IsPartialDict(**expected_role))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {k: IsPartialDict(configuration_ids=Contains(config)) for k in expected_keys}
                    )
                )
            yield Case(
                id=f'specialist-unique-charges/{original.named_table_id}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario='positive'
                if active
                else 'unknown'
                if truth == 'unknown' or dependency == 'unknown'
                else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                absent_stat_configurations={
                    '17:0': (config,),
                    '18:0': (config,),
                    **{key: (config,) for key in ('204:3457', '204:5571') if key not in expected_keys},
                }
                if original is AXE
                else {'204:5260': (config,)},
                report_contains=(original.name, 'Trade tier:', 'Charges') if active else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:' + locator,
                    'third-parties/d2data/json/uniqueitems.json:/' + str(original.named_table_id),
                ),
            )


CASES = tuple(cases())
