from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


IDS = [
    'lightning-starter-insight-merc',
    'nova-starter-insight-merc',
    'nova-standard-insight-merc',
    'nova-mf-insight-merc',
    'blizzard-starter-insight-merc',
    'blizzard-mf-insight-merc',
    'poison-starter-insight-merc',
    'poison-budget-insight-merc',
    'hammer-starter-insight-merc',
    'hammer-standard-insight-merc',
    'hammer-mf-insight-merc',
    'hammer-ubers-insight-merc',
]


@pytest.mark.parametrize('role_id', IDS)
def test_insight_merc_requires_native_legal_polearm_and_socket_capacity(role_id):
    profile = next(p for p in build()['profiles'] if p['id'] == role_id)

    def item(base, quality='normal'):
        return replace(
            facts(base, quality, 'Insight'),
            runeword='Insight',
            sockets=4,
            socket_contents='filled',
            stats={'151:120': {'status': 'decoded', 'value': 12}},
        )

    for base in ('Bill', 'Thresher', 'Scythe'):
        for quality in ('normal', 'superior', 'low_quality'):
            assert assess_roles(item(base, quality), [profile])[0]['rule_trace']['truth'] == 'true'
    # An Act 2 merc can wield a spear, but Insight cannot be made in one.
    assert assess_roles(item('War Pike'), [profile]) == []
    # Bardiche is a polearm, but cannot have the four sockets this word requires.
    assert assess_roles(item('Bardiche'), [profile])[0]['status'] == 'failed'
    unknown = replace(item('Bill'), base_code=None)
    assert assess_roles(unknown, [profile])[0]['rule_trace']['truth'] == 'unknown'


@pytest.mark.parametrize('role_id', IDS)
def test_insight_merc_role_requires_completed_recipe_and_meditation_but_not_perfect_roll(role_id):
    profile = next(p for p in build()['profiles'] if p['id'] == role_id)
    item = replace(
        facts('Bill', 'normal', 'Insight'),
        runeword='Insight',
        sockets=4,
        socket_contents='filled',
        stats={'151:120': {'status': 'decoded', 'value': 12}},
    )
    result = assess_roles(item, [profile])[0]
    assert result['side'] == 'merc'
    assert result['rule_trace']['truth'] == 'true'
    assert result['status'] == 'partial'
    assert any(p['label'] == 'Level 17 Meditation' and p['status'] == 'false' for p in result['preferences'])
    for other in (replace(item, runeword='Spirit'), replace(item, sockets=3), replace(item, socket_contents='empty')):
        assert assess_roles(other, [profile])[0]['status'] == 'failed'
    assert assess_roles(replace(item, stats={}), [profile])[0]['rule_trace']['truth'] == 'unknown'
    assert assess_roles(replace(item, item_type='staf'), [profile]) == []
