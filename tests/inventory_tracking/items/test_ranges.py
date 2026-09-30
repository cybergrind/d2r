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


@pytest.mark.parametrize(
    ('stat', 'layer', 'suffix'), [(107, 77, 'Terror (Necromancer Only)'), (83, 2, 'Necromancer Skill Levels')]
)
@pytest.mark.parametrize(('value', 'quality'), [(1, 'low'), (2, 'normal'), (3, 'perfect'), (4, None)])
def test_parameterized_skill_rows_preserve_templates_for_verified_ranges(stat, layer, suffix, value, quality):
    from inventory_tracking.items.metadata import decode_stats

    decoded, _, unresolved = decode_stats([{'id': stat, 'layer': layer, 'raw': value}])
    assert not unresolved
    annotate_roll_ranges(
        decoded,
        {
            'source': {'path': 'reviewed-skill-definition'},
            'roll_ranges': {f'{stat}:{layer}': {'layer': layer, 'min': 1, 'max': 3}},
        },
    )
    row = decoded[0]
    assert row['text'] == f'+{value}' + (' (1-3)' if quality else '') + f' to {suffix}'
    assert row.get('roll_quality') == quality
    assert row['value'] == value
    # A range for another skill/class must never annotate this row.
    other, _, _ = decode_stats([{'id': stat, 'layer': layer, 'raw': value}])
    annotate_roll_ranges(
        other,
        {
            'source': {},
            'roll_ranges': {f'{stat}:{layer + 1}': {'layer': layer + 1, 'min': 1, 'max': 3}},
        },
    )
    assert 'roll_range' not in other[0]
