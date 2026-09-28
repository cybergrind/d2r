from unittest.mock import Mock, patch

import pytest

from inventory_tracking.models import Observation, ObservationStatus, ShopPanel
from inventory_tracking.native.layout import PANEL_FLAGS
from inventory_tracking.tracking.shop_panel import SMITHS, loaded_vendors, observe_shop_panel


IMAGES = {'identity': {'pid': 12}, 'candidate_base': 0x140000000}


def panels(*names):
    return Observation(100, {name: name in names for name in PANEL_FLAGS})


def vendor(txt_id, unit_id=1, stable=True):
    return {'address': 0x1000 + unit_id, 'type': 1, 'txt_id': txt_id, 'unit_id': unit_id, 'identity_stable': stable}


def snapshot(*units):
    return {'groups': {'monsters': {'units': list(units)}}}


def grids(occupied):
    return {2: {'width': 10, 'height': 10, 'cells': [0x2000 if occupied else 0] + [0] * 99}}


def test_loaded_vendors_reads_only_stable_vendor_units():
    reads = []

    def read_grids(read, unit):
        reads.append(unit['txt_id'])
        return grids(unit['txt_id'] == 154)

    with patch('inventory_tracking.tracking.shop_panel.read_owner_grids', side_effect=read_grids):
        units = snapshot(vendor(154), vendor(148, 2), vendor(511, 3, stable=False), vendor(162, 4))
        loaded = loaded_vendors(object(), units)
    assert loaded == [154]
    assert reads == [154, 148]


@pytest.mark.parametrize(
    ('flags', 'loaded', 'expected'),
    [
        (('inventory', 'npc_shop'), [154], ShopPanel(True, 'Charsi', True)),
        (('npc_shop',), [148], ShopPanel(True, 'Akara', False)),
        (('inventory',), [154], ShopPanel(False)),
    ],
)
def test_open_shop_names_the_single_loaded_vendor(flags, loaded, expected):
    with (
        patch('inventory_tracking.tracking.shop_panel.observe_panels', return_value=panels(*flags)),
        patch('inventory_tracking.tracking.shop_panel.os.open', return_value=3),
        patch('inventory_tracking.tracking.shop_panel.os.close'),
        patch('inventory_tracking.tracking.shop_panel.process_mappings', return_value=[]),
        patch('inventory_tracking.tracking.shop_panel.loaded_vendors', return_value=loaded),
    ):
        observation = observe_shop_panel(12, IMAGES, snapshot())
    assert observation.status == ObservationStatus.AVAILABLE
    assert observation.value == expected


@pytest.mark.parametrize(
    ('loaded', 'after', 'reason'),
    [
        ([], panels('npc_shop'), 'No loaded vendor stock'),
        ([154, 178], panels('npc_shop'), 'Several vendors'),
        ([154], panels(), 'Shop closed during read'),
        (OSError('mem'), panels('npc_shop'), 'mem'),
    ],
)
def test_ambiguous_or_changing_stock_is_unavailable_not_a_guess(loaded, after, reason):
    vendors = Mock(side_effect=loaded) if isinstance(loaded, Exception) else Mock(return_value=loaded)
    with (
        patch('inventory_tracking.tracking.shop_panel.observe_panels', side_effect=[panels('npc_shop'), after]),
        patch('inventory_tracking.tracking.shop_panel.os.open', return_value=3),
        patch('inventory_tracking.tracking.shop_panel.os.close') as close,
        patch('inventory_tracking.tracking.shop_panel.process_mappings', return_value=[]),
        patch('inventory_tracking.tracking.shop_panel.loaded_vendors', vendors),
    ):
        observation = observe_shop_panel(12, IMAGES, snapshot())
    assert observation.status == ObservationStatus.UNAVAILABLE
    assert reason in observation.reason
    close.assert_called_once_with(3)


def test_unreadable_panel_flags_skip_the_grid_reads():
    unavailable = Observation.unavailable(100, 'Panel flags are unreadable')
    with (
        patch('inventory_tracking.tracking.shop_panel.observe_panels', return_value=unavailable),
        patch('inventory_tracking.tracking.shop_panel.os.open') as opened,
    ):
        observation = observe_shop_panel(12, IMAGES, snapshot())
    assert observation.status == ObservationStatus.UNAVAILABLE
    assert observation.reason == 'Panel flags are unreadable'
    opened.assert_not_called()


def test_smiths_are_the_five_repair_vendors():
    from inventory_tracking.shop.capture import VENDORS

    assert {VENDORS[i] for i in SMITHS} == {'Charsi', 'Fara', 'Hratli', 'Halbu', 'Larzuk'}
