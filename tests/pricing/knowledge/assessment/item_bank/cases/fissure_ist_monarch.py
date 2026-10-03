"""Four Ist runes do not supply the Monarch's native Deflecting properties."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'fissure-druid-magic-find-shield-ist-filled'
RAW = ((20, 0, 42), (102, 0, 30), (80, 0, 100), (194, 0, 4))
ITEM = Item(
    'Monarch', 'magic', raw_stats=RAW, sockets=4, socket_contents='filled', socket_items=(SocketItem('Ist Rune'),) * 4
)


def cases():
    for label, item, klass, active in (
        ('native', ITEM, 'Druid', True),
        ('reordered', replace(ITEM, socket_items=ITEM.socket_items[::-1]), 'Druid', True),
        ('normal', replace(ITEM, rarity='normal'), 'Druid', False),
        ('rare', replace(ITEM, rarity='rare'), 'Druid', False),
        ('empty', replace(ITEM, socket_contents='empty', socket_items=()), 'Druid', False),
        ('missing-ist', replace(ITEM, socket_items=ITEM.socket_items[:3]), 'Druid', False),
        (
            'wrong-fourth',
            replace(ITEM, socket_items=(*ITEM.socket_items[:3], SocketItem('Shael Rune'))),
            'Druid',
            False,
        ),
        ('ethereal', replace(ITEM, ethereal=True), 'Druid', False),
        ('unknown-ethereal', replace(ITEM, ethereal=None), 'Druid', False),
        ('wrong-class', ITEM, 'Sorceress', False),
        ('wrong-base', replace(ITEM, base='Aegis'), 'Druid', False),
        ('low-block', replace(ITEM, raw_stats=((20, 0, 41), *RAW[1:])), 'Druid', False),
        ('low-fbr', replace(ITEM, raw_stats=tuple((s, p, 29 if s == 102 else n) for s, p, n in RAW)), 'Druid', False),
        ('low-mf', replace(ITEM, raw_stats=tuple((s, p, 99 if s == 80 else n) for s, p, n in RAW)), 'Druid', False),
    ):
        yield Case(
            id=f'fissure-ist-monarch/{label}',
            item=item,
            context={'player_class': klass},
            covers=(f'role:{ROLE}:magic',),
            scenario='positive'
            if active
            else 'unknown'
            if label in ('missing-ist', 'unknown-ethereal')
            else 'negative',
            expected={
                'assessment': IsPartialDict(
                    stat_evaluation=IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                                for key in ('20:0', '102:0', '80:0')
                            }
                        )
                    )
                )
            }
            if active
            else {},
            absent_configurations=() if active else (ROLE + '-stats',),
            report_contains=('Monarch', 'Sockets: 4', 'Ist') if active else (),
            evidence=('pricing/data/wp-a-builds.json:/fissure-druid/variants/2/player/Off-Hand/0',),
        )


CASES = tuple(cases())
