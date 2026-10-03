"""Opalvein elemental cohorts keep the native random modifier exclusive."""

from dataclasses import replace
from itertools import combinations, product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


FIXED = ((105, 0, 10), (195, 25487, 2))
ITEM = Item('Ring', 'unique', 'Opalvein', (), complete=True, named_table_id=416)
KEYS = ['329:0', '331:0', '330:0', '86:0', '138:0', '39:0', '41:0', '43:0', '45:0']


def specimen(choice=329, roll=3, resist=6, life=1, mana=1):
    return replace(
        ITEM,
        raw_stats=(
            *FIXED,
            (choice, 0, roll),
            *((s, 0, resist) for s in (39, 41, 43, 45)),
            (86, 0, life),
            (138, 0, mana),
        ),
    )


def additional_choice_cases():
    for stats, limits in (((357,), (3, 5)), ((332,), (3, 5)), ((17, 18), (20, 40))):
        for roll, resist, life, mana in product(limits, (6, 8), (1, 3), (1, 3)):
            base = specimen(329, 3, resist, life, mana)
            raw = (*(r for r in base.raw_stats if r[0] != 329), *((s, 0, roll) for s in stats))
            yield make_case(f'other-{stats[0]}-{roll}-{resist}-{life}-{mana}', replace(base, raw_stats=raw), False)
    base = specimen(331)
    for stat, low, high in ((331, 3, 5), (39, 6, 8), (41, 6, 8), (43, 6, 8), (45, 6, 8), (86, 1, 3), (138, 1, 3)):
        for value in (None, low - 1, high + 1):
            raw = tuple(
                (s, p, value if s == stat else v) for s, p, v in base.raw_stats if s != stat or value is not None
            )
            yield make_case(f'cold-component-{stat}-{value}', replace(base, raw_stats=raw), False)
    yield make_case(
        'cold-unequal-resists',
        replace(base, raw_stats=tuple((s, p, 7 if s == 39 else v) for s, p, v in base.raw_stats)),
        False,
    )
    for label, changes in (
        ('incomplete', {'complete': False}),
        ('unidentified', {'identified': False}),
        ('ethereal', {'ethereal': True}),
        ('unknown-ethereal', {'ethereal': None}),
        ('socketed', {'sockets': 1}),
        ('unknown-sockets', {'sockets': None}),
        ('unknown-contents', {'socket_contents': 'unknown'}),
    ):
        yield make_case('cold-' + label, replace(base, **changes), False)
    alternatives = (((357,), 3), ((17, 18), 20), ((329,), 3), ((331,), 3), ((330,), 3), ((332,), 3))
    for (left, lv), (right, rv) in combinations(alternatives, 2):
        base = specimen(left[0], lv)
        raw = (*base.raw_stats, *((s, 0, lv) for s in left[1:]), *((s, 0, rv) for s in right))
        yield make_case(f'choice-pair-{left[0]}-{right[0]}', replace(base, raw_stats=raw), False)


def cases():
    for choice, roll, resist, life, mana in product((329, 331, 330), (3, 5), (6, 8), (1, 3), (1, 3)):
        yield make_case(
            f'{choice}-{roll}-{resist}-{life}-{mana}', specimen(choice, roll, resist, life, mana), choice != 330
        )
    base = specimen()
    for stat in (329, 39, 41, 43, 45, 86, 138):
        yield make_case(
            f'missing-{stat}', replace(base, raw_stats=tuple(r for r in base.raw_stats if r[0] != stat)), False
        )
    for choice in (329, 331, 330):
        for roll in (2, 6):
            yield make_case(f'invalid-choice-{choice}-{roll}', specimen(choice, roll), False)
    for stat, low, high in ((39, 6, 8), (41, 6, 8), (43, 6, 8), (45, 6, 8), (86, 1, 3), (138, 1, 3)):
        for value in (low - 1, high + 1):
            raw = tuple((s, p, value if s == stat else v) for s, p, v in base.raw_stats)
            yield make_case(f'invalid-{stat}-{value}', replace(base, raw_stats=raw), False)
    for choice in (331, 330, 332, 17, 18):
        yield make_case(f'mixed-fire-{choice}', replace(base, raw_stats=(*base.raw_stats, (choice, 0, 3))), False)
    for choice in (357, 332):
        yield make_case(f'unsupported-{choice}', specimen(choice), False)
    yield make_case(
        'physical',
        replace(base, raw_stats=((17, 0, 30), (18, 0, 30), *(r for r in base.raw_stats if r[0] != 329))),
        False,
    )
    yield make_case('multiple-choices', replace(base, raw_stats=(*base.raw_stats, (357, 0, 3))), False)
    yield make_case(
        'unequal-resists',
        replace(base, raw_stats=tuple((s, p, 7 if s == 39 else v) for s, p, v in base.raw_stats)),
        False,
    )
    for label, changes in (
        ('incomplete', {'complete': False}),
        ('unidentified', {'identified': False}),
        ('ethereal', {'ethereal': True}),
        ('unknown-ethereal', {'ethereal': None}),
        ('socketed', {'sockets': 1}),
        ('unknown-sockets', {'sockets': None}),
        ('unknown-contents', {'socket_contents': 'unknown'}),
    ):
        yield make_case(label, replace(base, **changes), False)


def make_case(label, item, qualified):
    status = 'candidate' if qualified else 'unresolved'
    return Case(
        id='opal-trade/' + label,
        item=item,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if qualified else 'unknown',
        covers=('named:unique:Opalvein',),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': KEYS} if qualified else {})},
            'lines': [
                {
                    'text': (
                        'Trade: ordinary candidate — Elemental damage variant '
                        'with verified resistance and recovery rolls.'
                    ),
                    'tone': 'tier_low',
                }
            ]
            if qualified
            else [],
        },
        report_contains=('Trade tier: high',) if qualified or label == 'incomplete' or label == 'missing-329' else (),
        report_absent=('Trade: use only', 'Trade: premium candidate'),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


CASES = (*tuple(cases()), *tuple(additional_choice_cases()))
