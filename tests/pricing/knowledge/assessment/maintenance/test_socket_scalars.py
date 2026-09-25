import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.maintenance.socket_scalars import compile_scalars


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
