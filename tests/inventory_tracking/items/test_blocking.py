"""Native shield blocking includes the base; non-shield blocking is a bonus."""

import pytest

from inventory_tracking.items.metadata import decode_stats, metadata
from inventory_tracking.items.ranges import annotate_roll_ranges


@pytest.mark.parametrize(
    ('base_name', 'raw'),
    [
        ('Monarch', 22),
        ('Monarch', 42),
        ('Sacred Rondache', 28),
        ('Buckler', 0),
        ('Preserved Head', 3),
        ('Old Book', 3),
    ],
)
def test_shield_block_is_not_labeled_as_added_blocking(base_name, raw):
    base = next(b for b in metadata()['bases'].values() if b['name'] == base_name)
    decoded, _, unresolved = decode_stats([{'id': 20, 'layer': 0, 'raw': raw}], base=base)
    assert not unresolved
    row = decoded[0]
    assert row['text'] == f'Shield blocking (base + bonuses): {raw}%'
    assert row['value'] == row['memory_stat']['raw'] == raw
    assert row['origin'] == 'shield_block_total'
    # An overlapping total does not establish a rolled affix bonus.
    annotate_roll_ranges(decoded, {'roll_ranges': {'20': {'min': 10, 'max': 30}}, 'source': {}})
    assert 'roll_range' not in row


def test_guardian_angel_block_bonus_remains_a_bonus():
    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Templar Coat')
    decoded, _, _ = decode_stats([{'id': 20, 'layer': 0, 'raw': 20}], base=base)
    assert decoded[0]['text'] == '20% Increased Chance of Blocking'
    assert decoded[0]['value'] == 20


def test_modifier_without_base_context_keeps_its_scalar_semantics():
    decoded, _, _ = decode_stats([{'id': 20, 'layer': 0, 'raw': 7}])
    assert decoded[0]['text'] == '7% Increased Chance of Blocking'
