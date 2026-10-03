"""Claws functional modifiers are fixed; native defense cannot imply a premium."""

from dataclasses import replace

from tests.pricing.knowledge.assessment.item_bank.cases.original_set_trade import make_case
from tests.pricing.knowledge.assessment.item_bank.models import Item


FIXED = ((105, 0, 20), (43, 0, 30), (188, 16, 2), (332, 0, 25))


def cases():
    original = Item('Heavy Bracers', 'set', "Trang-Oul's Claws", ((31, 0, 74), *FIXED), complete=True)
    specimens = [
        (f'defense-{defense}', replace(original, raw_stats=((31, 0, defense), *FIXED)), True)
        for defense in (67, 71, 74)
    ]
    specimens.extend(
        (label, replace(original, **changes), False)
        for label, changes in (
            ('upgraded', {'base': 'Vambraces', 'raw_stats': ((31, 0, 97), *FIXED)}),
            ('ethereal', {'ethereal': True}),
            ('unknown-ethereal', {'ethereal': None}),
            ('socketed', {'sockets': 1}),
            ('unknown-sockets', {'sockets': None}),
            ('unknown-contents', {'socket_contents': 'unknown'}),
            ('unidentified', {'identified': False}),
        )
    )
    for label, item, qualified in specimens:
        case = make_case('claws/' + label, item, qualified)
        yield replace(case, id='claws-trade/' + label)


CASES = tuple(cases())
