"""Ordinary original boots retain fixed combat mods even at the minimum defense roll."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def boots(ed=160):
    return Item(
        'War Boots',
        'unique',
        'Gore Rider',
        (
            (31, 0, 54 * (100 + ed) // 100),
            (16, 0, ed),
            (91, 0, -25),
            (141, 0, 15),
            (96, 0, 30),
            (136, 0, 15),
            (135, 0, 10),
            (73, 0, 34),
            (11, 0, 20 * 256),
        ),
        complete=True,
    )


def cases():
    variants = [(f'ed-{ed}', boots(ed), True) for ed in (160, 164, 182, 199, 200)]
    variants += [(f'invalid-ed-{ed}', boots(ed), False) for ed in (159, 201)]
    original = boots()
    variants += [
        (
            'unknown-ed',
            replace(original, raw_stats=tuple(s for s in original.raw_stats if s[0] != 16), complete=False),
            False,
        ),
        ('upgraded', replace(original, base='Myrmidon Greaves'), False),
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
            id='gore-rider-trade/' + label,
            item=candidate,
            context={},
            covers=('named:unique:Gore Rider',),
            scenario='positive' if qualifies else 'unknown' if label.startswith('unknown') else 'negative',
            expected={
                'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status)),
                'price_estimate': IsPartialDict(estimate_ist=9.32, sellers=3, basis='classified_exact_variant_asks')
                if label == 'ed-200'
                else IsPartialDict(estimate_ist=None),
            },
            report_contains=('low defense still has trade interest.',) if qualifies else (),
            report_absent=() if qualifies else ('Trade: ordinary candidate',),
            evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
            trade_checks={
                'schema_version': 1,
                'qualification': {'status': status},
                'lines': [
                    {
                        'text': 'Trade: ordinary candidate — Crushing Blow, Deadly Strike and Open Wounds are fixed; '
                        'low defense still has trade interest.',
                        'tone': 'tier_low',
                    }
                ]
                if qualifies
                else [],
            },
        )


CASES = tuple(cases())
