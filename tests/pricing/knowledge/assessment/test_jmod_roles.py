from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import decode_stats
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('blizzard-sorceress', 'main-shield', 'Sorceress'),
    ('blizzard-sorceress', 'main-swap', 'Sorceress'),
    ('blizzard-sorceress', 'standard-swap', 'Sorceress'),
    ('fissure-druid', 'main-shield', 'Druid'),
    ('fissure-druid', 'magic-find-shield', 'Druid'),
    ('lightning-sentry-assassin', 'main-shield', 'Assassin'),
    ('lightning-sentry-assassin', 'main-swap', 'Assassin'),
    ('lightning-sorceress', 'main-shield', 'Sorceress'),
    ('lightning-strike-amazon', 'main-shield', 'Amazon'),
    ('poison-nova-necromancer', 'main-shield', 'Necromancer'),
    ('lightning-fury-amazon-guide', 'main-shield', 'Amazon'),
    ('lightning-fury-amazon-guide', 'ubers-shield', 'Amazon'),
]


def monarch(block=20, fbr=30):
    decoded, _, _ = decode_stats([{'id': 20, 'layer': 0, 'raw': block}, {'id': 102, 'layer': 0, 'raw': fbr}])
    return normalize(
        {
            'item': replace(facts('Monarch', 'magic'), sockets=4).to_dict(),
            'decoded_stats': decoded,
            'source': {'stat_capture_complete': True},
        }
    )


@pytest.mark.parametrize(('build_name', 'suffix', 'wearer'), CASES)
def test_empty_jmod_role_requires_both_affixes_and_four_empty_sockets(build_name, suffix, wearer):
    profile = next((p for p in build()['profiles'] if p['id'] == f'{build_name}-{suffix}-jmod-base'), None)
    assert profile is not None
    item = monarch()
    context = {'player_class': wearer}
    assert assess_roles(item, [profile], context)[0]['status'] == 'partial'
    bad = [
        monarch(19),
        monarch(fbr=29),
        replace(item, sockets=3),
        replace(item, ethereal=True),
        replace(item, socket_contents='filled'),
        replace(item, base_code=facts('Aegis').base_code),
    ]
    for candidate in bad:
        assert assess_roles(candidate, [profile], context)[0]['status'] == 'failed'
    assert assess_roles(replace(item, socket_contents=None), [profile], context)[0]['status'] == 'partial'
    assert not assess_roles(replace(item, rarity='rare'), [profile], context)
    assert any('socket' in s.lower() for s in profile['conditions'])
