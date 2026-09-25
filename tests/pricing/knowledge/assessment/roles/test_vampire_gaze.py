from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


IDS = [
    'dream-hybrid-gaze-merc',
    'dream-ubers-gaze-merc',
    'lightning-strike-standard-gaze-merc',
    'lightning-strike-ubers-gaze-merc',
    'lightning-fury-ubers-gaze-merc',
    'lightning-sorc-mephisto-gaze-merc',
]


def gaze():
    return replace(
        facts('Grim Helm', 'unique', 'Vampire Gaze'),
        stats={
            '60:0': {'status': 'decoded', 'value': 6},
            '36:0': {'status': 'decoded', 'value': 15},
        },
    )


@pytest.mark.parametrize('identity', IDS)
def test_gaze_roles_accept_low_rolls_but_preserve_mercenary_context(identity):
    profile = next((p for p in build()['profiles'] if p['id'] == identity), None)
    assert profile is not None
    role = assess_roles(gaze(), [profile])[0]
    assert role['side'] == 'merc'
    assert role['rule_trace']['truth'] == 'true'
    assert role['status'] == 'partial'
    assert any('Mercenary type' in missing for missing in role['missing'])
    if identity in IDS[-2:]:
        assert any('Um Rune' in missing for missing in role['missing'])
    if identity == 'lightning-strike-ubers-gaze-merc':
        assert 'required_rune' not in profile
    poor = replace(gaze(), stats={**gaze().stats, '60:0': {'status': 'decoded', 'value': 5}})
    assert assess_roles(poor, [profile])[0]['status'] == 'failed'
    if identity == 'lightning-sorc-mephisto-gaze-merc':
        assert any('Uber Mephisto' in text for text in role['missing'])


def test_rogue_gaze_requires_ias_and_all_resistances_on_one_jewel():
    profile = next((p for p in build()['profiles'] if p['id'] == IDS[0]), None)
    assert profile is not None
    stats = {f'{stat}:0': {'status': 'decoded', 'value': 15} for stat in (93, 39, 41, 43, 45)}
    item = replace(
        gaze(),
        sockets=1,
        socket_contents='filled',
        socket_items=[
            {'name': 'Scintillating Jewel of Fervor', 'item_type': 'jewl', 'stats_complete': True, 'stats': stats}
        ],
    )
    role = assess_roles(item, [profile], {'mercenary_type': 'Act 1 Cold'})[0]
    assert all(d['status'] == 'true' for d in role['dependencies'])
    missing = replace(item, socket_items=[], stats={**gaze().stats, **stats})
    role = assess_roles(missing, [profile], {'mercenary_type': 'Act 1 Cold'})[0]
    assert any(d['status'] != 'true' for d in role['dependencies'])
