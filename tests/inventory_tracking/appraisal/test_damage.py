from copy import deepcopy

import pytest

from inventory_tracking.appraisal.damage import display_damage
from inventory_tracking.items.metadata import decode_stats


def test_hellplague_damage_pairs_preserve_native_rows():
    rows, _, _ = decode_stats(
        [{'id': stat, 'layer': 0, 'raw': value} for stat, value in [(21, 5), (22, 32), (48, 25), (49, 75)]]
    )
    original = deepcopy(rows)
    assert [r['text'] for r in display_damage(rows)] == ['One-Hand Damage: 5-32', 'Adds 25-75 Fire Damage']
    assert rows == original
    assert display_damage(rows[:1]) == rows[:1]
    assert display_damage(rows[:2] + rows[:1]) == rows[:2] + rows[:1]


def test_damage_roll_ranges_and_tiers_survive_pairing():
    rows, _, _ = decode_stats([{'id': stat, 'layer': 0, 'raw': value} for stat, value in [(48, 25), (49, 75)]])
    rows[0].update(roll_range={'min': 20, 'max': 25}, roll_tier=1, roll_quality='perfect')
    rows[1].update(roll_range={'min': 60, 'max': 80}, roll_tier=2, roll_quality='normal')
    paired = display_damage(rows)[0]
    assert paired['text'] == 'Adds 25 (20-25) [T1]-75 (60-80) [T2] Fire Damage'
    assert 'roll_quality' not in paired


@pytest.mark.parametrize(('minimum', 'maximum', 'label'), [(21, 22, 'One-Hand'), (23, 24, 'Two-Hand')])
def test_per_level_weapon_maximum_matches_tooltip_without_mutating_stats(minimum, maximum, label):
    rows, _, _ = decode_stats(
        [{'id': stat, 'layer': 0, 'raw': value} for stat, value in [(minimum, 22), (maximum, 46), (218, 4)]],
        viewer_level=91,
    )
    original = deepcopy(rows)
    displayed = display_damage(rows)
    assert displayed[0]['text'] == f'{label} Damage: 22-91'
    assert displayed[1]['text'] == '+45 to Maximum Damage (Based on Character Level)'
    assert rows == original
    assert display_damage(displayed) == displayed


def test_unverified_or_duplicate_per_level_bonus_is_not_added_to_damage():
    rows, _, _ = decode_stats(
        [{'id': stat, 'layer': 0, 'raw': value} for stat, value in [(21, 22), (22, 46), (218, 4)]],
        viewer_level=91,
    )
    bad = deepcopy(rows)
    bad[2]['value'] = 90
    assert display_damage(bad)[0]['text'] == 'One-Hand Damage: 22-46'
    assert display_damage([*rows, rows[2]])[0]['text'] == 'One-Hand Damage: 22-46'
