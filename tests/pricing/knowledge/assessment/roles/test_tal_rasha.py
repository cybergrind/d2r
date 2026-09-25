from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


PIECES = {
    "Tal Rasha's Guardianship": ('Lacquered Plate', 'armor'),
    "Tal Rasha's Fine-Spun Cloth": ('Mesh Belt', 'belt'),
    "Tal Rasha's Adjudication": ('Amulet', 'amulet'),
}


@pytest.mark.parametrize('name', PIECES)
def test_tal_mf_piece_needs_other_two_player_pieces(name):
    base, slot = PIECES[name]
    profile = next(p for p in build()['profiles'] if p['id'] == f'lightning-mf-tal-{slot}')
    item = facts(base, 'set', name)
    role = assess_roles(item, [profile])[0]
    assert role['side'] == 'player'
    assert role['status'] == 'partial'
    companions = [p for p in role['dependencies'] if p['label'].startswith('Wear ')]
    assert len(companions) == 2
    assert all(p['status'] == 'unknown' for p in companions)
    assert {p['label'][5:] for p in companions} == PIECES.keys() - {name}
    context = {'player_class': 'Sorceress', 'player_items': list(PIECES.keys() - {name})}
    role = assess_roles(item, [profile], context)[0]
    assert all(p['status'] == 'true' for p in role['dependencies'] if p['label'].startswith('Wear '))
    assert role['dependencies'][-1]['status'] == 'unknown'
    # Known companions do not establish the loadout breakpoint.
    assert role['status'] == 'partial'
    known_total = assess_roles(item, [profile], {**context, 'player_total_fcr': 117})[0]
    assert all(p['status'] == 'true' for p in known_total['dependencies'])
    assert known_total['status'] == ('partial' if slot == 'armor' else 'matched')
    absent = assess_roles(item, [profile], {**context, 'player_items': []})[0]
    assert sum(p['status'] == 'false' for p in absent['dependencies']) == 2
    merc = assess_roles(item, [profile], {'mercenary_items': list(PIECES)})[0]
    assert all(p['status'] == 'unknown' for p in merc['dependencies'])
    assert assess_roles(replace(item, rarity='rare'), [profile]) == []
    assert assess_roles(replace(item, name='Unverified set identity'), [profile]) == []


def test_tal_armor_reports_ist_requirement_without_demanding_it_on_belt_or_amulet():
    profiles = [p for p in build()['profiles'] if p['id'].startswith('lightning-mf-tal-')]
    assert len(profiles) == 3
    for name, (base, _) in PIECES.items():
        item = facts(base, 'set', name)
        role = assess_roles(item, profiles)[0]
        assert any('Ist Rune' in s for s in role['missing']) == (name == "Tal Rasha's Guardianship")
        if name == "Tal Rasha's Guardianship":
            role = assess_roles(
                replace(item, sockets=1, socket_contents='filled', socket_items=[{'name': 'Ist Rune'}]), profiles
            )[0]
            assert 'Setup socket: Ist Rune' in role['matched']
            assert not any('Ist Rune' in s for s in role['missing'])
