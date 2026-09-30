"""The Uber helmet needs the cited combined jewel, not matching parent totals."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'dragon-talon-budget-guillaume'
CONFIG = ROLE + '-stats'
INTRINSIC = ((16, 0, 120), (136, 0, 35), (141, 0, 15), (99, 0, 30), (0, 0, 15))


def helmet(ias=15, resistance=30):
    payload = ((93, 0, ias), (41, 0, resistance))
    return Item(
        'Winged Helm',
        'set',
        "Guillaume's Face",
        (*INTRINSIC, *payload, (194, 0, 1)),
        sockets=1,
        socket_contents='filled',
        socket_items=(SocketItem('Jewel', payload, complete=True),),
        named_table_id=104,
    )


def cases():
    item = helmet()
    context = {'player_class': 'Assassin'}
    examples = [
        ('combined-jewel', item, context, 'true', 'true'),
        ('29-lightning-resistance', helmet(resistance=29), context, 'true', 'false'),
        ('no-jewel-ias', helmet(ias=0), context, 'true', 'false'),
        ('wrong-class', item, {'player_class': 'Sorceress'}, 'false', 'true'),
        ('unknown-class', item, {}, 'unknown', 'true'),
        ('unidentified', replace(item, identified=False), context, 'false', 'true'),
        (
            'empty-socket',
            replace(item, raw_stats=(*INTRINSIC, (194, 0, 1)), socket_contents='empty', socket_items=()),
            context,
            'true',
            'false',
        ),
        ('unread-child', replace(item, socket_items=()), context, 'true', 'unknown'),
        (
            'unread-resistance',
            replace(item, socket_items=(SocketItem('Jewel', ((93, 0, 15),), complete=False),)),
            context,
            'true',
            'unknown',
        ),
        (
            'parent-totals-do-not-prove-payload',
            replace(item, socket_items=(SocketItem('Jewel', ((93, 0, 15), (39, 0, 30)), complete=True),)),
            context,
            'true',
            'false',
        ),
    ]
    for label, candidate, loadout, truth, dependency in examples:
        active = truth == dependency == 'true'
        assessment = {
            'roles': Contains(
                IsPartialDict(
                    id=ROLE,
                    rule_trace=IsPartialDict(truth=truth),
                    dependencies=Contains(IsPartialDict(status=dependency)),
                )
            )
        }
        if active:
            assessment['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(CONFIG), desirability=grade)
                        for key, grade in (
                            ('136:0', 'desirable'),
                            ('93:0', 'desirable'),
                            ('41:0', 'desirable'),
                            ('99:0', 'supporting'),
                            ('0:0', 'supporting'),
                        )
                    }
                )
            )
        yield Case(
            id=f'dragon-talon-guillaume/{label}',
            item=candidate,
            context=loadout,
            covers=(ROLE,),
            scenario='positive' if active else 'negative' if 'false' in (truth, dependency) else 'unknown',
            expected={
                'assessment': IsPartialDict(**assessment),
                'price_estimate': IsPartialDict(estimate_ist=None),
            },
            absent_configurations=() if active else (CONFIG,),
            # Deadly Strike does not double kick damage; defense is not the cited contribution.
            absent_stat_configurations={'141:0': (CONFIG,), '16:0': (CONFIG,), '31:0': (CONFIG,)},
            report_contains=(
                "Guillaume's Face",
                'Trade tier:',
                '35% Chance of Crushing Blow',
                '15% Increased Attack Speed',
                'Lightning Resist +30%',
                'Jewel',
            )
            if active
            else (),
            evidence=(
                'pricing/data/wp-a-variants/dragon-talon-assassin.json:/variants/0/player/Helmet/0',
                "third-parties/d2data/json/setitems.json:/Guillaume's Face",
                'third-parties/d2data/json/magicprefix.json:/396',
                'third-parties/d2data/json/magicsuffix.json:/171',
            ),
        )


CASES = tuple(cases())
