from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.item_bank.models import Item


FATHOM = Item(
    'Dimensional Shard',
    'unique',
    "Death's Fathom",
    ((83, 1, 3), (331, 0, 30), (105, 0, 20), (39, 0, 40), (41, 0, 40)),
    complete=True,
)
MARA = Item(
    'Amulet',
    'unique',
    "Mara's Kaleidoscope",
    ((127, 0, 2), *((s, 0, 5) for s in (0, 1, 2, 3)), *((s, 0, 30) for s in (39, 41, 43, 45))),
    complete=True,
)


@pytest.mark.parametrize(
    ('item', 'family', 'stat'),
    [
        (FATHOM, 'weapon', 83),
        (FATHOM, 'weapon', 105),
        (MARA, 'amulet', 127),
        *((MARA, 'amulet', s) for s in (0, 1, 2, 3)),
    ],
)
def test_fixed_named_bonuses_are_exact(item, family, stat):
    for offset in (0, -1, 1):
        specimen = replace(item, raw_stats=tuple((s, p, v + offset if s == stat else v) for s, p, v in item.raw_stats))
        contract, gaps = NamedHandler().contract(normalize(specimen.capture()), family)
        assert (contract is not None) is (offset == 0), (stat, offset, gaps)
        if offset:
            assert any(f'Named roll {stat}:' in g for g in gaps)
