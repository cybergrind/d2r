from copy import deepcopy

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.maintenance.socket_scalars import compile_scalars


@pytest.mark.parametrize('stat', ['0', '60'])
@pytest.mark.parametrize('field', ['shift', 'op', 'encode', 'parameter_bits'])
def test_intrinsic_strength_and_leech_require_unscaled_unparameterized_native_stats(stat, field):
    stats = {**metadata()['stats']}
    stats[stat] = {**stats[stat], field: 1}
    with pytest.raises(ValueError, match='not an unscaled scalar'):
        compile_scalars({}, {}, stats, {})


@pytest.mark.parametrize('change', ['unknown-function', 'missing-stat', 'variable-roll', 'parameter'])
def test_unreviewed_fixed_scalar_inputs_cannot_compile_as_zero(change):
    gem = {'helmMod1Code': 'dex', 'helmMod1Min': 10, 'helmMod1Max': 10}
    prop = {'func1': 1, 'stat1': 'dexterity'}
    if change == 'unknown-function':
        prop['func1'] = 999
    elif change == 'missing-stat':
        prop.pop('stat1')
    elif change == 'variable-roll':
        gem['helmMod1Max'] = 11
    else:
        gem['helmMod1Param'] = 1
    with pytest.raises(ValueError, match=r'Unreviewed socket property|Socket scalar is not fixed'):
        compile_scalars({'test': gem}, {'dex': prop}, metadata()['stats'], {})


@pytest.mark.parametrize('change', ['operator', 'function', 'variable', 'parameter'])
def test_enhanced_defense_exception_cannot_admit_other_stat_operations(change):
    stats = deepcopy(metadata()['stats'])
    gem = {'helmMod1Code': 'ac%', 'helmMod1Min': 30, 'helmMod1Max': 30}
    prop = {'func1': 2, 'stat1': 'item_armor_percent'}
    if change == 'operator':
        stats['16']['op'] = 0
    elif change == 'function':
        prop['func1'] = 1
    elif change == 'variable':
        gem['helmMod1Max'] = 31
    else:
        gem['helmMod1Param'] = 1
    with pytest.raises(ValueError, match=r'not an unscaled scalar|not fixed and direct'):
        compile_scalars({'test': gem}, {'ac%': prop}, stats, {})
