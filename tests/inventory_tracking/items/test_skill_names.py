import pytest

from inventory_tracking.items.metadata import decode_stats, metadata


@pytest.mark.parametrize(
    ('skill', 'name', 'class_name'),
    [
        (234, 'Fissure', 'Druid'),
        (237, 'Summon Dire Wolf', 'Druid'),
        (251, 'Fire Blast', 'Assassin'),
        (262, 'Wake of Fire', 'Assassin'),
        (280, 'Phoenix Strike', 'Assassin'),
        (383, 'Levitation Mastery', 'Warlock'),
    ],
)
def test_player_skill_bonuses_use_localized_names_with_unchanged_native_identity(skill, name, class_name):
    stat = {'id': 107, 'layer': skill, 'raw': 3}
    rows, _, unresolved = decode_stats([stat])
    assert not unresolved
    assert rows[0]['text'] == f'+3 to {name} ({class_name} Only)'
    assert rows[0]['memory_stat'] == stat


def test_fissure_keeps_internal_name_for_source_traceability():
    assert metadata()['skills']['234']['name'] == 'Fissure'
    assert metadata()['skills']['234']['internal_name'] == 'Eruption'


def test_skill_name_compiler_preserves_internal_fallbacks_and_nonplayer_variants():
    from inventory_tracking.items.build_metadata import build_skills

    rows = {
        'a': {'*Id': 234, 'skill': 'Eruption', 'charclass': 'dru', 'skilldesc': 'eruption'},
        'b': {'*Id': 999, 'skill': 'Internal Variant', 'skilldesc': 'eruption'},
        'c': {'*Id': 1000, 'skill': 'Untranslated', 'charclass': 'dru', 'skilldesc': 'unknown'},
    }
    desc = {'1': {'skilldesc': 'eruption', 'str name': 'Skillname235'}}
    result = build_skills(rows, desc, {'Skillname235': 'Fissure'})
    assert result['234']['name'] == 'Fissure'
    assert result['999']['name'] == 'Internal Variant'
    assert result['1000']['name'] == 'Untranslated'
    assert build_skills(rows, desc, {})['234']['name'] == 'Eruption'


def test_localized_fissure_projects_by_native_skill_identity():
    from pricing.knowledge.assessment.adapters.market_projection import market_properties

    assert market_properties()['107:234'] == '1121'
