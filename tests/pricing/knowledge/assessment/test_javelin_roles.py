from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def javelin(skills=6, ias=40, base='Matriarchal Javelin', quality='magic'):
    return replace(
        facts(base, quality),
        stats={f'{s}:{layer}': {'status': 'decoded', 'value': v} for s, layer, v in [(188, 2, skills), (93, 0, ias)]},
    )


def test_lightning_fury_javelin_role_preserves_skill_speed_base_and_quality():
    profile = next((p for p in build()['profiles'] if p['id'] == 'lightning-fury-starter-lancers-javelin'), None)
    assert profile is not None
    for skills in (4, 5, 6):
        result = assess_roles(javelin(skills), [profile], {'player_class': 'Amazon'})[0]
        assert result['status'] == 'partial'
        assert result['rule_trace']['truth'] == 'true'
        assert (result['preferences'][0]['status'] == 'true') is (skills == 6)
    for item in (
        javelin(3),
        javelin(7),
        javelin(6, 30),
        javelin(6, 45),
        javelin(base='Maiden Javelin'),
        replace(javelin(), ethereal=True),
    ):
        assert assess_roles(item, [profile], {'player_class': 'Amazon'})[0]['status'] == 'failed'
    assert not assess_roles(javelin(quality='rare'), [profile], {'player_class': 'Amazon'})
    assert assess_roles(javelin(), [profile], {'player_class': 'Druid'})[0]['status'] == 'failed'
    assert assess_roles(javelin(), [profile])[0]['status'] == 'partial'
