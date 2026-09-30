"""Guide-qualified equipment uses retain distinct companions and native socket children."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


SPECS = (
    (
        'poison-nova-necromancer',
        'Necromancer',
        "Trang-Oul's Wing",
        'Cantor Trophy',
        ("Trang-Oul's Claws", "Trang-Oul's Girth"),
    ),
    ('strafe-amazon', 'Amazon', 'Angelic Halo', 'Ring', ('Angelic Wings',)),
    ('strafe-amazon', 'Amazon', 'Angelic Wings', 'Amulet', ('Angelic Halo',)),
    ('berserk-barbarian', 'Barbarian', 'Angelic Halo', 'Ring', ('Angelic Wings',)),
    ('berserk-barbarian', 'Barbarian', 'Angelic Wings', 'Amulet', ('Angelic Halo',)),
    ('double-throw-barbarian-guide', 'Barbarian', 'Angelic Wings', 'Amulet', ('Angelic Halo',)),
    (
        'berserk-barbarian',
        'Barbarian',
        "Immortal King's Forge",
        'War Gauntlets',
        ("Immortal King's Pillar", "Immortal King's Detail"),
    ),
    (
        'berserk-barbarian',
        'Barbarian',
        "Immortal King's Pillar",
        'War Boots',
        ("Immortal King's Forge", "Immortal King's Detail"),
    ),
    (
        'double-throw-barbarian-guide',
        'Barbarian',
        "Immortal King's Forge",
        'War Gauntlets',
        ("Immortal King's Pillar", "Immortal King's Detail"),
    ),
    (
        'double-throw-barbarian-guide',
        'Barbarian',
        "Immortal King's Pillar",
        'War Boots',
        ("Immortal King's Forge", "Immortal King's Detail"),
    ),
    ('dragon-talon-assassin', 'Assassin', 'Stormlash', 'Scourge', ('Shael Rune',)),
    ('berserk-barbarian', 'Barbarian', 'Rune Master', 'Ettin Axe', ('Ist Rune',) * 5),
)


def cases():
    for build, cls, name, base, companions in SPECS:
        slug = name.lower().replace("'", '-').replace(' ', '-')
        suffix = 'named-shield-tail' if name == "Trang-Oul's Wing" else 'qualified-equipment'
        role = f'{build}-{slug}-{suffix}'
        socketed = name in ('Stormlash', 'Rune Master')
        item = Item(base, 'unique' if socketed else 'set', name)
        context = {'player_class': cls}
        if socketed:
            item = replace(
                item,
                sockets=len(companions),
                socket_contents='filled',
                socket_items=tuple(SocketItem(n) for n in companions),
            )
            variants = (
                ('ready', item, context, 'true'),
                ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                (
                    'wrong-filler',
                    replace(item, socket_items=(SocketItem('El Rune'),) * len(companions)),
                    context,
                    'false',
                ),
            )
        else:
            variants = (
                ('ready', item, {**context, 'player_items': companions}, 'true'),
                ('missing', item, {**context, 'player_items': ()}, 'false'),
                ('unknown', item, context, 'unknown'),
                ('self-is-not-companion', item, {**context, 'player_items': (name,) * 2}, 'false'),
            )
            if len(companions) == 2:
                variants += (('duplicate', item, {**context, 'player_items': (companions[0],) * 2}, 'false'),)
        for label, candidate, ctx, truth in variants:
            yield Case(
                id=f'qualified-table/{build}/{slug}/{label}',
                item=candidate,
                context=ctx,
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={
                    'assessment': IsPartialDict(
                        roles=Contains(IsPartialDict(id=role, dependencies=Contains(IsPartialDict(status=truth))))
                    )
                },
                evidence=(f'pricing/raw/mr/guides__{build}.html:Gear Options / {name}',),
            )


def upgraded_deathbit_cases():
    for slot in ('weapon', 'off-hand'):
        role = f'double-throw-barbarian-guide-deathbit-{slot}-named-throwing-alternative'
        for label, base, truth in (('upgraded', 'Flying Knife', 'true'), ('original', 'Battle Dart', 'false')):
            yield Case(
                id=f'qualified-table/deathbit/{slot}/{label}',
                item=Item(base, 'unique', 'Deathbit', ((253, 0, 25),)),
                context={'player_class': 'Barbarian'},
                covers=(role,),
                scenario='positive' if truth == 'true' else 'negative',
                expected={
                    'assessment': IsPartialDict(
                        roles=Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))
                    )
                },
                evidence=('pricing/raw/mr/guides__double-throw-barbarian-guide.html:Deathbit (Upgraded)',),
            )


def rune_master_capacity_cases():
    role = 'berserk-barbarian-rune-master-qualified-equipment'
    for sockets, status in ((3, 'failed'), (4, 'failed'), (5, 'partial'), (None, 'partial')):
        yield Case(
            id=f'qualified-table/rune-master/capacity-{sockets}',
            item=Item('Ettin Axe', 'unique', 'Rune Master', sockets=sockets),
            context={'player_class': 'Barbarian'},
            covers=(role,),
            scenario='unknown' if sockets is None else 'positive' if sockets == 5 else 'negative',
            expected={'assessment': IsPartialDict(roles=Contains(IsPartialDict(id=role, status=status)))},
            evidence=('pricing/data/wp-a-builds.json:/berserk-barbarian/slots/Off-Hand/2',),
        )


CASES = (*cases(), *upgraded_deathbit_cases(), *rune_master_capacity_cases())
