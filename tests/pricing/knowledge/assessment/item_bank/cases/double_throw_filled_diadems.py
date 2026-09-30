"""Three distinct ED/IAS jewels must accompany the Diadem's native suffix."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


def cases():
    jewel = SocketItem('Jewel', ((17, 0, 31), (18, 0, 31), (93, 0, 15)), complete=True)
    for slug, stat, value, slot in (('speed', 96, 30, 3), ('nirvana', 2, 21, 4), ('luck', 80, 26, 5)):
        role = f'double-throw-barbarian-guide-{slug}-diadem-filled'
        raw = ((stat, 0, value), (17, 0, 93), (18, 0, 93), (93, 0, 45), (194, 0, 3))
        item = Item('Diadem', 'magic', raw_stats=raw, sockets=3, socket_contents='filled', socket_items=(jewel,) * 3)
        for label, candidate, klass, active in (
            ('native', item, 'Barbarian', True),
            (
                'perfect-jewels',
                replace(
                    item,
                    raw_stats=((stat, 0, value), (17, 0, 120), (18, 0, 120), (93, 0, 45), (194, 0, 3)),
                    socket_items=(SocketItem('Jewel', ((17, 0, 40), (18, 0, 40), (93, 0, 15)), complete=True),) * 3,
                ),
                'Barbarian',
                True,
            ),
            (
                'weak-third',
                replace(
                    item,
                    socket_items=(
                        jewel,
                        jewel,
                        SocketItem('Jewel', ((17, 0, 30), (18, 0, 30), (93, 0, 15)), complete=True),
                    ),
                ),
                'Barbarian',
                False,
            ),
            (
                'fire-res-ruby',
                replace(item, socket_items=(SocketItem('Jewel', ((39, 0, 30), (93, 0, 15)), complete=True),) * 3),
                'Barbarian',
                False,
            ),
            ('missing-third', replace(item, socket_items=(jewel, jewel)), 'Barbarian', False),
            ('empty', replace(item, socket_contents='empty', socket_items=()), 'Barbarian', False),
            ('low-suffix', replace(item, raw_stats=((stat, 0, value - 1), *raw[1:])), 'Barbarian', False),
            (
                'short-ias',
                replace(item, raw_stats=tuple((s, p, 44 if s == 93 else n) for s, p, n in raw)),
                'Barbarian',
                False,
            ),
            ('wrong-class', item, 'Amazon', False),
            ('ethereal', replace(item, ethereal=True), 'Barbarian', False),
            ('unknown-ethereal', replace(item, ethereal=None), 'Barbarian', False),
            ('rare', replace(item, rarity='rare'), 'Barbarian', False),
        ):
            yield Case(
                id=f'double-throw-filled-diadem/{slug}/{label}',
                item=candidate,
                context={'player_class': klass},
                covers=(f'role:{role}:magic',),
                scenario='positive'
                if active
                else 'unknown'
                if label in ('missing-third', 'unknown-ethereal')
                else 'negative',
                expected={
                    'assessment': IsPartialDict(
                        stat_evaluation=IsPartialDict(
                            annotations=IsPartialDict(
                                {
                                    key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                                    for key in (f'{stat}:0', '17:0', '93:0')
                                }
                            )
                        )
                    )
                }
                if active
                else {},
                absent_configurations=() if active else (role + '-stats',),
                report_contains=('Diadem', 'Sockets: 3') if active else (),
                evidence=(f'pricing/data/wp-a-builds.json:/double-throw-barbarian-guide/slots/Helmets/{slot}',),
            )


CASES = tuple(cases())
