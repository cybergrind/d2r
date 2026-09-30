"""Item facts keep equip gates and conditional effects distinct from drop metadata."""

import json

import pytest

from pricing.knowledge.facts import build_item_facts


def write_inputs(tmp_path, unique, sets=None):
    raw = tmp_path / 'pricing/raw/d2data'
    raw.mkdir(parents=True)
    files = {
        'uniqueitems': unique,
        'setitems': sets or {},
        'weapons': {'wnd': {'code': 'wnd', 'name': 'Wand', 'type': 'wand', 'levelreq': 0}},
        'armor': {'cap': {'code': 'cap', 'name': 'Cap', 'type': 'helm', 'reqstr': 15, 'levelreq': 0}},
        'misc': {},
        'itemtypes': {'helm': {'BodyLoc1': 'head'}, 'wand': {'BodyLoc1': 'rarm'}},
    }
    for name, value in files.items():
        (raw / f'{name}.json').write_text(json.dumps(value))
    return tmp_path


def test_equip_level_is_not_drop_level_and_absent_level_is_unknown(tmp_path):
    root = write_inputs(
        tmp_path,
        {
            '1': {'index': 'Early', 'code': 'cap', 'lvl': 70, 'lvl req': 7, 'spawnable': 1},
            '2': {'index': 'Unknown', 'code': 'wnd', 'lvl': 12, 'spawnable': 1},
        },
    )
    rows = build_item_facts(root)['rows']
    early, unknown = rows
    assert early['requirements'] == {'level': 7, 'strength': 15, 'dexterity': 0}
    assert early['drop_level'] == 70
    assert unknown['requirements']['level'] is None
    assert not unknown['requirements_known']
    assert early['item_id'] != unknown['item_id']


def test_set_bonuses_are_conditional_and_fixed_requirements_are_calculated(tmp_path):
    root = write_inputs(
        tmp_path,
        {
            '1': {'index': 'Reduced', 'code': 'cap', 'lvl req': 8, 'prop1': 'ease', 'min1': -20, 'max1': -20},
        },
        {
            'Hat': {
                'index': 'Hat',
                'item': 'cap',
                'lvl req': 3,
                'set': 'Pair',
                'add func': 2,
                'prop1': 'mana',
                'min1': 10,
                'max1': 10,
                'aprop1a': 'res-all',
                'amin1a': 15,
                'amax1a': 15,
            }
        },
    )
    reduced, hat = build_item_facts(root)['rows']
    assert reduced['requirements']['strength'] == 12
    assert reduced['base_requirements']['strength'] == 15
    assert [s['property'] for s in hat['stats']] == ['mana']
    assert hat['conditional_effects'][0]['condition']['pieces_required'] == 2
    assert hat['conditional_effects'][0]['property'] == 'res-all'
    assert hat['provenance']


def test_display_names_use_local_strings_without_merging_duplicate_identities(tmp_path):
    root = write_inputs(
        tmp_path,
        {
            '1': {'index': 'Internal Name', 'code': 'wnd', 'lvl req': 5},
            '2': {'index': 'Internal Name', 'code': 'cap', 'lvl req': 8},
        },
    )
    strings = root / 'pricing/raw/mr/planners/game-strings.json'
    strings.parent.mkdir(parents=True)
    strings.write_text(json.dumps([None, ['Internal Name', 'Shown Name']]))
    rows = build_item_facts(root)['rows']
    assert len(rows) == 2
    assert rows[0]['name'] == 'Shown Name'
    assert 'Internal Name' in rows[0]['aliases']
    assert rows[0]['item_id'] != rows[1]['item_id']


def test_manifest_and_census_expose_unmatched_catalog_entries(tmp_path):
    import hashlib

    root = write_inputs(tmp_path, {'1': {'index': 'Known', 'code': 'wnd', 'lvl req': 5}})
    catalog = root / 'pricing/data/appraisal-trade-catalog.json'
    catalog.parent.mkdir(parents=True)
    catalog.write_text(
        json.dumps(
            {
                'rows': [
                    {'name': 'Known', 'category': 'uniques', 'catalog_id': '1'},
                    {'name': 'Absent Hat', 'category': 'sets', 'catalog_id': '2'},
                ]
            }
        )
    )
    result = build_item_facts(root)
    assert result['coverage']['catalog_reconciliation']['set']['unmatched_catalog_names'] == ['Absent Hat']
    assert result['rows'][0]['catalog_ids'] == ['1']
    source = next(x for x in result['input_manifest'] if x['path'].endswith('uniqueitems.json'))
    assert source['sha256'] == hashlib.sha256((root / source['path']).read_bytes()).hexdigest()
    assert result['adapter_version']
    assert result['generated_at']


def test_missing_set_spawnable_is_not_treated_as_disabled(tmp_path):
    root = write_inputs(
        tmp_path,
        {'1': {'index': 'Disabled', 'code': 'wnd', 'spawnable': 0}},
        {'Hat': {'index': 'Hat', 'item': 'cap', 'lvl req': 3}},
    )
    unique, set_item = build_item_facts(root)['rows']
    assert unique['availability'] == 'disabled'
    assert set_item['availability'] == 'set_definition'
    assert set_item['availability_evidence'] == 'setitems row; no explicit spawnable flag'


