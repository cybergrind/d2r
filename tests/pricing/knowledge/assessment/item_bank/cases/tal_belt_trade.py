"""Every intrinsic MF roll; ordinary trade only for the reviewed15MF segment."""

from dataclasses import replace

from tests.pricing.knowledge.assessment.item_bank.cases.original_set_trade import make_case
from tests.pricing.knowledge.assessment.item_bank.models import Item


FIXED = ((91, 0, -20), (9, 0, 30 * 256), (2, 0, 20), (114, 0, 37))


def specimen(mf=15, defense=40, *, set_bonus=False):
    stats = (*FIXED, (31, 0, defense))
    if mf is not None:
        stats += ((80, 0, mf),)
    if set_bonus:
        stats += ((105, 0, 10),)
    return Item('Mesh Belt', 'set', "Tal Rasha's Fine-Spun Cloth", stats, complete=True)


def cases():
    specimens = [
        (f'mf-{mf}-defense-{defense}-fcr-{fcr}', specimen(mf, defense, set_bonus=bool(fcr)), mf == 15)
        for mf in range(10, 16)
        for defense, fcr in ((35, 0), (40, 0), (95, 0), (100, 0), (95, 10), (100, 10))
    ]
    specimens.extend((f'mf-{mf}', specimen(mf), False) for mf in (None, 9, 16))
    specimens.extend(
        (label, replace(specimen(), **changes), False)
        for label, changes in (
            ('upgraded', {'base': 'Mithril Coil', 'raw_stats': (*FIXED, (31, 0, 65), (80, 0, 15))}),
            ('ethereal', {'ethereal': True}),
            ('unknown-ethereal', {'ethereal': None}),
            ('socketed', {'sockets': 1}),
            ('unknown-sockets', {'sockets': None}),
            ('unknown-contents', {'socket_contents': 'unknown'}),
            ('unidentified', {'identified': False}),
        )
    )
    for label, item, qualified in specimens:
        yield replace(make_case('belt/' + label, item, qualified), id='tal-belt-trade/' + label)


CASES = tuple(cases())
