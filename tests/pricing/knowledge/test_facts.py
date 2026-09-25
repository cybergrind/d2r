"""Item facts keep equip gates and conditional effects distinct from drop metadata."""

import json

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


def test_set_bonuses_are_conditional_and_modifier_requirements_not_guessed(tmp_path):
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
    assert reduced['requirements']['strength'] is None
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
