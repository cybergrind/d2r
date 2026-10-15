from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from tests.pricing.knowledge.assessment.role_rows import role_rows
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
    result = role_rows(item, [profile], {'player_class': 'Warlock'})[0]
    assert result['rule_trace']['truth'] == 'true'
    assert result['slot'] == 'Off-Hand'
    assert 'Setup socket: ' + rune in result['matched']
    assert all(p['status'] == 'true' for p in result['preferences'])
    missing_rune = replace(item, sockets=0, socket_contents='empty', socket_items=[])
    result = role_rows(missing_rune, [profile], {'player_class': 'Warlock'})[0]
    assert result['status'] == 'partial'
    assert any(rune in message for message in result['missing'])
    for key in ('188:58', '105:0', '329:0', '107:401'):
        changed = replace(item, stats={k: v for k, v in item.stats.items() if k != key})
        assert role_rows(changed, [profile], {'player_class': 'Warlock'})[0]['status'] == 'failed'
    assert not role_rows(replace(item, name="Ars Tor'Baalos"), [profile], {'player_class': 'Warlock'})
    assert role_rows(item, [profile], {'player_class': 'Sorceress'})[0]['status'] == 'failed'

    assert role_rows(replace(item, ethereal=True), [profile], {'player_class': 'Warlock'})[0]['status'] == 'failed'
