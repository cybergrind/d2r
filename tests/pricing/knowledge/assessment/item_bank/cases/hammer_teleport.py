"""Hammerdin Weapon-Swap/3: a charged staff, not a passive Teleport bonus."""

from dataclasses import replace

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_teleport_alternatives import emit
from tests.pricing.knowledge.assessment.item_bank.models import Item


def cases():
    role = 'blessed-hammer-paladin-charge-alternative-weapon-swap-3'
    context = {'player_class': 'Paladin'}
    for quality in ('magic', 'rare'):
        item = Item('Long Staff', quality, raw_stats=((204, 3462, (33 << 8) | 1),))
        for label, candidate, loadout, truth, scenario in (
            ('one-charge', item, context, 'true', 'positive'),
            ('full-charges', replace(item, raw_stats=((204, 3462, (33 << 8) | 33),)), context, 'true', 'positive'),
            ('ethereal-charge', replace(item, ethereal=True), context, 'true', 'positive'),
            ('depleted', replace(item, raw_stats=((204, 3462, 33 << 8),)), context, 'true', 'negative'),
            (
                'ethereal-depleted',
                replace(item, ethereal=True, raw_stats=((204, 3462, 33 << 8),)),
                context,
                'true',
                'negative',
            ),
            ('unread-charges', replace(item, raw_stats=()), context, 'unknown', 'unknown'),
            ('absent-charges', replace(item, raw_stats=(), complete=True), context, 'false', 'negative'),
            (
                'triggered-not-charged',
                replace(item, raw_stats=((198, 3462, 5),), complete=True),
                context,
                'false',
                'negative',
            ),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false', 'negative'),
            ('unknown-class', item, {}, 'unknown', 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false', 'negative'),
        ):
            row = emit(role, label, candidate, loadout, truth, scenario, '204:3462')
            yield replace(row, id=f'hammer/teleport/{quality}/{label}')


CASES = tuple(cases())