def test_english_fallback_joins_new_names_and_preserves_translation_provenance(tmp_path):
    root = write_inputs(
        tmp_path,
        {
            '419': {'index': 'Unique Warlock Helm', 'code': 'cap', 'lvl req': 80},
            '2': {'index': 'OverrideKey', 'code': 'cap', 'lvl req': 1},
        },
    )
    english = root / 'third-parties/d2data/json/allstrings-eng.json'
    english.parent.mkdir(parents=True)
    english.write_text(json.dumps({'Unique Warlock Helm': "Hellwarden's Will", 'OverrideKey': 'English Name'}))
    planner = root / 'pricing/raw/mr/planners/game-strings.json'
    planner.parent.mkdir(parents=True)
    planner.write_text(json.dumps([['OverrideKey', 'Planner Name']]))
    trade = root / 'pricing/data/appraisal-trade-catalog.json'
    trade.parent.mkdir(parents=True)
    trade.write_text(
        json.dumps({'rows': [{'name': "Hellwarden's Will", 'category': 'uniques', 'catalog_id': 'market-helm'}]})
    )
    document = build_item_facts(root)
    helm, override = document['rows']
    assert helm['name'] == "Hellwarden's Will"
    assert 'Unique Warlock Helm' in helm['aliases']
    assert helm['catalog_ids'] == ['market-helm']
    assert {'path': str(english.relative_to(root)), 'record_key': 'Unique Warlock Helm'} in helm['provenance']
    assert override['name'] == 'Planner Name'
    assert {'path': str(planner.relative_to(root)), 'record_key': 'OverrideKey'} in override['provenance']
    assert any(s['path'] == str(english.relative_to(root)) and s.get('sha256') for s in document['input_manifest'])


@pytest.mark.parametrize(
    ('strength', 'dexterity', 'minimum', 'maximum', 'ethereal', 'expected'),
    [
        (58, 0, -20, -20, False, (47, 0)),
        (208, 0, -60, -60, False, (84, 0)),
        (98, 35, -30, -30, False, (69, 25)),
        (98, 35, -30, -30, True, (59, 15)),
        (15, 5, 0, 0, True, (5, 0)),
        (15, 5, -100, -100, False, (0, 0)),
        (15, 5, -20, -10, False, (None, None)),
        (15, 5, None, -20, False, (None, None)),
    ],
)
def test_native_requirement_rounding_and_unresolved_rolls(
    tmp_path, strength, dexterity, minimum, maximum, ethereal, expected
):
    native = {'index': 'Reduced', 'code': 'cap', 'lvl req': 8, 'prop1': 'ease', 'min1': minimum, 'max1': maximum}
    if ethereal:
        native.update(prop2='ethereal', min2=1, max2=1)
    root = write_inputs(tmp_path, {'1': native})
    path = root / 'pricing/raw/d2data/armor.json'
    armor = json.loads(path.read_text())
    armor['cap'].update(reqstr=strength, reqdex=dexterity)
    path.write_text(json.dumps(armor))
    row = build_item_facts(root)['rows'][0]
    assert row['requirements'] == {'level': 8, 'strength': expected[0], 'dexterity': expected[1]}
    assert row['requirements_known'] == (expected[0] is not None)
    assert ('requirement modifier arithmetic unresolved' in row['gaps']) == (expected[0] is None)


def test_tal_rasha_native_reduced_requirements():
    from pathlib import Path

    rows = {row['name']: row for row in build_item_facts(Path.cwd())['rows']}
    assert rows["Tal Rasha's Fine-Spun Cloth"]['requirements'] == {'level': 53, 'strength': 47, 'dexterity': 0}
    assert rows["Tal Rasha's Guardianship"]['requirements'] == {'level': 71, 'strength': 84, 'dexterity': 0}


@pytest.mark.parametrize(('skill_id', 'native_level', 'skill_level'), [(111, 17, 18), (121, 23, 30)])
def test_native_single_skill_raises_equip_level_and_pins_skill_source(tmp_path, skill_id, native_level, skill_level):
    root = write_inputs(
        tmp_path,
        {
            '16': {
                'index': 'Rusthandle',
                'code': 'wnd',
                'lvl req': native_level,
                'prop1': 'skill',
                'par1': skill_id,
                'min1': 1,
                'max1': 3,
            },
        },
    )
    skills = root / 'third-parties/d2data/json/skills.json'
    skills.parent.mkdir(parents=True)
    skills.write_text(json.dumps({str(skill_id): {'skill': 'Granted skill', '*Id': skill_id, 'reqlevel': skill_level}}))
    result = build_item_facts(root)
    assert result['rows'][0]['requirements']['level'] == skill_level
    assert any(row['path'] == str(skills.relative_to(root)) for row in result['input_manifest'])
    skills.write_text('{}')
    assert build_item_facts(root)['rows'][0]['requirements']['level'] is None


@pytest.mark.parametrize(
    ('property_name', 'param', 'low', 'high', 'expected'),
    [
        ('skill', 'feral rage', 1, 2, 12),
        ('skill', 232, 1, 2, 12),
        ('skill', 'missing', 1, 2, None),
        ('skill', 232, 0, 2, None),
        ('skill', 232, 0, 0, 5),
        ('hit-skill', 232, 5, 7, 5),
        ('charged', 232, 30, 14, 5),
    ],
)
def test_single_skill_requirement_preserves_native_parameter_semantics(property_name, param, low, high, expected):
    from pricing.knowledge.item_requirements import single_skill_level

    skills = {'232': {'skill': 'Feral Rage', 'reqlevel': 12}}
    prop = {'property': property_name, 'param': param, 'min': low, 'max': high}
    assert single_skill_level(5, [prop], skills) == expected
