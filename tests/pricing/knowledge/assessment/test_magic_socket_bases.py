from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import decode_stats
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('berserk-barbarian', 'luck-tiara', 'Tiara', 3, 80, 26, 35, 'Barbarian'),
    ('double-throw-barbarian-guide', 'speed-diadem', 'Diadem', 3, 96, 30, 30, 'Barbarian'),
    ('double-throw-barbarian-guide', 'nirvana-diadem', 'Diadem', 3, 2, 21, 30, 'Barbarian'),
    ('double-throw-barbarian-guide', 'luck-diadem', 'Diadem', 3, 80, 26, 35, 'Barbarian'),
    ('strafe-amazon', 'nirvana-diadem', 'Diadem', 3, 2, 21, 30, 'Amazon'),
    ('strafe-amazon', 'speed-diadem', 'Diadem', 3, 96, 30, 30, 'Amazon'),
    ('strafe-amazon', 'stability-shroud', 'Dusk Shroud', 4, 99, 24, 24, 'Amazon'),
    ('strafe-amazon', 'precision-shroud', 'Dusk Shroud', 4, 2, 10, 15, 'Amazon'),
    ('lightning-strike-amazon', 'topaz-crown', 'Crown', 3, None, None, None, 'Amazon'),
    ('lightning-strike-amazon', 'resist-crown', 'Crown', 3, None, None, None, 'Amazon'),
]


def captured(base, sockets, stat, value):
    rows = [{'id': stat, 'layer': 0, 'raw': value}] if stat else []
    decoded, _, _ = decode_stats(rows)
    return normalize(
        {
            'item': replace(facts(base, 'magic'), sockets=sockets).to_dict(),
            'decoded_stats': decoded,
            'source': {'stat_capture_complete': True},
        }
    )


@pytest.mark.parametrize(('build_name', 'suffix', 'base', 'sockets', 'stat', 'minimum', 'maximum', 'wearer'), CASES)
def test_magic_socket_base_checks_suffix_and_existing_empty_sockets(
    build_name, suffix, base, sockets, stat, minimum, maximum, wearer
):
    profile = next((p for p in build()['profiles'] if p['id'] == f'{build_name}-{suffix}-socket-base'), None)
    assert profile is not None
    context = {'player_class': wearer}
    item = captured(base, sockets, stat, minimum)
    assert assess_roles(item, [profile], context)[0]['status'] == 'partial'
    for candidate in (
        replace(item, sockets=sockets - 1),
        replace(item, socket_contents='filled'),
        replace(item, ethereal=True),
    ):
        assert assess_roles(candidate, [profile], context)[0]['status'] == 'failed'
    assert not assess_roles(replace(item, rarity='rare'), [profile], context)
    if stat:
        assert assess_roles(captured(base, sockets, stat, minimum - 1), [profile], context)[0]['status'] == 'failed'
    if minimum != maximum:
        assert assess_roles(item, [profile], context)[0]['preferences'][0]['status'] == 'false'
        perfect = assess_roles(captured(base, sockets, stat, maximum), [profile], context)[0]
        assert perfect['preferences'][0]['status'] == 'true'
    assert any('socket' in c.lower() for c in profile['conditions'])
