import pytest

from pricing.knowledge.market_mechanics import apply_mechanics


@pytest.mark.parametrize(
    ('name', 'payload'), [('Vampire Gaze', 'Um Rune'), ('Stealskull', 'Perfect Topaz'), ('Shaftstop', 'Ber Rune')]
)
def test_explicit_filler_proves_one_socket_only_for_named_single_socket_mechanics(name, payload):
    row = {'name': name, 'category': 'uniques', 'properties': {'934': payload}}
    apply_mechanics(row)
    assert row['sockets'] == 1
    assert row['socket_contents'] == 'filled'
    assert row['facet_basis']['sockets']['kind'] == 'named_single_socket_payload'
    assert 'ethereal' not in row
    assert 'base_code' not in row  # original versus upgraded remains unknown


@pytest.mark.parametrize(
    ('name', 'payload'),
    [
        ('Tomb Reaver', 'Um Rune'),
        ('Crown of Ages', 'Ber Rune'),
        ('Unknown Unique', 'Um Rune'),
        ('Vampire Gaze', 'Jewel'),
        ('Vampire Gaze', ''),
        ('Vampire Gaze', None),
        ('Vampire Gaze', 'None'),
        ('Vampire Gaze', 'Um Rune, Shael Rune'),
    ],
)
def test_missing_ambiguous_or_intrinsic_socket_payload_never_invents_count(name, payload):
    row = {'name': name, 'category': 'uniques', 'properties': {'934': payload}}
    apply_mechanics(row)
    assert 'sockets' not in row


def test_explicit_conflicting_count_is_rejected_not_replaced():
    row = {'name': 'Vampire Gaze', 'category': 'uniques', 'properties': {'934': 'Um Rune', '402': 2}, 'sockets': 2}
    apply_mechanics(row)
    assert row['sockets'] == 2
    assert row['mechanics_conflicts']
