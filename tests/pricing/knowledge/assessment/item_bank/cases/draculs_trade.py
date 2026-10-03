"""Life-leech trade qualification, distinct from fixed Smite utility and perfect gear."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def gloves(leech=10, strength=14, ed=110, heal=6):
    return Item(
        'Vampirebone Gloves',
        'unique',
        "Dracul's Grasp",
        (
            (31, 0, 66 * (100 + ed) // 100),
            (16, 0, ed),
            (60, 0, leech),
            (0, 0, strength),
            (86, 0, heal),
            (135, 0, 25),
            (198, (82 << 6) | 10, 5),
        ),
        complete=True,
    )


def cases():
    variants = [
        (f'leech-{ll}-str-{strength}-ed-{ed}-heal-{heal}', gloves(ll, strength, ed, heal), ll == 10)
        for ll, strength, ed, heal in product((7, 9, 10), (10, 15), (90, 120), (5, 10))
    ]
    original = gloves()
    for key, low, high in ((60, 7, 10), (0, 10, 15), (16, 90, 120), (86, 5, 10)):
        variants.append(
            (
                f'unknown-roll-{key}',
                replace(original, raw_stats=tuple(s for s in original.raw_stats if s[0] != key), complete=False),
                False,
            )
        )
        for value in (low - 1, high + 1):
            variants.append(
                (
                    f'invalid-roll-{key}-{value}',
                    replace(
                        original, raw_stats=tuple((key, 0, value) if s[0] == key else s for s in original.raw_stats)
                    ),
                    False,
                )
            )
    variants += [
        ('ethereal', replace(original, ethereal=True), False),
        ('unknown-ethereal', observation(original, ethereal=None), False),
        ('unknown-sockets', observation(original, sockets=None), False),
        ('unknown-contents', observation(original, socket_contents='unknown'), False),
        ('filled', observation(original, socket_contents='filled'), False),
        ('unidentified', replace(original, identified=False), False),
        ('socketed', replace(original, sockets=1), False),
    ]
    for label, candidate, qualifies in variants:
        status = 'candidate' if qualifies else 'unresolved'
        yield Case(
            id='draculs-trade/' + label,
            item=candidate,
            context={},
            covers=("named:unique:Dracul's Grasp",),
            scenario='positive' if qualifies else 'unknown' if label.startswith('unknown') else 'negative',
            expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
            report_contains=('Perfect 10% life leech; other rolls need not be perfect.',) if qualifies else (),
            report_absent=() if qualifies else ('Trade: ordinary candidate',),
            evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
            trade_checks={
                'schema_version': 1,
                'qualification': {'status': status},
                'lines': [
                    {
                        'text': 'Trade: ordinary candidate — Perfect 10% life leech; other rolls need not be perfect.',
                        'tone': 'tier_low',
                    }
                ]
                if qualifies
                else [],
            },
        )


CASES = tuple(cases())
