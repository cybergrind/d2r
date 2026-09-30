"""The actual Holy Bolt jewel's four affixes establish independent stat bounds."""

from copy import deepcopy

import pytest

from pricing.knowledge.builds import decode_planner
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import read


@pytest.fixture(scope='module')
def evidence():
    planner = decode_planner(read('pricing/raw/mr/planners/s10106pr.json'))
    return planner['items']['55'], {
        'mp': read('third-parties/d2data/json/magicprefix.json'),
        'ms': read('third-parties/d2data/json/magicsuffix.json'),
    }


def test_actual_rare_jewel_bounds_are_summed_without_requiring_perfect_rolls(evidence):
    from pricing.knowledge.assessment.maintenance.planner_jewel_affixes import reviewed_bounds

    jewel, tables = evidence
    assert reviewed_bounds(jewel, tables) == {
        'item_fastergethitrate': (7, 7),
        'fireresist': (21, 40),
        'lightresist': (5, 10),
        'coldresist': (5, 10),
        'poisonresist': (5, 10),
        'item_damagetomana': (7, 12),
    }


@pytest.mark.parametrize(
    'change',
    [
        'changed-total',
        'outside-roll',
        'missing-affix',
        'unsupported-affix',
        'magic-only',
        'wrong-base',
        'wrong-quality',
    ],
)
def test_changed_or_unreviewed_jewel_data_is_rejected(evidence, change):
    from pricing.knowledge.assessment.maintenance.planner_jewel_affixes import reviewed_bounds

    jewel, tables = deepcopy(evidence)
    if change == 'changed-total':
        jewel['stats']['fireresist'] = 41
    elif change == 'outside-roll':
        jewel['mods']['mp336'] = [11]
    elif change == 'missing-affix':
        jewel['mods'].pop('mp200')
    elif change == 'unsupported-affix':
        tables['mp']['200']['mod1code'] = 'unsupported'
    elif change == 'magic-only':
        tables['mp']['200']['rare'] = 0
    elif change == 'wrong-base':
        jewel['base'] = 'cjw'
    elif change == 'wrong-quality':
        jewel['quality'] = 6
    with pytest.raises(ValueError, match=r'jewel|affix'):
        reviewed_bounds(jewel, tables)


def test_lower_legal_rolls_preserve_affix_combination(evidence):
    from pricing.knowledge.assessment.maintenance.planner_jewel_affixes import reviewed_bounds

    jewel, tables = deepcopy(evidence)
    jewel['mods'].update(mp336=[5], mp376=[16], mp200=[7])
    jewel['stats'].update(fireresist=21, lightresist=5, coldresist=5, poisonresist=5, item_damagetomana=7)
    bounds = reviewed_bounds(jewel, tables)
    assert bounds['fireresist'] == (21, 40)
    assert bounds['item_damagetomana'] == (7, 12)


def test_missing_secondary_resistance_is_not_a_complete_shimmering_roll(evidence):
    from pricing.knowledge.assessment.maintenance.planner_jewel_affixes import reviewed_bounds

    jewel, tables = deepcopy(evidence)
    jewel['stats'].pop('poisonresist')
    with pytest.raises(ValueError, match='totals'):
        reviewed_bounds(jewel, tables)
