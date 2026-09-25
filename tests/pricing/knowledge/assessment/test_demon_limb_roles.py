from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_demon_limb_prebuff_roles_require_available_enchant_and_correct_player():
    profiles = [p for p in build()['profiles'] if p['role'] == 'Demon Limb Enchant prebuff']
    assert len(profiles) == 4
    for profile in profiles:
        player_class = profile['must']['value']
        item = facts('Tyrant Club', 'unique', 'Demon Limb')
        context = {'player_class': player_class, 'player_items': []}
        for remaining, status in [(0, 'false'), (1, 'true')]:
            charged = replace(
                item,
                stats={
                    '204:3351': {
                        'status': 'decoded',
                        'value': remaining,
                        'unit': 'charges_remaining',
                        'charges': {'remaining': remaining, 'maximum': 20},
                    }
                },
            )
            result = assess_roles(charged, [profile], context)[0]
            assert result['dependencies'][0]['status'] == status
            assert assess_roles(charged, [profile], {**context, 'player_class': 'Sorceress'})[0]['status'] == 'failed'
        unknown = assess_roles(replace(item, capture_complete=False), [profile], context)[0]
        assert unknown['dependencies'][0]['status'] == 'unknown'
        assert not assess_roles(facts('Tyrant Club', 'rare'), [profile], context)
    strafe = next(p for p in profiles if p['build'] == 'strafe-amazon')
    result = assess_roles(item, [strafe], {'player_class': 'Amazon', 'player_items': ['Lava Gout']})[0]
    assert result['dependencies'][1]['status'] == 'false'
