from pricing.knowledge.named_triggers import fixed_triggers


def test_trigger_compiler_preserves_event_level_and_chance_without_scalar_roll_ordering():
    record = {'prop1': 'hit-skill', 'par1': 66, 'min1': 5, 'max1': 2}
    props = {'hit-skill': {'func1': 11, 'stat1': 'item_skillonhit'}}
    stats = {'item_skillonhit': 198}
    skills = {'Amplify Damage': 66}
    assert fixed_triggers(record, props, stats, skills) == [{'stat_id': 198, 'skill_id': 66, 'level': 2, 'chance': 5}]
    assert fixed_triggers({**record, 'par1': 'Amplify Damage'}, props, stats, skills) == fixed_triggers(
        record, props, stats, skills
    )
    assert fixed_triggers(record, {'hit-skill': {'func1': 1, 'stat1': 'item_skillonhit'}}, stats, skills) == []
    for changed in ({'par1': 999}, {'min1': 101}, {'max1': 64}, {'max1': True}):
        assert fixed_triggers({**record, **changed}, props, stats, skills) == []


def test_runeword_trigger_fields_use_recipe_namespace():
    properties = {'hit-skill': {'func1': 11, 'stat1': 'item_skillonhit'}}
    stats = {'item_skillonhit': 198}
    skills = {'Decrepify': 87}
    record = {
        'T1Code4': 'hit-skill',
        'T1Param4': 'Decrepify',
        'T1Min4': 20,
        'T1Max4': 15,
        'prop1': 'hit-skill',
        'par1': 87,
        'min1': 99,
        'max1': 1,
    }
    assert fixed_triggers(record, properties, stats, skills, runeword=True) == [
        {'stat_id': 198, 'skill_id': 87, 'level': 15, 'chance': 20}
    ]


def test_trigger_skill_names_accept_case_only_variants_but_not_ambiguous_ids():
    record = {'T1Code3': 'kill-skill', 'T1Param3': 'enchant', 'T1Min3': 30, 'T1Max3': 21}
    properties = {'kill-skill': {'func1': 11, 'stat1': 'item_skillonkill'}}
    stats = {'item_skillonkill': 196}
    assert fixed_triggers(record, properties, stats, {'Enchant': 52}, runeword=True) == [
        {'stat_id': 196, 'skill_id': 52, 'level': 21, 'chance': 30}
    ]
    assert fixed_triggers(record, properties, stats, {'Enchant': 52, 'ENCHANT': 99}, runeword=True) == []


def test_colossal_jewel_trigger_codes_accept_native_case_variants():
    import json
    from pathlib import Path

    root = Path('third-parties/d2data/json')
    unique = json.loads((root / 'uniqueitems.json').read_text())
    properties = json.loads((root / 'properties.json').read_text())
    expected = {
        "Defender's Bile": (68, 25),
        "Guardian's Thunder": (235, 25),
        "Protector's Frost": (40, 25),
        "Defender's Fire": (46, 25),
        "Protector's Stone": (267, 15),
        "Guardian's Light": (387, 25),
    }
    for name, (skill, level) in expected.items():
        record = next(r for r in unique.values() if r['index'] == name)
        assert record['prop1'] == 'Gethit-skill'
        assert fixed_triggers(record, properties, {'item_skillongethit': 201}, {name: skill}) == [
            {'stat_id': 201, 'skill_id': skill, 'level': level, 'chance': 1}
        ]
    assert fixed_triggers({'prop1': None}, properties, {}, {}) == []
