"""Prose travel alternatives retain charged-skill and pre-Enigma conditions."""

from dataclasses import replace

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_teleport_alternatives import emit
from tests.pricing.knowledge.assessment.item_bank.models import Item


def cases():
    for suffix, base, layer, maximum in (('staf', 'Long Staff', 3462, 33), ('amul', 'Amulet', 3458, 25)):
        role = 'berserk-barbarian-teleport-' + suffix
        context = {'player_class': 'Barbarian', 'player_items': []}
        for quality in ('magic', 'rare'):
            item = Item(base, quality, raw_stats=((204, layer, (maximum << 8) | 1),))
            rows = [
                ('one-charge', item, context, 'true', 'positive'),
                ('depleted', replace(item, raw_stats=((204, layer, maximum << 8),)), context, 'true', 'negative'),
                ('unread-charges', replace(item, raw_stats=()), context, 'unknown', 'unknown'),
                ('absent-charges', replace(item, raw_stats=(), complete=True), context, 'false', 'negative'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false', 'negative'),
                ('unknown-class', item, {'player_items': []}, 'unknown', 'unknown'),
            ]
            rows += [
                ('enigma-equipped', item, {**context, 'player_items': ['Enigma']}, 'true', 'negative'),
                ('unknown-armor', item, {'player_class': 'Barbarian'}, 'true', 'unknown'),
            ]
            if suffix == 'staf':
                rows += [
                    ('ethereal-one-charge', replace(item, ethereal=True), context, 'true', 'positive'),
                ]
            for label, candidate, loadout, truth, scenario in rows:
                case = emit(role, label, candidate, loadout, truth, scenario, f'204:{layer}')
                yield replace(case, id=f'berserk/legacy-teleport/{suffix}/{quality}/{label}')


CASES = tuple(cases())
