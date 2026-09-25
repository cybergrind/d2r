from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    'patch',
    [
        {'sockets': 0},
        {'socket_contents': 'empty'},
        {'sockets': None},
        {'socket_contents': None},
        {'filled_sockets': 0},
        {'socket_items': [{'name': 'Ist Rune'}, {'name': 'Ist Rune'}]},
    ],
)
def test_required_rune_name_does_not_override_unknown_or_conflicting_socket_state(patch):
    profile = next(p for p in build()['profiles'] if p['id'] == 'hammer-mf-stealskull-merc')
    item = replace(
        facts('Casque', 'unique', 'Stealskull'),
        sockets=1,
        socket_contents='filled',
        socket_items=[{'name': 'Ist Rune'}],
        stats={f'{stat}:0': {'status': 'decoded', 'value': value} for stat, value in ((60, 5), (80, 55), (93, 10))},
    )
    assert 'Setup socket: Ist Rune' in assess_roles(item, [profile])[0]['matched']
    invalid = assess_roles(replace(item, **patch), [profile])[0]
    assert 'Setup socket: Ist Rune' not in invalid['matched']
    assert any('Setup socket requires Ist Rune' in text for text in invalid['missing'])


def test_verified_required_child_does_not_need_unrelated_socket_identities():
    from pricing.knowledge.assessment.roles.socket_payload import has_verified_socket_item

    item = replace(
        facts('Mage Plate'),
        sockets=3,
        socket_contents='filled',
        filled_sockets=2,
        empty_sockets=1,
        socket_items=[{'name': 'Ist Rune'}],
    )
    assert not item.socket_state.identities_complete
    assert has_verified_socket_item(item, 'Ist Rune')
    assert not has_verified_socket_item(item, 'Lem Rune')
    assert not has_verified_socket_item(replace(item, filled_sockets=None, empty_sockets=None), 'Ist Rune')
