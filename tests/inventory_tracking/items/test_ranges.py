import pytest

from inventory_tracking.items.ranges import annotate_roll_ranges


@pytest.mark.parametrize(
    ('value', 'better', 'quality'),
    [
        (100, 'higher', 'perfect'),
        (20, 'higher', 'low'),
        (21, 'higher', 'normal'),
        (0, 'lower', 'perfect'),
        (80, 'lower', 'low'),
        (79, 'lower', 'normal'),
    ],
)
def test_roll_quality_respects_bounds_and_direction(value, better, quality):
    rows = [
        {
            'status': 'decoded',
            'memory_stat': {'id': 105, 'layer': 0, 'raw': value},
            'value': value,
            'label': '+{{value}}%',
            'text': f'+{value}%',
        }
    ]
    identity = {'source': {'path': 'fixture'}, 'roll_ranges': {'105': {'min': 0, 'max': 100, 'better': better}}}
    annotate_roll_ranges(rows, identity)
    assert rows[0]['roll_quality'] == quality
    assert rows[0]['value'] == value


@pytest.mark.parametrize(('low', 'high', 'value'), [(25, 35, 36), (25, 35, 24), (35, 35, 35)])
def test_outside_definition_and_fixed_values_are_not_ranked(low, high, value):
    rows = [
        {
            'status': 'decoded',
            'memory_stat': {'id': 105, 'layer': 0},
            'value': value,
            'label': '+{{value}}%',
            'text': f'+{value}%',
        }
    ]
    annotate_roll_ranges(rows, {'source': {}, 'roll_ranges': {'105': {'min': low, 'max': high}}})
    assert 'roll_quality' not in rows[0]
    assert rows[0]['text'] == f'+{value}%'
