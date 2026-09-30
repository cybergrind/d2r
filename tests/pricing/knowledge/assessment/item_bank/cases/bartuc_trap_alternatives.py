"""Bartuc's trap alternatives: native skills, recovery and caster durability."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CLAW = Item(
    'Greater Talons',
    'unique',
    "Bartuc's Cut-Throat",
    (
        (83, 6, 2),
        (188, 50, 1),
        (17, 0, 150),
        (18, 0, 150),
        (99, 0, 30),
        (119, 0, 20),
        (0, 0, 20),
        (2, 0, 20),
        (60, 0, 5),
    ),
    named_table_id=286,
)


def cases():
    for build, position in (('lightning-sentry-assassin', 5), ('wake-of-fire-assassin', 4)):
        role = build + '-bartuc-s-cut-throat-weapon-tail-alternative'
        config = role + '-stats'
        context = {'player_class': 'Assassin'}
        for label, item, ctx, truth in (
            ('native', CLAW, context, 'true'),
            ('upgraded', replace(CLAW, base='Runic Talons'), context, 'true'),
            ('ethereal-trap-placement', replace(CLAW, ethereal=True), context, 'true'),
            ('unknown-ethereal-trap-placement', replace(CLAW, ethereal=None), context, 'true'),
            ('open-socket', replace(CLAW, sockets=1, raw_stats=(*CLAW.raw_stats, (194, 0, 1))), context, 'true'),
            (
                'illegal-two-sockets',
                replace(CLAW, sockets=2, raw_stats=(*CLAW.raw_stats, (194, 0, 2))),
                context,
                'false',
            ),
            ('unknown-sockets', replace(CLAW, sockets=None, socket_contents='unknown'), context, 'unknown'),
            ('unidentified', replace(CLAW, identified=False), context, 'false'),
            ('wrong-class', CLAW, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', CLAW, {}, 'unknown'),
            ('unread-assassin-skills', replace(CLAW, raw_stats=CLAW.raw_stats[1:]), context, 'true'),
        ):
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            keys = ['99:0', '0:0', '2:0']
            if label != 'unread-assassin-skills':
                keys.append('83:6')
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            absent_keys = ['188:50', '17:0', '18:0', '119:0', '60:0']
            if label == 'unread-assassin-skills':
                absent_keys.append('83:6')
            yield Case(
                id=f'bartuc-trap/{build}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                absent_stat_configurations=dict.fromkeys(absent_keys, (config,)),
                report_contains=("Bartuc's Cut-Throat", 'Trade tier:') if active else (),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/slots/Weapon/{position}',
                    'third-parties/d2data/json/uniqueitems.json:/286',
                ),
            )


CASES = tuple(cases())
