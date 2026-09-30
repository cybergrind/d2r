"""Mercenary life leech must not be highlighted for an unknown or spell-only bearer."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


def cases():
    for name, suffix, stats, defensive in (
        ('Undead Crown', 'undead-crown', ((60, 0, 5), (45, 0, 50)), ('45:0',)),
        ('Bulwark', 'bulwark', ((60, 0, 6), (36, 0, 10), (76, 0, 5), (99, 0, 20)), ('36:0', '76:0', '99:0')),
    ):
        role = 'fissure-starter-merc-' + suffix
        for quality in ('unique',) if suffix == 'undead-crown' else ('normal', 'superior', 'low_quality'):
            item = Item('Crown', quality, name, stats)
            if suffix == 'bulwark':
                item = replace(
                    item,
                    runeword=name,
                    sockets=3,
                    socket_contents='filled',
                    socket_items=tuple(SocketItem(n + ' Rune') for n in ('Shael', 'Io', 'Sol')),
                )
            for label, candidate, klass, merc, leech in (
                ('prayer', item, 'Druid', 'Act 2 Prayer', True),
                ('rogue', item, 'Druid', 'Act 1 Cold', True),
                ('unknown-bearer', item, 'Druid', None, False),
                ('caster', item, 'Druid', 'Act 3 Fire', False),
                ('zero-leech', replace(item, raw_stats=((60, 0, 0), *stats[1:])), 'Druid', 'Act 2 Prayer', False),
                ('wrong-class', item, 'Barbarian', 'Act 2 Prayer', False),
                ('unknown-class', item, None, 'Act 2 Prayer', False),
                ('unidentified', replace(item, identified=False), 'Druid', 'Act 2 Prayer', False),
            ):
                active = klass == 'Druid' and candidate.identified
                keys = (*defensive, '60:0') if leech else defensive if active else ()
                yield Case(
                    id=f'fissure-starter-leech/{suffix}/{quality}/{label}',
                    item=candidate,
                    context={'player_class': klass, 'mercenary_type': merc},
                    covers=(role,),
                    scenario='unknown' if label.startswith('unknown') else 'positive' if leech else 'negative',
                    expected={
                        'assessment': IsPartialDict(
                            stat_evaluation=IsPartialDict(
                                annotations=IsPartialDict(
                                    {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in keys}
                                )
                            )
                        )
                    },
                    absent_stat_configurations={} if leech else {'60:0': (role + '-stats',)},
                    absent_configurations=() if active else (role + '-stats',),
                    evidence=('pricing/raw/mr/guides__fissure-druid.html:Starter / Mercenary',),
                )


CASES = tuple(cases())
