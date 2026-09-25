import pytest

from inventory_tracking.items.metadata import decode_stats


@pytest.mark.parametrize('rate', [1, 10, 30])
def test_replenish_quantity_preserves_native_rate_without_inventing_market_value(rate):
    rows, affixes, unresolved = decode_stats([{'id': 253, 'layer': 0, 'raw': rate}])
    assert not unresolved
    assert rows[0]['text'] == 'Replenishes quantity'
    assert rows[0]['value'] == rate
    assert rows[0]['unit'] == 'replenishment_rate'
    assert not affixes


@pytest.mark.parametrize(('layer', 'raw'), [(0, 0), (0, -1), (1, 10)])
def test_invalid_replenishment_payload_stays_unresolved(layer, raw):
    _, affixes, unresolved = decode_stats([{'id': 253, 'layer': layer, 'raw': raw}])
    assert unresolved
    assert not affixes
