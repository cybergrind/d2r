"""Native socket fixtures must distinguish unique variants sharing a display name."""

import struct

import pytest

from inventory_tracking.items.identity import IDENTITY_OFFSET, QUALITY_OFFSET
from tests.pricing.knowledge.assessment.item_bank.models import Item, SocketItem


def test_compound_rare_jewel_retains_native_quality():
    child = SocketItem('Jewel', ((99, 0, 7), (39, 0, 40), (114, 0, 12)), True, rare=True)
    data = bytes.fromhex(child.native_capture(0)['item_data_hex'])
    assert struct.unpack_from('<I', data, QUALITY_OFFSET)[0] == 6


@pytest.mark.parametrize(
    'child',
    [
        SocketItem('Shael Rune'),
        SocketItem('Jewel', name='Rainbow Facet', unique_table_id=392),
    ],
)
def test_rare_jewel_flag_cannot_override_another_socket_identity(child):
    from dataclasses import replace

    with pytest.raises(ValueError, match='Rare socket fixture'):
        replace(child, rare=True).native_capture(0)


@pytest.mark.parametrize('table_id', range(392, 400))
def test_rainbow_facet_fixture_retains_selected_native_variant(table_id):
    child = SocketItem('Jewel', name='Rainbow Facet', unique_table_id=table_id)
    data = bytes.fromhex(child.native_capture(0)['item_data_hex'])
    assert struct.unpack_from('<I', data, IDENTITY_OFFSET)[0] == table_id
    assert struct.unpack_from('<I', data, QUALITY_OFFSET)[0] == 7
    item = Item('Monarch', 'magic', sockets=1, socket_contents='filled', socket_items=(child,)).capture()
    assert item['item']['socket_items'][0]['name'] == 'Rainbow Facet'


@pytest.mark.parametrize(('name', 'table_id'), [('Rainbow Facet', 0), (None, 392)])
def test_unique_variant_cannot_override_missing_or_contradictory_identity(name, table_id):
    with pytest.raises(ValueError, match=r'(Unique socket variant|Socket fixture requires)'):
        SocketItem('Jewel', name=name, unique_table_id=table_id).native_capture(0)
