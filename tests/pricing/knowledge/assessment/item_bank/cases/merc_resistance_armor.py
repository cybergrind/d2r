"""Independently specified guide contexts and native four-rune armor examples."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


BUILDS = (
    ('lightning-fury-amazon-guide', 'Amazon', ('Act 2 Might', 'Act 2 Holy Freeze')),
    ('lightning-strike-amazon', 'Amazon', ('Act 2 Holy Freeze',)),
    ('double-throw-barbarian-guide', 'Barbarian', ('Act 2 Might', 'Act 5 Frenzy')),
    ('poison-nova-necromancer', 'Necromancer', ('Act 2 Might',)),
    ('zeal-paladin', 'Paladin', ('Act 2 Might', 'Act 5 Frenzy')),
    ('summoner-necromancer-guide', 'Necromancer', ('Act 2 Might',)),
    ('berserk-barbarian', 'Barbarian', ('Act 2 Might',)),
    ('fissure-druid', 'Druid', ('Act 2 Might', 'Act 5 Bash', 'Act 5 Frenzy')),
    ('enchant-sorceress', 'Sorceress', ('Act 2 Prayer',)),
    ('lightning-sorceress', 'Sorceress', ('Act 2 Might', 'Act 2 Holy Freeze')),
    ('dream-paladin', 'Paladin', ('Act 2 Might',)),
)
RUNES = ('Ral Rune', 'Ort Rune', 'Thul Rune', 'Tal Rune')
KEYS = ('39:0', '41:0', '43:0', '45:0')


def cases():
    for build, klass, mercs in BUILDS:
        role = (
            'zeal-paladin-early-merc-resistance-armor'
            if build == 'zeal-paladin'
            else build + '-merc-resistance-rune-armor'
        )
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                'Dusk Shroud',
                quality,
                raw_stats=((39, 0, 30), (41, 0, 30), (43, 0, 30), (45, 0, 30)),
                sockets=4,
                socket_contents='filled',
                socket_items=tuple(SocketItem(n) for n in RUNES),
            )
            scenarios = [
                ('native', item, klass, mercs[0], True),
                ('ethereal', replace(item, ethereal=True), klass, mercs[0], True),
                ('unknown-ethereal', replace(item, ethereal=None), klass, mercs[0], True),
                ('unknown-bearer', item, klass, None, False),
                ('wrong-bearer', item, klass, 'Act 3 Fire', False),
                ('wrong-class', item, 'Assassin', mercs[0], False),
                ('wrong-base', replace(item, base='Monarch'), klass, mercs[0], False),
                ('empty', replace(item, socket_contents='empty', socket_items=()), klass, mercs[0], False),
                ('missing-child', replace(item, socket_items=item.socket_items[:3]), klass, mercs[0], False),
                (
                    'wrong-payload',
                    replace(item, socket_items=(SocketItem('Perfect Topaz'),) * 4),
                    klass,
                    mercs[0],
                    False,
                ),
                (
                    'short-resistance',
                    replace(item, raw_stats=(*item.raw_stats[:3], (45, 0, 29))),
                    klass,
                    mercs[0],
                    False,
                ),
            ]
            scenarios += [(f'bearer-{i}', item, klass, merc, True) for i, merc in enumerate(mercs[1:])]
            for label, candidate, player, merc, active in scenarios:
                yield Case(
                    id=f'merc-resistance-armor/{build}/{quality}/{label}',
                    item=candidate,
                    context={'player_class': player, 'mercenary_type': merc},
                    covers=(role,),
                    scenario='unknown' if label.startswith('unknown') else 'positive' if active else 'negative',
                    expected={
                        'assessment': IsPartialDict(
                            stat_evaluation=IsPartialDict(
                                annotations=IsPartialDict(
                                    {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in KEYS}
                                )
                            )
                        )
                    }
                    if active
                    else {},
                    absent_configurations=() if active else (role + '-stats',),
                    evidence=(
                        f'pricing/raw/mr/guides__{build}.html:Mercenary Gear Options / Early-Game',
                        'pricing/raw/mr/planners/fc01065b.json:items/93',
                    ),
                )


CASES = tuple(cases())
