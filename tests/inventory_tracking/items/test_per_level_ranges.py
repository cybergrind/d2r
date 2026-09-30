"""Native recipe evidence, coefficient rolls, and character-level display bounds."""

from copy import deepcopy

import pytest

from inventory_tracking.items.identity import resolve_identity
from inventory_tracking.items.metadata import decode_stats, metadata
from inventory_tracking.items.ranges import annotate_roll_ranges
from tests.inventory_tracking.items.test_runeword_recipes import capture


@pytest.fixture
def fortitude():
    recipe = next(r for r in metadata()['identities']['runeword'].values() if r['name'] == 'Fortitude')
    details, arrays, base = capture(recipe, 'Sacred Armor')
    identity = resolve_identity(details, arrays, base)
    assert identity['method'] == 'captured_recipe'
    return deepcopy(identity)


def life(raw=2048, level=80):
    rows, _, _ = decode_stats([{'id': 216, 'layer': 0, 'raw': raw}], viewer_level=level)
    return rows[0]


@pytest.mark.parametrize(
    ('raw', 'level', 'value', 'bounds', 'quality'),
    [
        (2048, 80, 80, (80, 120), 'low'),
        (2304, 80, 90, (80, 120), 'normal'),
        (3072, 80, 120, (80, 120), 'perfect'),
        (2048, 1, 1, (1, 1), 'low'),
        (3072, 1, 1, (1, 1), 'perfect'),
        (3072, 99, 148, (99, 148), 'perfect'),
    ],
)
def test_fortitude_native_coefficient_range(fortitude, raw, level, value, bounds, quality):
    row = life(raw, level)
    annotate_roll_ranges([row], fortitude)
    assert row['value'] == value
    assert row['text'] == f'+{value} ({bounds[0]}-{bounds[1]}) to Life (Based on Character Level)'
    assert row['roll_quality'] == quality
    assert row['roll_range']['min'] == bounds[0]
    assert row['roll_range']['max'] == bounds[1]
    assert row['roll_range']['source'] == fortitude['source']
    before = deepcopy(row)
    annotate_roll_ranges([row], fortitude)
    assert row == before


@pytest.mark.parametrize(
    'change',
    [
        'below',
        'above',
        'off-step',
        'unknown-level',
        'wrong-denominator',
        'wrong-value',
        'wrong-layer',
        'duplicate',
        'fixed',
    ],
)
def test_inconsistent_or_unrankable_per_level_evidence_is_not_annotated(fortitude, change):
    row = life({'below': 1792, 'above': 3328, 'off-step': 2049}.get(change, 2048))
    if change == 'unknown-level':
        row.pop('viewer_level')
    if change == 'wrong-denominator':
        row['per_level']['denominator'] = 8
    if change == 'wrong-value':
        row['value'] = 81
    if change == 'wrong-layer':
        row['memory_stat']['layer'] = 1
    if change == 'duplicate':
        fortitude['variable_per_level_effects'] *= 2
    if change == 'fixed':
        fortitude['variable_per_level_effects'][0]['maximum_raw'] = 2048
    before = deepcopy(row)
    annotate_roll_ranges([row], fortitude)
    assert row == before
