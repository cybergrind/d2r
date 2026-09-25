from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(('variant', 'payload'), [('topaz', 'three Perfect Topazes'), ('resist', 'Ral, Ort and Thul')])
def test_empty_crown_reports_preparation_without_inventing_defense_priority(variant, payload):
    profile = next(p for p in build()['profiles'] if p['id'] == f'lightning-strike-amazon-{variant}-crown-socket-base')
    item = replace(
        facts('Crown', 'magic'), sockets=3, socket_contents='empty', stats={'31:0': {'status': 'decoded', 'value': 45}}
    )
    context = {'player_class': 'Amazon'}
    role = assess_roles(item, [profile], context)[0]
    assert role['status'] == 'partial'
    assert role['rule_trace']['truth'] == 'true'
    assert role['important_rolls'] == []
    assert any(payload in condition for condition in role['missing'])
    # Bare defense is not a source-backed selection target or a requirement.
    assert assess_roles(replace(item, stats={}), [profile], context)[0]['rule_trace']['truth'] == 'true'
    for changes in (
        {'sockets': 2},
        {'sockets': None},
        {'socket_contents': 'filled'},
        {'socket_contents': None},
        {'ethereal': True},
        {'ethereal': None},
    ):
        changed = assess_roles(replace(item, **changes), [profile], context)[0]
        assert changed['rule_trace']['truth'] != 'true'
    assert assess_roles(replace(item, rarity='rare'), [profile], context) == []
    assert assess_roles(item, [profile], {})[0]['rule_trace']['truth'] == 'unknown'
