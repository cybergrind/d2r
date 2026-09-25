from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers import HANDLERS
from tests.pricing.knowledge.assessment.test_socket_survival_comparisons import socketed_item


@pytest.mark.parametrize(
    ('base', 'quality', 'name', 'filler', 'stat', 'native', 'bonus'),
    [
        ('Winged Helm', 'set', "Guillaume's Face", 'Fal Rune', 0, 15, 10),
        ('Tiara', 'unique', "Kira's Guardian", 'Lum Rune', 1, 0, 10),
        ('Sallet', 'unique', 'Rockstopper', 'Io Rune', 3, 15, 10),
        *[
            ('Winged Helm', 'set', "Guillaume's Face", n, 0, 15, b)
            for n, b in [
                ('Chipped Amethyst', 3),
                ('Flawed Amethyst', 4),
                ('Amethyst', 6),
                ('Flawless Amethyst', 8),
                ('Perfect Amethyst', 10),
            ]
        ],
    ],
)
def test_named_attribute_fillers_preserve_totals_and_bound_native_roll(
    base, quality, name, filler, stat, native, bonus
):
    item = socketed_item(base, quality, name, [filler], {stat: bonus})
    contract, gaps = HANDLERS['named'].contract(item, 'helm')
    assert contract is not None, gaps
    prop = item.stats[f'{stat}:0']['market_property']
    assert contract.properties[prop] == native + bonus
    assert contract.socket_payload == (filler,)
    # A coherent projected total still must leave a legal intrinsic value.
    row = {**item.stats[f'{stat}:0'], 'value': native + bonus + 1, 'raw': native + bonus + 1}
    bad = replace(
        item, stats={**item.stats, f'{stat}:0': row}, properties={**item.properties, prop: native + bonus + 1}
    )
    assert HANDLERS['named'].contract(bad, 'helm')[0] is None


@pytest.mark.parametrize(('rarity', 'handler'), [('normal', 'base'), ('magic', 'affixed'), ('rare', 'affixed')])
@pytest.mark.parametrize(('filler', 'stat'), [('Fal Rune', 0), ('Lum Rune', 1), ('Io Rune', 3)])
def test_attribute_runes_work_for_base_and_affixed_armor(rarity, handler, filler, stat):
    item = socketed_item('Diadem', rarity, None, [filler], {stat: 10})
    contract, gaps = HANDLERS[handler].contract(item, 'helm')
    assert contract is not None, gaps
    assert contract.socket_payload == (filler,)
