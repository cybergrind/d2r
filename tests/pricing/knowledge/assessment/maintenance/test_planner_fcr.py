"""Only native-checked contributions in the active weapon set count toward FCR."""

from copy import deepcopy

import pytest

from pricing.knowledge.builds import decode_planner
from tests.pricing.knowledge.assessment.maintenance.test_swap_planner_links import read


PATHS = {
    'game': 'pricing/raw/mr/planners/game-data.json',
    'metadata': 'inventory_tracking/items/data/item_metadata.json',
    'uniques': 'third-parties/d2data/json/uniqueitems.json',
    'runes': 'third-parties/d2data/json/runes.json',
    'armor': 'third-parties/d2data/json/armor.json',
    'weapons': 'third-parties/d2data/json/weapons.json',
    'types': 'third-parties/d2data/json/itemtypes.json',
    'properties': 'third-parties/d2data/json/properties.json',
    'stats': 'third-parties/d2data/json/itemstatcost.json',
    'misc': 'third-parties/d2data/json/misc.json',
    'gems': 'third-parties/d2data/json/gems.json',
}


def example(index=1):
    planner = deepcopy(decode_planner(read('pricing/raw/mr/planners/f80206a8.json')))
    return planner['profiles'][index], planner['items'], {key: read(path) for key, path in PATHS.items()}


def calculate(profile, items, tables):
    from pricing.knowledge.assessment.maintenance.planner_fcr import active_fcr_evidence

    return active_fcr_evidence(profile, items, tables)


@pytest.mark.parametrize('index', [1, 2])
def test_hammer_loadouts_have_125_native_checked_active_fcr(index):
    profile, items, tables = example(index)
    result = calculate(profile, items, tables)
    assert result['minimum_fcr'] == 125
    assert len(result['contributors']) == 5
    assert 'larm2' not in {r['slot'] for r in result['contributors']}
    assert 'rarm2' not in {r['slot'] for r in result['contributors']}
    names = {r['name'] for r in result['contributors']}
    assert {'Spirit', 'Void', 'Sling', 'Arachnid Mesh'} <= names
    if index == 1:
        assert "Hellwarden's Will" in names
    else:
        assert 'Storm Collar' in names


def test_swap_cannot_fill_a_main_set_fcr_shortfall():
    profile, items, tables = example()
    # The two sets share an item definition in this planner; isolate swap copy.
    profile['items']['larm2'] = 'swap-shield'
    items['swap-shield'] = deepcopy(items[str(profile['items']['larm'])])
    items[str(profile['items']['larm'])]['stats']['item_fastercastrate'] = 25
    result = calculate(profile, items, tables)
    assert result['minimum_fcr'] == 115


@pytest.mark.parametrize(
    'change',
    [
        'double-count',
        'wrong-runes',
        'wrong-base',
        'unique-base',
        'unique-value',
        'crafted-affix',
        'crafted-roll',
        'bool-value',
        'negative-value',
        'missing-item',
    ],
)
def test_fcr_rejects_unverified_or_incompatible_contributions(change):
    profile, items, tables = example(2 if change.startswith('crafted') else 1)
    if change == 'double-count':
        # Unknown slot aliases must not be treated as another active slot.
        profile['items']['larm-extra'] = profile['items']['larm']
    elif change == 'wrong-runes':
        items[str(profile['items']['rarm'])]['socketedItems'].reverse()
    elif change == 'wrong-base':
        items[str(profile['items']['rarm'])]['base'] = items[str(profile['items']['larm'])]['base']
    elif change == 'unique-base':
        items[str(profile['items']['lrin'])]['base'] = items[str(profile['items']['neck'])]['base']
    elif change == 'unique-value':
        items[str(profile['items']['lrin'])]['stats']['item_fastercastrate'] = 50
    elif change == 'crafted-affix':
        items[str(profile['items']['neck'])]['mods'].pop('ms174')
    elif change == 'crafted-roll':
        items[str(profile['items']['neck'])]['crafted']['crf088'][-1] = 20
    elif change == 'bool-value':
        items[str(profile['items']['larm'])]['stats']['item_fastercastrate'] = True
    elif change == 'negative-value':
        items[str(profile['items']['feet'])]['stats']['item_fastercastrate'] = -10
    else:
        items.pop(str(profile['items']['belt']))
    with pytest.raises(ValueError, match='FCR'):
        calculate(profile, items, tables)


@pytest.mark.parametrize('change', ['unknown-property', 'stale-identity', 'wrong-stat'])
def test_missing_native_semantics_do_not_become_zero_fcr(change):
    profile, items, original = example(2 if change == 'unknown-property' else 1)
    tables = deepcopy(original)
    if change == 'unknown-property':
        tables['game']['magicSuffix']['ms174']['mod1code'] = 'unmapped_cast'
    elif change == 'stale-identity':
        tables['metadata']['identities']['unique']['415']['game_definition']['min2'] = 50
    else:
        tables['stats']['item_fastercastrate']['*ID'] = 999
    with pytest.raises(ValueError, match='FCR'):
        calculate(profile, items, tables)


def test_unknown_rotw_planner_ids_are_resolved_by_current_native_recipe_and_unique_rows():
    profile, items, tables = example()
    assert items[str(profile['items']['rarm'])]['unique'] not in tables['game']['runes']
    assert items[str(profile['items']['head'])]['unique'] not in tables['game']['uniqueItems']
    result = calculate(profile, items, tables)
    assert {'Void', "Hellwarden's Will"} <= {row['name'] for row in result['contributors']}


def test_one_item_reference_cannot_contribute_from_two_active_slots():
    profile, items, tables = example()
    profile['items']['rrin'] = profile['items']['lrin']
    with pytest.raises(ValueError, match=r'FCR.*duplicate'):
        calculate(profile, items, tables)
