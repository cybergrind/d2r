import json
from typing import Any

from pricing.knowledge.definitions import build_definitions, scalar_ranges
from pricing.knowledge.index import build_index, compact_result, lookup


def test_only_unambiguous_scalar_properties_have_numeric_ranges():
    properties = {'cast3': {'func1': 8, 'stat1': 'fcr'}, 'charged': {'func1': 19}, 'dmg%': {'func1': 7}}
    record = {
        'prop1': 'cast3',
        'min1': 25,
        'max1': 35,
        'prop2': 'charged',
        'min2': 12,
        'max2': 60,
        'prop3': 'dmg%',
        'min3': 80,
        'max3': 150,
    }
    ranges = scalar_ranges(record, properties, {'fcr': 105})
    assert set(ranges) == {'105', '17', '18'}
    assert ranges['105']['min'] == 25
    record.update(prop4='cast3', min4=1, max4=2)
    assert '105' not in scalar_ranges(record, properties, {'fcr': 105})
    record['par3'] = 'unverified parameter'
    assert '17' not in scalar_ranges(record, properties, {'fcr': 105})


def test_runeword_definitions_are_built_and_searchable_in_offline_kb(tmp_path):
    inputs = {
        'third-parties/d2data/json/allstrings-eng.json': {},
        'third-parties/d2data/json/qualityitems.json': {},
        'third-parties/d2data/json/skills.json': {},
        'third-parties/d2data/json/automagic.json': {},
        'third-parties/d2data/json/rareprefix.json': {},
        'third-parties/d2data/json/raresuffix.json': {},
        'third-parties/d2data/json/sets.json': {},
        'third-parties/d2data/json/magicprefix.json': {
            '0': {},
            '2': {'Name': 'Stout', 'itype1': 'scha', 'mod1code': 'hp', 'mod1min': 1, 'mod1max': 2},
        },
        'third-parties/d2data/json/magicsuffix.json': {
            '0': {},
            '2': {'Name': 'of Vita', 'itype1': 'scha', 'mod1code': 'hp', 'mod1min': 16, 'mod1max': 20},
        },
        'third-parties/d2data/json/gems.json': {},
        'third-parties/d2data/json/properties.json': {
            'cast3': {'func1': 8, 'stat1': 'fcr'},
            'hp': {'func1': 1, 'stat1': 'life'},
        },
        'third-parties/d2data/json/itemstatcost.json': {'fcr': {'*ID': 105}, 'life': {'*ID': 7}},
        'third-parties/d2data/json/cubemain.json': {},
        'pricing/raw/mr/planners/game-strings.json': [],
        'pricing/raw/d2data/weapons.json': {},
        'pricing/raw/d2data/armor.json': {'test': {'name': 'Shield', 'type': 'shie'}},
        'pricing/raw/d2data/misc.json': {'test-charm': {'name': 'Test Charm', 'type': 'scha'}},
        'pricing/raw/d2data/itemtypes.json': {'shie': {'Equiv1': 'shld'}},
        'pricing/raw/d2data/setitems.json': {},
        'pricing/raw/d2data/uniqueitems.json': {},
        'pricing/raw/d2data/runes.json': {
            'Spirit': {
                'complete': 1,
                'itype1': 'shld',
                'Rune1': 'test-rune',
                'T1Code1': 'cast3',
                'T1Min1': 25,
                'T1Max1': 35,
            }
        },
    }
    for name, value in inputs.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
    mapping = tmp_path / 'third-parties/d2go/pkg/data/item/runeword.go'
    mapping.parent.mkdir(parents=True)
    mapping.write_text('RunewordSpirit RunewordName = "Spirit"\n20635: RunewordSpirit,\n')
    definitions = build_definitions(tmp_path)
    assert definitions['rows'][0]['table_id'] == 20635
    assert definitions['rows'][0]['base_codes'] == ['test']
    charm_rows = {r['affix_table']: r for r in definitions['rows'] if 'affix_table' in r}
    assert charm_rows['suffix']['table_id'] == 2
    assert charm_rows['prefix']['table_id'] == 4
    assert charm_rows['suffix']['roll_ranges']['7']['max'] == 20
    portable = tmp_path / 'definitions.json'
    portable.write_text(json.dumps(definitions))
    database = tmp_path / 'kb.sqlite3'
    build_index([portable], database)
    result = compact_result(lookup(database, 'Spirit', rarity='runeword'))
    assert isinstance(result, dict)
    row = result['evidence']['item_definition'][0]
    assert row['roll_ranges']['105']['max'] == 35
    assert row['source']['source_date'] == '2026-09-23'


