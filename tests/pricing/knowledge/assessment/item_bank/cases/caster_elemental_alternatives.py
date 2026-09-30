"""Caster alternatives distinguish skill bonuses from weapon and proc effects."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


HAMMER = Item(
    'Battle Hammer',
    'unique',
    'Earthshaker',
    ((188, 42, 3), (17, 0, 180), (18, 0, 180), (93, 0, 30), (81, 0, 1), (113, 0, 1), (198, 14983, 5)),
    named_table_id=151,
)
AMULET = Item(
    'Amulet',
    'unique',
    'The Rising Sun',
    ((126, 1, 2), (235, 0, 6), (74, 0, 10), (48, 0, 24), (49, 0, 48)),
    named_table_id=270,
)


def cases():
    for original, role, klass, locator, keys, excluded in (
        (
            HAMMER,
            'fissure-druid-earthshaker-caster-remainder-alternative',
            'Druid',
            '/fissure-druid/slots/Weapon/6',
            ('188:42',),
            ('17:0', '18:0', '93:0', '81:0', '113:0', '198:14983'),
        ),
        (
            AMULET,
            'fire-warlock-guide-the-rising-sun-caster-remainder-alternative',
            'Warlock',
            '/fire-warlock-guide/slots/Amulets/1',
            ('126:1', '235:0', '74:0'),
            ('48:0', '49:0'),
        ),
    ):
        config = role + '-stats'
        ctx = {'player_class': klass}
        variants = [
            ('native', original, ctx, 'true'),
            ('wrong-class', original, {'player_class': 'Amazon'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
            ('unidentified', replace(original, identified=False), ctx, 'false'),
            ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), ctx, 'unknown'),
            (
                'illegal-two-sockets',
                replace(original, sockets=2, raw_stats=(*original.raw_stats, (194, 0, 2))),
                ctx,
                'false',
            ),
        ]
        if original is HAMMER:
            variants.extend(
                (
                    ('ethereal-casting', replace(original, ethereal=True), ctx, 'true'),
                    ('unknown-ethereal-casting', replace(original, ethereal=None), ctx, 'true'),
                    ('upgraded', replace(original, base='Legendary Mallet'), ctx, 'true'),
                    (
                        'open-socket',
                        replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))),
                        ctx,
                        'true',
                    ),
                )
            )
        else:
            variants.extend(
                (
                    ('level-99', replace(original, viewer_level=99), ctx, 'true'),
                    ('ethereal', replace(original, ethereal=True), ctx, 'false'),
                    ('unknown-ethereal', replace(original, ethereal=None), ctx, 'unknown'),
                    (
                        'illegal-one-socket',
                        replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))),
                        ctx,
                        'false',
                    ),
                )
            )
        for label, item, context, truth in variants:
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            yield Case(
                id=f'caster-elemental-alternatives/{original.named_table_id}/{label}',
                item=item,
                context=context,
                covers=(role,),
                scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                absent_stat_configurations=dict.fromkeys(excluded, (config,)),
                report_contains=(original.name, 'Trade tier:') if active else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:' + locator,
                    f'third-parties/d2data/json/uniqueitems.json:/{original.named_table_id}',
                ),
            )


CASES = tuple(cases())
