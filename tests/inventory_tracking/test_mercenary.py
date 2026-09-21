"""Only the player's living hireling may supply healing decisions."""

import pytest

from inventory_tracking.mercenary import select_mercenary


def monster(*, owner=7, life=32768, mode=1):
    data = [0] * 64
    data[0x54 // 4] = owner
    return {
        'unit_id': 99,
        'txt_id': 338,
        'mode': mode,
        'details': {
            'monster_data_u32': data,
            'full_stats': [{'layer': 0, 'id': 6, 'raw': life}, {'layer': 0, 'id': 7, 'raw': 2090 * 256}],
        },
    }


def test_full_health_matches_2090_and_wrong_owner_is_rejected():
    assert select_mercenary([monster()], 7).maximum_raw == 2090 * 256
    assert select_mercenary([monster()], 7).current_raw == 2090 * 256
    assert select_mercenary([monster(owner=8)], 7) is None
    assert select_mercenary([monster(), monster()], 7) is None


@pytest.mark.parametrize(('life', 'mode'), [(0, 1), (32768, 0), (32768, 12)])
def test_dead_or_dying_never_alive(life, mode):
    assert not select_mercenary([monster(life=life, mode=mode)], 7).alive


def test_half_health_uses_normalized_client_life():
    assert select_mercenary([monster(life=16384)], 7).current_raw == 1045 * 256
