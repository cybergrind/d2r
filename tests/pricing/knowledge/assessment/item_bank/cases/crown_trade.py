"""Native Crown reports: sockets, intrinsic bounds and removable inserts."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


def specimen(defense=349, resist=20, reduction=10):
    return Item(
        'Corona',
        'unique',
        'Crown of Ages',
        ((31, 0, defense), (36, 0, reduction), (127, 0, 1), (99, 0, 30), *((s, 0, resist) for s in (39, 41, 43, 45))),
        sockets=2,
        complete=True,
    )


def cases():
    ordinary = specimen()
    variants = [
        ('minimum', ordinary, True),
        ('maximum', specimen(399, 30, 15), True),
        ('one-socket', replace(ordinary, sockets=1), False),
        ('missing-sockets', replace(ordinary, sockets=None), False),
        ('impossible-sockets', replace(ordinary, sockets=3), False),
        ('unknown-ethereal', replace(ordinary, ethereal=None), False),
        ('unidentified', replace(ordinary, identified=False), False),
        ('incomplete', replace(ordinary, complete=False), False),
        ('missing-reduction', replace(ordinary, raw_stats=tuple(r for r in ordinary.raw_stats if r[0] != 36)), False),
        ('below-defense', specimen(348), False),
        ('above-defense', specimen(400), False),
        ('unknown-inserts', replace(specimen(349, 20, 26), socket_contents='unknown'), True),
        ('unknown-defense-inserts', replace(specimen(409), socket_contents='unknown'), True),
        ('unknown-resistance-inserts', replace(specimen(349, 50), socket_contents='unknown'), True),
        ('null-contents', replace(ordinary, socket_contents=None), True),
        (
            'two-bers',
            replace(
                specimen(349, 20, 26),
                socket_contents='filled',
                socket_items=(SocketItem('Ber Rune'), SocketItem('Ber Rune')),
            ),
            True,
        ),
    ]
    for axis, low, high in ((31, 349, 399), (36, 10, 15), (39, 20, 30)):
        for value in (None, low - 1, low, high, high + 1):
            affected = {39, 41, 43, 45} if axis == 39 else {axis}
            raw = tuple(
                (stat, layer, value if stat in affected else n)
                for stat, layer, n in ordinary.raw_stats
                if value is not None or stat not in affected
            )
            variants.append(
                (f'axis-{axis}-{value}', replace(ordinary, raw_stats=raw), value is not None and low <= value <= high)
            )
    for stat in (39, 41, 43, 45):
        variants.append(
            (
                f'missing-resist-{stat}',
                replace(ordinary, raw_stats=tuple(r for r in ordinary.raw_stats if r[0] != stat)),
                False,
            )
        )
    for label, changes in (
        ('zero', {'sockets': 0}),
        ('zero-unidentified', {'sockets': 0, 'identified': False}),
        ('zero-ethereal', {'sockets': 0, 'ethereal': True}),
        ('zero-unknown-ethereal', {'sockets': 0, 'ethereal': None}),
        ('zero-unknown-contents', {'sockets': 0, 'socket_contents': 'unknown'}),
        ('two-ethereal', {'ethereal': True}),
    ):
        variants.append((label, replace(ordinary, **changes), False))
    for label, item, candidate in variants:
        reason = 'Two sockets support defensive Uber setups; no proven intrinsic-roll premium.'
        if item.socket_contents != 'empty':
            reason += ' Assess inserts separately.'
        yield Case(
            id=f'crown-trade/{label}',
            item=item,
            context={},
            scenario='positive' if candidate else 'unknown' if label.startswith(('missing', 'unknown')) else 'negative',
            covers=('named:unique:Crown of Ages',),
            expected={
                'assessment': IsPartialDict(
                    trade_qualification=IsPartialDict(
                        status='candidate' if candidate else 'unresolved',
                    )
                )
            },
            report_contains=('Trade: candidate', 'Two sockets support defensive Uber setups') if candidate else (),
            report_absent=('Trade: premium',) if candidate else ('Trade: candidate', 'Trade: premium'),
            evidence=('pricing/data/appraisal-crown-of-ages-roll-review-2026-10-02.json',),
            trade_checks={
                'schema_version': 1,
                'qualification': {'status': 'candidate' if candidate else 'unresolved'},
                'lines': [
                    {
                        'text': 'Trade: candidate — ' + reason,
                        'tone': 'tier_high' if item.socket_contents == 'empty' else 'tier_med',
                    }
                ]
                if candidate
                else [],
            },
        )


CASES = tuple(cases())
