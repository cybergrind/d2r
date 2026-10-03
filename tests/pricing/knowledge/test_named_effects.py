import json
from pathlib import Path

from pricing.knowledge.named_effects import fixed_elemental_effects


def test_compound_cold_preserves_fixed_endpoints_and_native_frame_duration():
    root = Path(__file__).resolve().parents[3]
    properties = {
        r['code']: r
        for r in json.loads((root / 'third-parties/d2data/json/properties.json').read_text()).values()
        if r.get('code')
    }
    record = {'prop2': 'dmg-cold', 'min2': 15, 'max2': 45, 'par2': 100}
    assert fixed_elemental_effects(record, properties) == [
        {'kind': 'cold', 'slot': 2, 'minimum_damage': 15, 'maximum_damage': 45, 'duration_frames': 100}
    ]
    changed = {**properties, 'dmg-cold': {**properties['dmg-cold'], 'func3': 1}}
    assert fixed_elemental_effects(record, changed) == []
    assert fixed_elemental_effects({**record, 'par2': None}, properties) == []
    # Separate cold-min/max/len properties have independent variable rolls.
    variable = {
        'prop1': 'cold-min',
        'min1': 1,
        'max1': 2,
        'prop2': 'cold-max',
        'min2': 3,
        'max2': 5,
        'prop3': 'cold-len',
        'min3': 50,
        'max3': 250,
    }
    assert fixed_elemental_effects(variable, properties) == []


def test_named_poison_accepts_one_fixed_source_but_not_variable_or_mixed_sources():
    from pricing.knowledge.named_effects import fixed_poison_effect

    root = Path(__file__).resolve().parents[3]
    properties = {
        r['code']: r
        for r in json.loads((root / 'third-parties/d2data/json/properties.json').read_text()).values()
        if r.get('code')
    }
    compound = {'prop1': 'dmg-pois', 'min1': 102, 'max1': 102, 'par1': 100}
    assert fixed_poison_effect(compound, properties) == {
        'minimum_rate_raw': 102,
        'maximum_rate_raw': 102,
        'duration_frames': 100,
        'source_count': 1,
    }
    scalar = {
        'prop1': 'pois-min',
        'min1': 48,
        'max1': 48,
        'prop2': 'pois-max',
        'min2': 96,
        'max2': 96,
        'prop3': 'pois-len',
        'min3': 150,
        'max3': 150,
    }
    assert fixed_poison_effect(scalar, properties) == {
        'minimum_rate_raw': 48,
        'maximum_rate_raw': 96,
        'duration_frames': 150,
        'source_count': 1,
    }
    assert fixed_poison_effect({**scalar, 'max1': 49}, properties) is None
    assert fixed_poison_effect({**scalar, 'prop4': 'dmg-pois', 'min4': 1, 'max4': 1, 'par4': 25}, properties) is None
    changed = {**properties, 'pois-max': {**properties['pois-max'], 'func1': 8}}
    assert fixed_poison_effect(scalar, changed) is None


def test_recipe_elemental_fields_do_not_read_named_item_namespace():
    root = Path(__file__).resolve().parents[3]
    properties = {
        r['code']: r
        for r in json.loads((root / 'third-parties/d2data/json/properties.json').read_text()).values()
        if r.get('code')
    }
    record = {'T1Code1': 'dmg-fire', 'T1Min1': 120, 'T1Max1': 120, 'prop1': 'dmg-fire', 'min1': 1, 'max1': 2}
    assert fixed_elemental_effects(record, properties, runeword=True) == [
        {'kind': 'fire', 'slot': 1, 'minimum_damage': 120, 'maximum_damage': 120}
    ]


def test_hellrack_compound_elemental_definition_preserves_all_three_damage_types():
    root = Path(__file__).resolve().parents[3]
    properties = json.loads((root / 'third-parties/d2data/json/properties.json').read_text())
    uniques = json.loads((root / 'third-parties/d2data/json/uniqueitems.json').read_text())
    record = next(row for row in uniques.values() if row.get('index') == 'Hellrack')
    assert fixed_elemental_effects(record, properties) == [
        {'kind': 'fire', 'slot': 2, 'minimum_damage': 63, 'maximum_damage': 324},
        {'kind': 'lightning', 'slot': 2, 'minimum_damage': 63, 'maximum_damage': 324},
        {'kind': 'cold', 'slot': 2, 'minimum_damage': 63, 'maximum_damage': 324, 'duration_frames': 33},
    ]
    for position in range(1, 8):
        altered = {**properties, 'dmg-elem': {**properties['dmg-elem'], f'func{position}': 0}}
        assert fixed_elemental_effects(record, altered) == []
    without_duration = {**record, 'par2': None}
    assert {effect['kind'] for effect in fixed_elemental_effects(without_duration, properties)} == {'fire', 'lightning'}


def test_compound_runeword_damage_keeps_missing_duration_explicit():
    from pricing.knowledge.definitions import build_definitions

    root = Path(__file__).resolve().parents[3]
    rows = build_definitions(root)['rows']
    for name, low, high, slot in [('Famine', 50, 200, 6), ('Harmony', 55, 160, 2)]:
        definition = next(row for row in rows if row.get('rarity') == 'runeword' and row['name'] == name)
        assert definition['fixed_elemental_effects'] == [
            {'kind': 'fire', 'slot': slot, 'minimum_damage': low, 'maximum_damage': high},
            {'kind': 'lightning', 'slot': slot, 'minimum_damage': low, 'maximum_damage': high},
            {'kind': 'cold', 'slot': slot, 'minimum_damage': low, 'maximum_damage': high, 'duration_frames': None},
        ]
