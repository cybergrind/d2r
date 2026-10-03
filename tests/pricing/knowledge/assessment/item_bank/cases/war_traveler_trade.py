"""Native boots exercise perfect-MF trade interest through the complete report."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def boots(mf=50, ed=174, base='Battle Boots', defense=None, thorns=6):
    return Item(
        base,
        'unique',
        'War Traveler',
        (
            (80, 0, mf),
            (16, 0, ed),
            (78, 0, thorns),
            (31, 0, defense or 48 * (100 + ed) // 100),
            (0, 0, 10),
            (3, 0, 10),
            (96, 0, 25),
            (154, 0, 40),
            (21, 0, 15),
            (22, 0, 25),
            (72, 0, 48),
            (73, 0, 48),
        ),
        complete=True,
    )


def cases():
    item = boots()
    rows = [
        ('perfect-mf-mid-ed', item, 'candidate'),
        ('perfect-mf-min-ed', boots(ed=150), 'candidate'),
        ('perfect-mf-perfect-ed', boots(ed=190), 'candidate'),
        ('upgraded', boots(base='Mirrored Boots', defense=172), 'candidate'),
        ('mf49', boots(mf=49), 'unresolved'),
        ('mf30', boots(mf=30), 'unresolved'),
        ('ethereal', replace(item, ethereal=True), 'unresolved'),
        ('unknown-ethereal', observation(item, ethereal=None), 'unresolved'),
        ('illegal-mf', boots(mf=51), 'unresolved'),
        ('socketed', replace(item, sockets=1), 'unresolved'),
    ]
    for base in ('Battle Boots', 'Mirrored Boots'):
        slug = 'original' if base == 'Battle Boots' else 'upgraded'
        for mf, ed, thorns in product((30, 49, 50), (150, 190), (5, 10)):
            candidate = boots(
                mf=mf, ed=ed, thorns=thorns, base=base, defense=(63 if slug == 'upgraded' else 48) * (100 + ed) // 100
            )
            rows.append((f'{slug}/rolls/{mf}-{ed}-{thorns}', candidate, 'candidate' if mf == 50 else 'unresolved'))
        maximum = boots(ed=190, thorns=10, base=base, defense=182 if slug == 'upgraded' else 139)
        for stat, values in ((80, (None, 29, 51)), (16, (None, 149, 191)), (78, (None, 4, 11))):
            for value in values:
                raw = tuple(
                    (s, p, value if s == stat else v)
                    for s, p, v in maximum.raw_stats
                    if not (s == stat and value is None)
                )
                rows.append((f'{slug}/invalid/{stat}-{value}', replace(maximum, raw_stats=raw), 'unresolved'))
        for label, changes in [
            ('unidentified', {'identified': False}),
            ('ethereal', {'ethereal': True}),
            ('unknown-ethereal', {'ethereal': None}),
            ('unknown-sockets', {'sockets': None}),
            ('socketed', {'sockets': 1}),
            ('unknown-contents', {'socket_contents': 'unknown'}),
            ('filled', {'socket_contents': 'filled'}),
        ]:
            rows.append((f'{slug}/variant/{label}', observation(maximum, **changes), 'unresolved'))
    for label, candidate, status in rows:
        qualifies = status == 'candidate'
        yield Case(
            id='war-traveler-trade/' + label,
            item=candidate,
            context={},
            covers=('named:unique:War Traveler',),
            scenario='positive' if qualifies else 'unknown' if label == 'unknown-ethereal' else 'negative',
            expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
            report_contains=('Trade: ordinary candidate', 'Perfect 50% magic find') if qualifies else (),
            report_absent=() if qualifies else ('Trade: ordinary candidate',),
            evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
            trade_checks={
                'schema_version': 1,
                'qualification': {'status': status},
                'lines': [
                    {
                        'text': (
                            'Trade: ordinary candidate — Perfect 50% magic find is sought after; '
                            'enhanced defense need not be perfect.'
                        ),
                        'tone': 'tier_low',
                    },
                ]
                if qualifies
                else [],
            },
        )


CASES = tuple(cases())
