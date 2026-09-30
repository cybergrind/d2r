"""Concrete embedded planner examples, with actual staffmods and rune contents."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


EXAMPLES = (
    (
        'void',
        'abyss-warlock-table-dagger-void',
        Item(
            'Kriss',
            'normal',
            'Void',
            (
                (127, 0, 2),
                (105, 0, 40),
                (357, 0, 15),
                (97, 402, 3),
                (107, 402, 3),
                (107, 399, 3),
                (107, 382, 3),
                (0, 0, 12),
                (1, 0, 12),
                (2, 0, 12),
                (3, 0, 12),
                (80, 0, 30),
                (204, 5572, 35 << 8),
            ),
            sockets=3,
            socket_contents='filled',
            runeword='Void',
            socket_items=tuple(SocketItem(n) for n in ('Thul Rune', 'Zod Rune', 'Ist Rune')),
        ),
        ('107:402', '107:399', '97:402', '80:0'),
    ),
    (
        'rare',
        'abyss-warlock-table-rare-kris',
        Item(
            'Kriss',
            'rare',
            raw_stats=(
                (83, 7, 2),
                (107, 402, 3),
                (107, 399, 3),
                (107, 377, 3),
                (39, 0, 30),
                (0, 0, 15),
                (74, 0, 5),
                (117, 0, 1),
                (80, 0, 60),
            ),
            sockets=2,
            socket_contents='filled',
            socket_items=(SocketItem('Ist Rune'), SocketItem('Ist Rune')),
        ),
        ('83:7', '107:402', '107:399', '39:0', '0:0', '80:0'),
    ),
    (
        'magic',
        'abyss-warlock-table-dagger-arch-devil',
        Item(
            'Kriss',
            'magic',
            raw_stats=((83, 7, 2), (107, 402, 3), (107, 399, 3), (107, 377, 3), (204, 5827, 82 << 8), (80, 0, 60)),
            sockets=2,
            socket_contents='filled',
            socket_items=(SocketItem('Ist Rune'), SocketItem('Ist Rune')),
        ),
        ('83:7', '107:402', '107:399', '80:0'),
    ),
)

CASES = tuple(
    Case(
        id='abyss/planner-daggers/' + slug,
        item=item,
        context={'player_class': 'Warlock'},
        expected={
            'assessment': IsPartialDict(
                roles=Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth='true'))),
                stat_evaluation=IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                ),
            )
        },
        covers=(role,),
        scenario='positive',
        absent_stat_configurations={
            '117:0': (role + '-stats',),
            '204:5827': (role + '-stats',),
            '204:5572': (role + '-stats',),
        },
        evidence=('pricing/data/appraisal-guide-sections.json', 'pricing/raw/mr/planners/gsg0p0l0.json'),
    )
    for slug, role, item, keys in EXAMPLES
)
