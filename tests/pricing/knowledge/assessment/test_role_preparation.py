from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_deaths_guard_role_links_only_the_cited_upgrade_and_keeps_current_dependency_false():
    profile = next(p for p in build()['profiles'] if p['id'] == 'strafe-amazon-deaths-guard-upgrade')
    item = replace(facts('Sash', 'set', "Death's Guard"), stats={'153:0': {'status': 'decoded', 'value': 1}})
    role = assess_roles(item, [profile], {'player_class': 'Amazon'})[0]
    dependency = role['dependencies'][0]
    assert dependency['status'] == 'false'
    assert dependency['preparation']['target_name'] == 'Demonhide Sash'
    assert len(dependency['preparation']['steps']) == 1
    assert role['status'] == 'partial'
    text = ' '.join(role['missing'])
    assert 'Tal Rune + Shael Rune + Perfect Diamond' in text
    assert 'Spiderweb Sash' not in text
    assert item.base_name == 'Sash'


def test_failed_unknown_and_satisfied_roles_do_not_recommend_preparation():
    profile = next(p for p in build()['profiles'] if p['id'] == 'strafe-amazon-deaths-guard-upgrade')
    item = replace(facts('Sash', 'set', "Death's Guard"), stats={'153:0': {'status': 'decoded', 'value': 1}})
    for changed, context in (
        (item, {'player_class': 'Barbarian'}),
        (item, {}),
        (replace(item, identified=False), {'player_class': 'Amazon'}),
        (replace(item, stats={}), {'player_class': 'Amazon'}),
        (replace(item, base_code=facts('Demonhide Sash').base_code), {'player_class': 'Amazon'}),
    ):
        role = assess_roles(changed, [profile], context)[0]
        assert 'preparation' not in role['dependencies'][0]


def test_upgrade_dependency_link_does_not_depend_on_other_dependency_order():
    profile = next(p for p in build()['profiles'] if p['id'] == 'strafe-amazon-deaths-guard-upgrade')
    upgrade = profile['depends_on'][0]
    other = {
        'label': 'Confirm mercenary',
        'when': {
            'op': 'context_eq',
            'field': 'mercenary_type',
            'value': 'Act 2',
        },
    }
    item = replace(facts('Sash', 'set', "Death's Guard"), stats={'153:0': {'status': 'decoded', 'value': 1}})
    for dependencies in ([other, upgrade], [upgrade, other]):
        role = assess_roles(item, [{**profile, 'depends_on': dependencies}], {'player_class': 'Amazon'})[0]
        assert sum('preparation' in row for row in role['dependencies']) == 1
        assert role['status'] == 'partial'
