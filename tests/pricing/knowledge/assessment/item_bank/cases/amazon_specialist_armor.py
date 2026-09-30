"""Amazon armor alternatives: native rolls, sustain and conditional damage."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


HELM = Item(
    'Winged Helm',
    'unique',
    'Valkyrie Wing',
    ((16, 0, 150), (96, 0, 20), (99, 0, 20), (83, 0, 1), (138, 0, 2)),
    named_table_id=205,
)
ARMOR = Item(
    'Sacred Armor',
    'unique',
    "Tyrael's Might",
    (
        (91, 0, -100),
        (152, 0, 1),
        (16, 0, 120),
        (108, 0, 1),
        (121, 0, 50),
        (153, 0, 1),
        (96, 0, 20),
        (39, 0, 20),
        (41, 0, 20),
        (43, 0, 20),
        (45, 0, 20),
        (0, 0, 20),
    ),
    named_table_id=311,
)


def cases():
    for original, role, locator, keys, maxima, ranges in (
        (
            HELM,
            'lightning-strike-amazon-valkyrie-wing-equipment-tail-alternative',
            '/lightning-strike-amazon/slots/Helmets/6',
            ('83:0', '96:0', '99:0', '138:0'),
            {16: 200, 83: 2, 138: 4},
            ('(150-200%)', '(1-2)', '(2-4)'),
        ),
        (
            ARMOR,
            'strafe-amazon-tyrael-s-might-specialist-equipment-alternative',
            '/strafe-amazon/slots/Body Armor/9',
            ('153:0', '96:0', '39:0', '41:0', '43:0', '45:0', '0:0', '121:0', '16:0'),
            {16: 150, 121: 100, 39: 30, 41: 30, 43: 30, 45: 30, 0: 30},
            ('(120-150%)', '(50-100%)', '(20-30%)'),
        ),
    ):
        config = role + '-stats'
        context = {'player_class': 'Amazon'}
        variants = [
            ('native-minimum', original, context, 'true'),
            (
                'maximum-rolls',
                replace(
                    original,
                    raw_stats=tuple((s, layer, maxima.get(s, value)) for s, layer, value in original.raw_stats),
                ),
                context,
                'true',
            ),
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
            ('ethereal', replace(original, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
            ('unidentified', replace(original, identified=False), context, 'false'),
            ('wrong-class', original, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
        ]
        if original is HELM:
            variants.extend(
                (
                    ('upgraded', replace(original, base='Spired Helm'), context, 'true'),
                    ('unread-mana-on-kill', replace(original, raw_stats=original.raw_stats[:-1]), context, 'true'),
                )
            )
        for label, item, ctx, truth in variants:
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            observed = tuple(k for k in keys if label != 'unread-mana-on-kill' or k != '138:0')
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(config)) for key in observed}
                    )
                )
            absent = ['62:0', '60:0', '93:0']
            if label == 'unread-mana-on-kill':
                absent.append('138:0')
            yield Case(
                id=f'amazon-specialist-armor/{original.named_table_id}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                absent_stat_configurations=dict.fromkeys(absent, (config,)),
                report_contains=(original.name, 'Trade tier:', *ranges)
                if label in ('native-minimum', 'maximum-rolls')
                else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:' + locator,
                    f'third-parties/d2data/json/uniqueitems.json:/{original.named_table_id}',
                ),
            )


CASES = tuple(cases())
