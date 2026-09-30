"""Berserk guide Teleport amulets and staves retain charge availability boundaries."""

from dataclasses import replace

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_teleport_alternatives import emit
from tests.pricing.knowledge.assessment.item_bank.models import Item


def cases():
    context = {'player_class': 'Barbarian'}
    for slot, base, level, maximum in (
        ('weapon-swap-8', 'Long Staff', 6, 33),
        ('amulets-6', 'Amulet', 2, 25),
    ):
        layer = 54 * 64 + level
        role = 'berserk-barbarian-charge-alternative-' + slot
        for quality in ('magic', 'rare'):
            item = Item(base, quality, raw_stats=((204, layer, (maximum << 8) | 1),))
            rows = [
                ('one-charge', item, context, 'true', 'positive'),
                (
                    'full',
                    replace(item, raw_stats=((204, layer, (maximum << 8) | maximum),)),
                    context,
                    'true',
                    'positive',
                ),
                ('depleted', replace(item, raw_stats=((204, layer, maximum << 8),)), context, 'true', 'negative'),
                ('unread', replace(item, raw_stats=()), context, 'unknown', 'unknown'),
                ('absent', replace(item, raw_stats=(), complete=True), context, 'false', 'negative'),
                (
                    'triggered-not-charged',
                    replace(item, raw_stats=((201, 54 * 64 + 3, 10),), complete=True),
                    context,
                    'false',
                    'negative',
                ),
                ('unidentified', replace(item, identified=False), context, 'false', 'negative'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false', 'negative'),
                ('unknown-class', item, {}, 'unknown', 'unknown'),
            ]
            if base == 'Long Staff':
                rows += [
                    ('ethereal-one', replace(item, ethereal=True), context, 'true', 'positive'),
                    (
                        'ethereal-empty',
                        replace(item, ethereal=True, raw_stats=((204, layer, maximum << 8),)),
                        context,
                        'true',
                        'negative',
                    ),
                    ('socketed', replace(item, sockets=2), context, 'true', 'positive'),
                ]
            else:
                rows += [
                    ('invalid-socket', replace(item, sockets=1), context, 'false', 'negative'),
                    ('unknown-sockets', replace(item, sockets=None), context, 'unknown', 'unknown'),
                ]
            for label, candidate, loadout, truth, scenario in rows:
                case = emit(role, label, candidate, loadout, truth, scenario, f'204:{layer}')
                yield replace(case, id=f'berserk/teleport-alternatives/{slot}/{quality}/{label}')


def named_cases():
    role = 'berserk-barbarian-naj-teleport-swap'
    item = Item('Elder Staff', 'set', "Naj's Puzzler", ((204, 3467, (69 << 8) | 1), (105, 0, 30), (127, 0, 1)))
    context = {'player_class': 'Barbarian', 'player_level': 78, 'player_strength': 44, 'player_dexterity': 37}
    rows = [
        ('one-charge', item, context, 'true', 'positive'),
        ('full', replace(item, raw_stats=((204, 3467, (69 << 8) | 69),)), context, 'true', 'positive'),
        ('depleted', replace(item, raw_stats=((204, 3467, 69 << 8),)), context, 'true', 'negative'),
        ('unread', replace(item, raw_stats=()), context, 'true', 'unknown'),
        ('unknown-equipment', item, {'player_class': 'Barbarian'}, 'true', 'unknown'),
        ('wrong-class', item, {**context, 'player_class': 'Sorceress'}, 'false', 'negative'),
        ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown', 'unknown'),
        ('unidentified', replace(item, identified=False), context, 'false', 'negative'),
    ]
    for attr in ('player_level', 'player_strength', 'player_dexterity'):
        rows.append(('below-' + attr, item, {**context, attr: context[attr] - 1}, 'true', 'negative'))
    for label, candidate, loadout, truth, scenario in rows:
        case = emit(role, label, candidate, loadout, truth, scenario, '204:3467')
        yield replace(case, id='berserk/teleport-alternatives/naj/' + label)


CASES = (*cases(), *named_cases())
