"""Loose materials: exact native identity, invalid modifiers and incomplete capture."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from inventory_tracking.items.metadata import metadata
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


RUNES = [
    'El',
    'Eld',
    'Tir',
    'Nef',
    'Eth',
    'Ith',
    'Tal',
    'Ral',
    'Ort',
    'Thul',
    'Amn',
    'Sol',
    'Shael',
    'Dol',
    'Hel',
    'Io',
    'Lum',
    'Ko',
    'Fal',
    'Lem',
    'Pul',
    'Um',
    'Mal',
    'Ist',
    'Gul',
    'Vex',
    'Ohm',
    'Lo',
    'Sur',
    'Ber',
    'Jah',
    'Cham',
    'Zod',
]
GEMS = [
    f'{grade}{gem}'
    for gem in ('Amethyst', 'Diamond', 'Emerald', 'Ruby', 'Sapphire', 'Topaz', 'Skull')
    for grade in ('Chipped ', 'Flawed ', '', 'Flawless ', 'Perfect ')
]


def cases():
    native = {row['name']: row for row in metadata()['bases'].values()}
    for name in [*(f'{rune} Rune' for rune in RUNES), *GEMS]:
        code = native[name]['code']
        item = Item(name, 'normal', complete=True)
        for scenario, specimen in (
            ('positive', item),
            ('negative', replace(item, raw_stats=((39, 0, 20),))),
            ('unknown', replace(item, complete=False)),
        ):
            expected = {
                'assessment': IsPartialDict(
                    family='socket_material',
                    quality_policy='socket_material',
                    contract=IsPartialDict(
                        policy='socket_material',
                        name=name,
                        base_code=code,
                        properties={},
                        ethereal=False,
                        sockets=0,
                        socket_contents='empty',
                    )
                    if scenario == 'positive'
                    else None,
                )
            }
            if scenario != 'positive':
                expected['price_estimate'] = IsPartialDict(estimate_ist=None)
            if scenario == 'unknown':
                expected['price_estimate'] = IsPartialDict(estimate_ist=None, unavailable_reason='capture_incomplete')
            yield Case(
                id=f'socket-material/{name}/{scenario}',
                item=specimen,
                context={},
                expected=expected,
                covers=('socket_material:' + code,),
                scenario=scenario,
                report_contains=(name, 'No variable rolls')
                if scenario == 'positive'
                else (name, 'Price: not assessed'),
                evidence=(f'third-parties/d2data/json/misc.json:/{code}',),
            )


CASES = tuple(cases())
