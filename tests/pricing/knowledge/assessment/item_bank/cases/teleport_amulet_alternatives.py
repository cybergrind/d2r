"""Explicit remaining guide Teleport amulets, preserving native charge availability."""

from dataclasses import replace

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_teleport_alternatives import emit
from tests.pricing.knowledge.assessment.item_bank.models import Item


USES = (
    ('double-throw-barbarian-guide', 5, 'Barbarian'),
    ('dream-paladin', 4, 'Paladin'),
    ('fissure-druid', 9, 'Druid'),
    ('poison-nova-necromancer', 8, 'Necromancer'),
)


def cases():
    for guide, index, player_class in USES:
        role = f'{guide}-charge-alternative-amulets-{index}'
        context = {'player_class': player_class}
        for quality in ('magic', 'rare'):
            item = Item('Amulet', quality, raw_stats=((204, 3458, (25 << 8) | 1),))
            examples = (
                ('one-charge', item, context, 'true', 'positive'),
                ('full', replace(item, raw_stats=((204, 3458, (25 << 8) | 25),)), context, 'true', 'positive'),
                ('depleted', replace(item, raw_stats=((204, 3458, 25 << 8),)), context, 'true', 'negative'),
                ('unread-charges', replace(item, raw_stats=()), context, 'unknown', 'unknown'),
                ('missing-charges', replace(item, raw_stats=(), complete=True), context, 'false', 'negative'),
                (
                    'trigger-not-charges',
                    replace(item, raw_stats=((201, 3458, 10),), complete=True),
                    context,
                    'false',
                    'negative',
                ),
                ('unidentified', replace(item, identified=False), context, 'false', 'negative'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false', 'negative'),
                ('unread-class', item, {}, 'unknown', 'unknown'),
                ('unread-sockets', replace(item, sockets=None), context, 'unknown', 'unknown'),
                ('impossible-sockets', replace(item, sockets=1), context, 'false', 'negative'),
            )
            for label, candidate, loadout, truth, scenario in examples:
                case = emit(role, label, candidate, loadout, truth, scenario, '204:3458')
                yield replace(
                    case,
                    id=f'teleport-amulet-alternative/{guide}/{quality}/{label}',
                    evidence=(f'pricing/data/wp-a-builds.json:/{guide}/slots/Amulets/{index}',),
                )


CASES = tuple(cases())
