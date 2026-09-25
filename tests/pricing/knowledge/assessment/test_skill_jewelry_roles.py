import pytest

from inventory_tracking.items.metadata import decode_stats
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = (
    [
        (build, suffix, base, key, skill, secondary, minimum, wearer)
        for build, wearer in [('lightning-sentry-assassin', 'Assassin'), ('wake-of-fire-assassin', 'Assassin')]
        for suffix, base, key, skill, secondary, minimum in [
            ('cunning-magus', 'Diadem', '188:48', 3, 105, 20),
            ('cunning-whale', 'Amulet', '188:48', 3, 7, 81),
            ('cunning-apprentice', 'Amulet', '188:48', 3, 105, 10),
        ]
    ]
    + [
        (build, 'berserker-magus', 'Diadem', '83:4', 2, 105, 20, 'Barbarian')
        for build in ('berserk-barbarian', 'double-throw-barbarian-guide')
    ]
    + [
        ('poison-nova-necromancer', variant, 'Amulet', '188:17', 3, None, None, 'Necromancer')
        for variant in ('starter-venomous', 'budget-venomous')
    ]
)


def item(base, key, skill, secondary, value, rarity='magic'):
    stat, layer = map(int, key.split(':'))
    rows = [{'id': stat, 'layer': layer, 'raw': skill}]
    if secondary:
        rows.append({'id': secondary, 'layer': 0, 'raw': value * 256 if secondary == 7 else value})
    decoded, _, _ = decode_stats(rows)
    return normalize(
        {'item': facts(base, rarity).to_dict(), 'decoded_stats': decoded, 'source': {'stat_capture_complete': True}}
    )


@pytest.mark.parametrize(('build_name', 'suffix', 'base', 'key', 'skill', 'secondary', 'minimum', 'wearer'), CASES)
def test_skill_jewelry_requires_source_combination(build_name, suffix, base, key, skill, secondary, minimum, wearer):
    profile = next((p for p in build()['profiles'] if p['id'] == f'{build_name}-{suffix}'), None)
    assert profile is not None
    context = {'player_class': wearer}
    matching = item(base, key, skill, secondary, minimum)
    result = assess_roles(matching, [profile], context)[0]
    assert result['status'] != 'failed'
    assert assess_roles(item(base, key, skill - 1, secondary, minimum), [profile], context)[0]['status'] == 'failed'
    stat, layer = key.split(':')
    wrong_skill = item(base, f'{stat}:{int(layer) + 1}', skill, secondary, minimum)
    assert assess_roles(wrong_skill, [profile], context)[0]['status'] == 'failed'
    if secondary:
        assert assess_roles(item(base, key, skill, secondary, minimum - 1), [profile], context)[0]['status'] == 'failed'
    assert assess_roles(matching, [profile], {'player_class': 'Druid'})[0]['status'] == 'failed'
    rare = item(base, key, skill, secondary, minimum, 'rare')
    if key == '83:4':
        assert assess_roles(rare, [profile], context)[0]['status'] != 'failed'
    else:
        assert assess_roles(rare, [profile], context) == []
