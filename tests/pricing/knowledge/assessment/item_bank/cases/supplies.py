"""Ordinary supplies: fixed identity, impossible modifier, and unknown capture."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    ('isc', 'Scroll of Identify', None, 'Identifies an unidentified item.'),
    ('tsc', 'Scroll of Town Portal', None, 'Opens a portal to town.'),
    ('ibk', 'Tome of Identify', 12, 'Contents: 12/20.'),
    ('tbk', 'Tome of Town Portal', 0, 'Refill this empty tome'),
    ('key', 'Key', 5, 'Contents: 5/12.'),
    ('aqv', 'Arrows', 250, 'Ammunition for bows.'),
    ('cqv', 'Bolts', 125, 'Ammunition for crossbows.'),
)


def cases():
    for code, name, quantity, text in EXAMPLES:
        stats = () if quantity is None else ((70, 0, quantity),)
        item = Item(name, 'normal', raw_stats=stats, complete=True)
        for scenario, specimen in (
            ('positive', item),
            ('negative', replace(item, raw_stats=(*stats, (39, 0, 20)))),
            ('unknown', replace(item, complete=False)),
        ):
            expected = {
                'assessment': IsPartialDict(
                    family='supply',
                    quality_policy='supply',
                    utility=IsPartialDict(
                        status='usable' if scenario == 'positive' else 'review',
                        quantity=quantity,
                        variable_rolls=False,
                    ),
                    contract=IsPartialDict(policy='supply', base_code=code)
                    if scenario == 'positive' and quantity is None
                    else None,
                ),
                'price_estimate': IsPartialDict(estimate_ist=None),
            }
            if scenario == 'unknown':
                expected['price_estimate'] = IsPartialDict(estimate_ist=None, unavailable_reason='capture_incomplete')
            yield Case(
                id=f'supply/{code}/{scenario}',
                item=specimen,
                context={},
                expected=expected,
                covers=('supply:' + code,),
                scenario=scenario,
                report_contains=(text, 'Supply use'),
                evidence=(f'third-parties/d2data/json/misc.json:/{code}',),
            )


CASES = tuple(cases())
