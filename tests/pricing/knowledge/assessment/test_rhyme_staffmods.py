"""The sourced +2 Poison Nova Rhyme use requires a capable staffmod base."""

from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from tests.pricing.knowledge.assessment.role_rows import role_rows
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def rhyme(quality, bonus):
    return replace(
        facts('Fetish Trophy', quality, name='Rhyme'),
        runeword='Rhyme',
        sockets=2,
        socket_contents='filled',
        stats={'107:92': {'status': 'decoded', 'value': bonus}},
    )


@pytest.mark.parametrize('quality', ['normal', 'superior'])
@pytest.mark.parametrize(('bonus', 'truth'), [(1, 'false'), (2, 'true'), (3, 'true')])
def test_rhyme_poison_nova_staffmod_threshold(quality, bonus, truth):
    role = next(r for r in build()['profiles'] if r['id'] == 'poison-nova-necromancer-0-rhyme')
    result = role_rows(rhyme(quality, bonus), [role], {'player_class': 'Necromancer'})
    assert result[0]['rule_trace']['truth'] == truth


def test_inferior_rhyme_is_not_a_two_point_poison_nova_candidate():
    role = next(r for r in build()['profiles'] if r['id'] == 'poison-nova-necromancer-0-rhyme')
    # Deliberately contradictory input: even a reported +2 cannot make inferior
    # quality eligible for a use requiring a staffmod it cannot generate.
    assert not role_rows(rhyme('low_quality', 2), [role], {'player_class': 'Necromancer'})
