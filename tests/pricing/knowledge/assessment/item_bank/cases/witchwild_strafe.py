"""A specific upgraded Witchwild planner setup requires both actual socket jewels."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'strafe-amazon-witchwild-string-magic-find'
CONFIG = ROLE + '-stats'
STONE = SocketItem(
    'Colossal Jewel',
    (
        (17, 0, 30),
        (18, 0, 30),
        (21, 0, 10),
        (22, 0, 10),
        (366, 0, 5),
        (85, 0, 3),
        (80, 0, 15),
        (79, 0, 25),
        (201, 17103, 1),
    ),
    True,
    "Protector's Stone",
    424,
)
JEWEL = SocketItem('Jewel', ((39, 0, 10),), True)


def bow(ed=150):
    return Item(
        'Diamond Bow',
        'unique',
        'Witchwild String',
        (
            (17, 0, ed + 30),
            (18, 0, ed + 30),
            (250, 0, 8),
            (198, 4229, 2),
            (39, 0, 50),
            (41, 0, 40),
            (43, 0, 40),
            (45, 0, 40),
            (80, 0, 15),
            (366, 0, 5),
            (157, 0, 20),
            (194, 0, 2),
        ),
        sockets=2,
        socket_contents='filled',
        socket_items=(STONE, JEWEL),
        named_table_id=192,
    )


def cases():
    original = bow()
    context = {'player_class': 'Amazon'}
    examples = [
        ('minimum-ed', original, context, 'true', True),
        ('maximum-ed', bow(170), context, 'true', True),
        ('wrong-class', original, {'player_class': 'Barbarian'}, 'false', False),
        ('unknown-class', original, {}, 'unknown', False),
        ('not-upgraded', replace(original, base='Short Siege Bow'), context, 'false', False),
        ('impossible-ethereal', replace(original, ethereal=True), context, 'false', False),
        ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown', False),
        ('unidentified', replace(original, identified=False), context, 'false', False),
        ('one-linked-child', replace(original, socket_items=(STONE,)), context, 'true', False),
        (
            'rune-in-second-socket',
            replace(original, socket_items=(STONE, SocketItem('Ist Rune'))),
            context,
            'true',
            False,
        ),
        ('two-ordinary-jewels', replace(original, socket_items=(JEWEL, JEWEL)), context, 'true', False),
        (
            'child-mf-below-bound',
            replace(original, socket_items=(replace(STONE, raw_stats=((80, 0, 14),)), JEWEL)),
            context,
            'true',
            False,
        ),
        (
            'unread-stone-stats',
            replace(original, socket_items=(replace(STONE, raw_stats=(), complete=False), JEWEL)),
            context,
            'true',
            False,
        ),
        ('unknown-contents', replace(original, socket_items=(), socket_contents='unknown'), context, 'unknown', False),
        (
            'empty-sockets',
            replace(original, raw_stats=((194, 0, 2),), socket_items=(), socket_contents='empty'),
            context,
            'false',
            False,
        ),
        (
            'owned-stone-not-socketed',
            replace(original, socket_items=(JEWEL, JEWEL)),
            {**context, 'player_items': ["Protector's Stone"]},
            'true',
            False,
        ),
        ('uncaptured-parent', replace(original, raw_stats=((194, 0, 2),)), context, 'true', False),
    ]
    keys = ('17:0', '18:0', '250:0', '198:4229', '39:0', '41:0', '43:0', '45:0', '80:0', '366:0')
    for label, item, loadout, truth, active in examples:
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if active:
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(
                            contributions=Contains(
                                IsPartialDict(
                                    configuration_id=CONFIG,
                                    role_id=ROLE,
                                    desirability='supporting'
                                    if key in ('39:0', '41:0', '43:0', '45:0')
                                    else 'desirable',
                                )
                            )
                        )
                        for key in keys
                    }
                )
            )
        yield Case(
            id='witchwild-strafe/' + label,
            item=item,
            context=loadout,
            covers=(ROLE,),
            scenario='positive'
            if active
            else 'unknown'
            if label.startswith(('unknown', 'unread', 'uncaptured', 'one-linked'))
            else 'negative',
            expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
            absent_configurations=() if active else (CONFIG,),
            absent_stat_configurations={'157:0': (CONFIG,)},
            report_contains=('Witchwild String', 'Sockets: 2', "Protector's Stone", 'Amplify Damage', 'Trade tier:')
            if active
            else (),
            evidence=(
                'pricing/data/wp-a-builds.json:/strafe-amazon/variants/2/player/Weapon/0',
                'third-parties/d2data/json/uniqueitems.json:/192',
                'third-parties/d2data/json/uniqueitems.json:/424',
            ),
        )


CASES = tuple(cases())
