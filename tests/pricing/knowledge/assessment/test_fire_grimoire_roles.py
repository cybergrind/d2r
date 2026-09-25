from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(('variant', 'rune'), [('standard', 'Um Rune'), ('mf', 'Ist Rune')])
def test_fire_warlock_grimoire_preserves_variant_socket_and_skill_requirements(variant, rune):
    profile = next((p for p in build()['profiles'] if p['id'] == f'fire-warlock-{variant}-ars-diabolos'), None)
    assert profile is not None
    item = replace(
        facts('Blasphemous Grimoire', 'unique', "Ars Al'Diabolos"),
        sockets=1,
        socket_contents='filled',
        socket_items=[{'name': rune}],
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in [('188:58', 2), ('105:0', 25), ('329:0', 25), ('107:401', 5)]
        },
    )
    result = assess_roles(item, [profile], {'player_class': 'Warlock'})[0]
    assert result['rule_trace']['truth'] == 'true'
    assert result['slot'] == 'Off-Hand'
    assert 'Setup socket: ' + rune in result['matched']
    assert all(p['status'] == 'true' for p in result['preferences'])
    missing_rune = replace(item, sockets=0, socket_contents='empty', socket_items=[])
    result = assess_roles(missing_rune, [profile], {'player_class': 'Warlock'})[0]
    assert result['status'] == 'partial'
    assert any(rune in message for message in result['missing'])
    for key in ('188:58', '105:0', '329:0', '107:401'):
        changed = replace(item, stats={k: v for k, v in item.stats.items() if k != key})
        assert assess_roles(changed, [profile], {'player_class': 'Warlock'})[0]['status'] == 'failed'
    assert not assess_roles(replace(item, name="Ars Tor'Baalos"), [profile], {'player_class': 'Warlock'})
    assert assess_roles(item, [profile], {'player_class': 'Sorceress'})[0]['status'] == 'failed'

    assert assess_roles(replace(item, ethereal=True), [profile], {'player_class': 'Warlock'})[0]['status'] == 'failed'
