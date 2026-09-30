"""General Fissure CoH utility is not restricted to the Ubers Dusk Shroud example."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'fissure-druid-chains-of-honor-general-armor'
KEYS = ('127:0', '39:0', '41:0', '43:0', '45:0', '36:0', '0:0', '74:0', '80:0', '16:0')
STATS = (
    (127, 0, 2),
    (39, 0, 65),
    (41, 0, 65),
    (43, 0, 65),
    (45, 0, 65),
    (36, 0, 8),
    (0, 0, 20),
    (74, 0, 7),
    (80, 0, 25),
    (16, 0, 70),
    (60, 0, 8),
    (121, 0, 200),
    (122, 0, 100),
)


def cases():
    for quality in ('normal', 'superior', 'low_quality'):
        item = Item(
            'Archon Plate',
            quality,
            'Chains of Honor',
            STATS,
            runeword='Chains of Honor',
            sockets=4,
            socket_contents='filled',
            socket_items=tuple(SocketItem(n + ' Rune') for n in ('Dol', 'Um', 'Ber', 'Ist')),
        )
        for label, candidate, cls, usable in (
            ('archon', item, 'Druid', True),
            ('dusk', replace(item, base='Dusk Shroud'), 'Druid', True),
            ('sacred', replace(item, base='Sacred Armor'), 'Druid', True),
            ('ethereal', replace(item, ethereal=True), 'Druid', False),
            ('unknown-ethereal', replace(item, ethereal=None), 'Druid', False),
            ('wrong-class', item, 'Paladin', False),
            ('unknown-class', item, None, False),
            ('unmade', replace(item, runeword=None, socket_contents='empty', socket_items=()), 'Druid', False),
            ('illegal-shield', replace(item, base='Monarch'), 'Druid', False),
        ):
            yield Case(
                id=f'fissure-general-coh/{quality}/{label}',
                item=candidate,
                context={'player_class': cls},
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
                absent_stat_configurations=dict.fromkeys(('60:0', '121:0', '122:0'), (ROLE + '-stats',)),
                evidence=(
                    'pricing/raw/mr/guides__fissure-druid.html:Gear Options / Body Armor',
                    'third-parties/d2data/json/runes.json:/Chains of Honor',
                ),
            )


CASES = tuple(cases())
