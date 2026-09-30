"""General Enigma permits legal armor alternatives without borrowing a planner base."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'fissure-druid-enigma-general-armor'
KEYS = ('127:0', '97:54', '96:0', '36:0', '76:0', '220:0', '240:0', '31:0', '86:0', '114:0')
STATS = (
    (127, 0, 2),
    (97, 54, 1),
    (96, 0, 45),
    (36, 0, 8),
    (76, 0, 5),
    (220, 0, 6),
    (240, 0, 8),
    (31, 0, 750),
    (86, 0, 14),
    (114, 0, 15),
)


def cases():
    for quality in ('normal', 'superior', 'low_quality'):
        item = Item(
            'Mage Plate',
            quality,
            'Enigma',
            STATS,
            sockets=3,
            socket_contents='filled',
            runeword='Enigma',
            socket_items=tuple(SocketItem(n + ' Rune') for n in ('Jah', 'Ith', 'Ber')),
        )
        for label, candidate, klass, usable in (
            ('mage', item, 'Druid', True),
            ('dusk', replace(item, base='Dusk Shroud'), 'Druid', True),
            ('archon', replace(item, base='Archon Plate'), 'Druid', True),
            ('breast', replace(item, base='Breast Plate'), 'Druid', True),
            ('ethereal', replace(item, ethereal=True), 'Druid', False),
            ('unknown-ethereal', replace(item, ethereal=None), 'Druid', False),
            ('wrong-class', item, 'Paladin', False),
            ('unknown-class', item, None, False),
            ('unmade', replace(item, runeword=None, socket_contents='empty', socket_items=()), 'Druid', False),
            ('illegal-shield', replace(item, base='Monarch'), 'Druid', False),
            ('unidentified', replace(item, identified=False), 'Druid', False),
        ):
            yield Case(
                id=f'fissure-general-enigma/{quality}/{label}',
                item=candidate,
                context={'player_class': klass},
                covers=(ROLE,),
                scenario='positive' if usable else 'unknown' if label.startswith('unknown') else 'negative',
                expected={
                    'assessment': IsPartialDict(
                        stat_evaluation=IsPartialDict(
                            annotations=IsPartialDict(
                                {key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats')) for key in KEYS}
                            )
                        )
                    )
                }
                if usable
                else {},
                absent_configurations=() if usable else (ROLE + '-stats',),
                evidence=(
                    'pricing/raw/mr/guides__fissure-druid.html:Gear Options / Enigma',
                    'third-parties/d2data/json/runes.json:/Enigma',
                ),
            )


CASES = tuple(cases())
