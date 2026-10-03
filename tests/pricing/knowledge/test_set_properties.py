from copy import deepcopy

import pytest

from pricing.knowledge.set_properties import standalone_set_record


def test_extra_projection_preserves_source_and_does_not_duplicate_on_reuse():
    source = {
        'prop1': 'ac',
        'min1': 30,
        'max1': 30,
        'par2': 'stale',
        'aprop3a': 'extra-pois',
        'amin3a': 25,
        'amax3a': 25,
    }
    before = deepcopy(source)
    projected = standalone_set_record(source)
    assert source == before
    assert projected['prop1'] == 'ac'
    assert (projected['prop2'], projected['min2'], projected['max2']) == ('extra-pois', 25, 25)
    assert 'par2' not in projected
    assert standalone_set_record(projected) == projected


@pytest.mark.parametrize('mode', [1, 2, None, False, 0.0, '0', 3])
def test_unknown_or_conditional_modes_never_promote_extra_modifiers(mode):
    record = {'add func': mode, 'aprop1a': 'ac', 'amin1a': 160, 'amax1a': 160}
    assert standalone_set_record(record) == record


def test_compiler_capacity_exhaustion_is_explicit_instead_of_losing_a_property():
    record = {f'prop{i}': 'ac' for i in range(1, 13)}
    record['aprop1a'] = 'hp'
    with pytest.raises(ValueError, match='capacity'):
        standalone_set_record(record)
