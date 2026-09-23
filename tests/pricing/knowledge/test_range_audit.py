import json

from pricing.knowledge import range_audit


def test_audit_accounts_for_every_property_without_calling_damage_endpoints_rolls(tmp_path, monkeypatch):
    source = {
        'index': 'Fixture',
        '*ID': 1,
        'prop1': 'ac%',
        'min1': 100,
        'max1': 150,
        'prop2': 'dmg-fire',
        'min2': 10,
        'max2': 30,
        'prop3': 'skill',
        'min3': 1,
        'max3': 3,
        'par3': 12,
        'aprop1a': 'str',
        'amin1a': 10,
        'amax1a': 10,
    }
    files = {
        'pricing/raw/d2data/uniqueitems.json': {'Fixture': source},
        'pricing/raw/d2data/setitems.json': {},
        'third-parties/d2data/json/properties.json': {'dmg-fire': {'func1': 15}},
    }
    for name, data in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
    monkeypatch.setattr(
        range_audit,
        'build_definitions',
        lambda root: {
            'source_date': 'fixture',
            'inputs': {},
            'rows': [
                {
                    'rarity': 'unique',
                    'table_id': 1,
                    'name': 'Fixture',
                    'base_code': 'fixture',
                    'base_defense_range': None,
                    'roll_ranges': {'16': {'property': 'ac%'}},
                }
            ],
        },
    )
    audit = range_audit.audit_ranges(tmp_path)
    assert audit['item_count'] == 1
    assert sum(audit['property_counts'].values()) == 4
    assert audit['property_counts'] == {
        'covered_scalar_range': 1,
        'damage_endpoints_not_roll_bounds': 1,
        'uncovered_variable_or_encoding': 1,
        'conditional_set_bonus_review': 1,
    }
    assert not audit['complete_range_coverage']
