"""All eight native facets: joint rolls, invalid variants and fixed triggers."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item
from tests.pricing.knowledge.assessment.test_facet_catalog_comparisons import VARIANTS


def make_case(spec, label, item, status):
    qualified = status != 'unresolved'
    premium = status == 'premium'
    reason = (
        'Rainbow Facet: '
        + spec[2]
        + (
            ': perfect 5/5 rolls; higher asking segment.'
            if premium
            else ': ordinary roll; premium requires both 5% damage and 5% enemy resistance reduction.'
        )
    )
    return Case(
        id=f'facet-trade/{spec[0]}/{label}',
        item=item,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if qualified else 'unknown',
        covers=('named:unique:Rainbow Facet',),
        trade_checks={
            'schema_version': 1,
            'qualification': {
                'status': status,
                **({'material_stats': [f'{spec[7]}:0', f'{spec[6]}:0']} if qualified else {}),
            },
            'lines': [
                {
                    'text': f'Trade: {"premium" if premium else "ordinary"} candidate — {reason}',
                    'tone': 'tier_high' if premium else 'tier_low',
                }
            ]
            if qualified
            else [],
        },
        report_absent=('Trade: use only',),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


def cases():
    for spec in VARIANTS:
        table, _, _, event, skill, level, damage, pierce, fixed, _ = spec
        fixed_raw = ((event, skill * 64 + level, 100), *((stat, 0, value) for stat, value in fixed))
        item = Item(
            'Jewel',
            'unique',
            'Rainbow Facet',
            ((damage, 0, 5), (pierce, 0, 5), *fixed_raw),
            named_table_id=table,
            complete=True,
        )
        for d, p in product((3, 4, 5), repeat=2):
            yield make_case(
                spec,
                f'{d}-{p}',
                replace(item, raw_stats=((damage, 0, d), (pierce, 0, p), *fixed_raw)),
                'premium' if d == p == 5 else 'candidate',
            )
        for stat in (damage, pierce):
            for value in (None, 2, 6):
                raw = tuple(
                    (s, p, value if s == stat else v) for s, p, v in item.raw_stats if s != stat or value is not None
                )
                yield make_case(spec, f'stat-{stat}-{value}', replace(item, raw_stats=raw), 'unresolved')
        for label, changes in (
            ('unidentified', {'identified': False}),
            ('ethereal', {'ethereal': True}),
            ('unknown-ethereal', {'ethereal': None}),
            ('socketed', {'sockets': 1}),
            ('unknown-sockets', {'sockets': None}),
            ('unknown-contents', {'socket_contents': 'unknown'}),
        ):
            yield make_case(spec, label, replace(item, **changes), 'unresolved')
        for chance in (None, 99):
            raw = tuple(
                (s, p, chance if s == event else v) for s, p, v in item.raw_stats if s != event or chance is not None
            )
            yield make_case(spec, f'trigger-{chance}', replace(item, raw_stats=raw), 'unresolved')
        other = next(s for s in VARIANTS if s[6] == damage and s[0] != table)
        yield make_case(spec, 'other-native-trigger', replace(item, named_table_id=other[0]), 'unresolved')


CASES = tuple(cases())
