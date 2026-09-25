from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('hammer-mf-stealskull-merc', 'Stealskull', 'Casque', 'Ist Rune', 5),
    ('blizzard-mf-stealskull-merc', 'Stealskull', 'Casque', 'Ist Rune', 5),
    ('meteor-mf-stealskull-merc', 'Stealskull', 'Casque', 'Ist Rune', 5),
    *[
        (f'gold-find-{variant}-crown-merc', 'Crown of Thieves', 'Grand Crown', 'Lem Rune', 9)
        for variant in ('standard', 'war-cry', 'whirlwind', 'leap-only')
    ],
]


@pytest.mark.parametrize(('role_id', 'name', 'base', 'rune', 'leech'), CASES)
def test_farming_helm_roles_preserve_socket_and_setup_conditions(role_id, name, base, rune, leech):
    profile = next((p for p in build()['profiles'] if p['id'] == role_id), None)
    assert profile is not None
    stats = {
        f'{stat}:0': {'status': 'decoded', 'value': value}
        for stat, value in ((60, leech), (80, 30), (79, 80), (93, 10))
    }
    item = replace(facts(base, 'unique', name), stats=stats)
    role = assess_roles(item, [profile])[0]
    assert role['side'] == 'merc'
    assert role['rule_trace']['truth'] == 'true'
    assert role['status'] == 'partial'
    assert any(rune in text for text in role['missing'])
    assert any(p['label'] == 'Ethereal mercenary helmet' and p['status'] == 'false' for p in role['preferences'])
    filled = replace(
        item, ethereal=True, sockets=1, socket_contents='filled', socket_items=[{'name': rune, 'item_type': 'rune'}]
    )
    prepared = assess_roles(filled, [profile], {'mercenary_type': 'Act 2 Might'})[0]
    assert any('Setup socket: ' + rune == text for text in prepared['matched'])
    assert prepared['status'] == 'partial'  # Full mercenary loadout still matters.
    bad = replace(item, stats={**stats, '60:0': {'status': 'decoded', 'value': leech - 1}})
    assert assess_roles(bad, [profile])[0]['status'] == 'failed'
    assert assess_roles(replace(item, rarity='rare'), [profile]) == []


def test_gold_find_crown_keeps_upgrade_separate_from_item_viability():
    profile = next(p for p in build()['profiles'] if p['id'] == 'gold-find-standard-crown-merc')
    item = replace(
        facts('Grand Crown', 'unique', 'Crown of Thieves'),
        stats={
            '60:0': {'status': 'decoded', 'value': 9},
            '79:0': {'status': 'decoded', 'value': 80},
        },
    )
    role = assess_roles(item, [profile], {'mercenary_type': 'Act 2 Might'})[0]
    assert role['rule_trace']['truth'] == 'true'
    dependency = next(d for d in role['dependencies'] if d['label'] == 'Cited upgraded Corona base')
    assert dependency['status'] == 'false'
    upgraded = replace(facts('Corona', 'unique', 'Crown of Thieves'), stats=item.stats)
    role = assess_roles(upgraded, [profile], {'mercenary_type': 'Act 2 Might'})[0]
    assert all(d['status'] == 'true' for d in role['dependencies'])
    assert role['status'] == 'partial'  # Lem and full setup still unverified.
