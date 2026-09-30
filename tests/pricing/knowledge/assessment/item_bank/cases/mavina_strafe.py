"""Native M'avina pieces support Strafe without implying the other set pieces."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# Partial captures deliberately omit total defense: a native flat bonus is not total armor defense.
PIECES = (
    (
        'true-sight-equipment',
        Item('Diadem', 'set', "M'avina's True Sight", ((74, 0, 10), (93, 0, 30), (9, 0, 25 * 256)), named_table_id=90),
        True,
        ('93:0', '9:0', '74:0'),
        ('127:0', '119:0', '39:0'),
        'Helmets/7',
    ),
    (
        'embrace-equipment',
        Item(
            'Kraken Shell',
            'set',
            "M'avina's Embrace",
            ((35, 0, 5), (188, 1, 2), (91, 0, -30), (214, 0, 32)),
            named_table_id=91,
        ),
        True,
        ('188:1', '35:0'),
        ('99:0',),
        'Body Armor/5',
    ),
    (
        'icy-clutch-equipment',
        Item(
            'Battle Gauntlets',
            'set',
            "M'avina's Icy Clutch",
            ((54, 0, 6), (55, 0, 18), (56, 0, 150), (118, 0, 1), (79, 0, 56), (0, 0, 10), (2, 0, 15)),
            named_table_id=92,
        ),
        False,
        ('54:0', '55:0', '118:0', '0:0', '2:0'),
        ('153:0', '331:0'),
        'Gloves/3',
    ),
    (
        'tenet-equipment',
        Item('Sharkskin Belt', 'set', "M'avina's Tenet", ((96, 0, 20), (62, 0, 5), (89, 0, 5)), named_table_id=93),
        False,
        ('96:0', '62:0'),
        ('39:0', '41:0', '43:0', '45:0'),
        'Belts/4',
    ),
    (
        'caster-weapon',
        Item(
            'Grand Matron Bow',
            'set',
            "M'avina's Caster",
            ((17, 0, 188), (18, 0, 188), (93, 0, 40), (19, 0, 50)),
            named_table_id=94,
        ),
        True,
        ('17:0', '18:0', '93:0', '19:0'),
        ('188:0', '52:0', '53:0'),
        'Weapon/3',
    ),
)


def cases():
    for suffix, original, socketable, keys, conditional_keys, slot in PIECES:
        role = 'strafe-amazon-m-avina-s-' + suffix + '-tail-alternative'
        config = role + '-stats'
        context = {'player_class': 'Amazon'}
        variants = [
            ('standalone', original, context, 'true'),
            (
                'open-socket',
                replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))),
                context,
                'true' if socketable else 'false',
            ),
            (
                'illegal-two-sockets',
                replace(original, sockets=2, raw_stats=(*original.raw_stats, (194, 0, 2))),
                context,
                'false',
            ),
            ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), context, 'unknown'),
            ('ethereal', replace(original, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
            ('wrong-class', original, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
            ('unidentified', replace(original, identified=False), context, 'false'),
        ]
        if original.named_table_id in (92, 93):
            upgraded = 'Crusader Gauntlets' if original.named_table_id == 92 else 'Vampirefang Belt'
            variants.append(('upgraded', replace(original, base=upgraded), context, 'true'))
        if original.named_table_id == 91:
            maximum = tuple((stat, layer, 12 if stat == 35 else value) for stat, layer, value in original.raw_stats)
            variants.append(('maximum-magic-reduction', replace(original, raw_stats=maximum), context, 'true'))
        for label, item, ctx, truth in variants:
            active = truth == 'true'
            assessment = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            yield Case(
                id=f'mavina-strafe/{original.named_table_id}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**assessment)},
                absent_configurations=() if active else (config,),
                absent_stat_configurations=dict.fromkeys(conditional_keys, (config,)),
                report_contains=(original.name, 'Trade tier:') if active else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/strafe-amazon/slots/' + slot,
                    'third-parties/d2data/json/setitems.json:/' + original.name,
                ),
            )


CASES = tuple(cases())
