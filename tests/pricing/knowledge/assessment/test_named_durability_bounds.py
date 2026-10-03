import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.models import Item


@pytest.mark.parametrize(
    ('name', 'base', 'noneth', 'eth'),
    [
        ('Steelgoad', 'Voulge', (70, 90), (46, 66)),
        ('Pelta Lunata', 'Buckler', (20, 24), (15, 19)),
        ('Umbral Disk', 'Small Shield', (26, 31), (19, 24)),
        ('Stormguild', 'Large Shield', (34, 39), (23, 28)),
        ('Steelclash', 'Kite Shield', (45, 50), (31, 36)),
        ('Bverrit Keep', 'Tower Shield', (140, 160), (111, 131)),
    ],
)
@pytest.mark.parametrize('ethereal', [False, True])
def test_named_durability_includes_base_and_flat_bonus(name, base, noneth, eth, ethereal):
    from pricing.knowledge.assessment.mechanics.named_durability import capture_gap

    low, high = eth if ethereal else noneth
    for value, valid in ((low - 1, False), (low, True), (high, True), (high + 1, False)):
        item = Item(base, 'unique', name, ((73, 0, value),), ethereal=ethereal, complete=True)
        assert (capture_gap(normalize(item.capture()), catalog().named['unique', name]) is None) is valid