def test_charm_quality_pool_excludes_disabled_tiers_and_other_sizes():
    from pricing.knowledge.definitions import add_charm_quality_ranges

    def entry(base, low, high, spawnable=True) -> dict[str, Any]:
        return {
            'affix_table': 'suffix',
            'spawnable': spawnable,
            'game_definition': {'frequency': 1},
            'base_codes': [base],
            'roll_ranges': {'7': {'min': low, 'max': high, 'property': 'hp'}},
        }

    rows = [entry('large', 16, 20), entry('large', 31, 35), entry('large', 90, 100, False), entry('grand', 41, 45)]
    add_charm_quality_ranges(rows)
    assert rows[0]['roll_tiers']['large']['7'] == [{'min': 31, 'max': 35}, {'min': 16, 'max': 20}]
    assert rows[0]['quality_ranges']['large']['7'] == {'min': 16, 'max': 35}
    assert rows[-1]['quality_ranges']['grand']['7'] == {'min': 41, 'max': 45}


def test_skill_tab_ranges_keep_native_class_tree_layers_separate():
    properties = {'skilltab': {'func1': 10}}
    record = {
        'prop1': 'skilltab',
        'par1': 5,
        'min1': 1,
        'max1': 2,
        'prop2': 'skilltab',
        'par2': 3,
        'min2': 1,
        'max2': 3,
    }
    ranges = scalar_ranges(record, properties, {})
    assert ranges['188:10']['max'] == 2  # Sorceress cold: class1/tree2.
    assert ranges['188:8']['max'] == 3  # Sorceress fire: class1/tree0.


def test_skill_ranges_require_known_parameter_and_preserve_layer():
    properties = {'aura': {'func1': 22, 'stat1': 'item_aura'}}
    record = {'prop1': 'aura', 'par1': 'Meditation', 'min1': 12, 'max1': 17}
    ranges = scalar_ranges(record, properties, {'item_aura': 151}, skill_ids={'Meditation': 120})
    assert ranges['151:120']['min'] == 12
    assert ranges['151:120']['max'] == 17
    assert not scalar_ranges(record, properties, {'item_aura': 151})


def test_class_specific_skill_ranges_preserve_verified_native_parameter():
    properties = {'skill': {'func1': 22, 'stat1': 'item_singleskill'}}
    record = {'prop1': 'skill', 'par1': 'Apocalypse', 'min1': 3, 'max1': 5}
    skills = {'Apocalypse': 401}
    expected = {'stat_id': 107, 'layer': 401, 'min': 3, 'max': 5, 'property': 'skill', 'better': 'higher'}
    assert scalar_ranges(record, properties, {'item_singleskill': 107}, skill_ids=skills) == {'107:401': expected}
    assert scalar_ranges({**record, 'par1': 401}, properties, {'item_singleskill': 107}, skill_ids=skills) == {
        '107:401': expected
    }
    assert (
        scalar_ranges({**record, 'par1': 'Unverified'}, properties, {'item_singleskill': 107}, skill_ids=skills) == {}
    )


def test_fire_skill_range_uses_property_element_layer():
    properties = {'fireskill': {'func1': 21, 'stat1': 'item_elemskill', 'val1': 1}}
    record = {'prop1': 'fireskill', 'min1': 2, 'max1': 2}
    assert scalar_ranges(record, properties, {'item_elemskill': 126}) == {
        '126:1': {'stat_id': 126, 'layer': 1, 'min': 2, 'max': 2, 'property': 'fireskill', 'better': 'higher'}
    }
    assert not scalar_ranges(record, {'fireskill': {**properties['fireskill'], 'val1': None}}, {'item_elemskill': 126})
