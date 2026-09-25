from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from pricing.knowledge.assessment.roles.predicates import evaluate, validate
from tests.pricing.knowledge.assessment.test_family_contracts import facts


RULE = {'op': 'socket_runes_equal', 'value': ['Lem Rune'] * 6}


def sword(names=None):
    names = ['Lem Rune'] * 6 if names is None else names
    bases = {b['name']: b for b in metadata()['bases'].values()}
    return replace(
        facts('Crystal Sword'),
        sockets=6,
        socket_contents='filled',
        filled_sockets=len(names),
        empty_sockets=6 - len(names),
        socket_items=[
            {'name': n, 'base_code': bases[n]['code'], 'unit_id': i + 1, 'position': i} for i, n in enumerate(names)
        ],
    )


def test_exact_rune_count_does_not_accept_one_matching_child_or_uncertain_links():
    item = sword()
    assert evaluate(RULE, item).truth == 'true'
    assert evaluate(RULE, sword(['Lem Rune'] * 5 + ['Ist Rune'])).truth == 'false'
    assert evaluate(RULE, sword(['Lem Rune'] * 5)).truth == 'false'
    for changed in (
        replace(item, filled_sockets=None, empty_sockets=None, socket_items=item.socket_items[:5]),
        replace(item, socket_contents='empty'),
        replace(item, socket_items=[{**c, 'unit_id': 1} for c in item.socket_items]),
        replace(item, socket_items=[{**c, 'base_code': 'unknown'} for c in item.socket_items]),
    ):
        assert evaluate(RULE, changed).truth == 'unknown'


@pytest.mark.parametrize('value', [[], ['Lem Rune'] * 7, ['Unknown Rune'], ['Perfect Topaz'], 'Lem Rune'])
def test_rune_payload_schema_rejects_unsupported_or_malformed_names(value):
    with pytest.raises(ValueError):
        validate({'op': 'socket_runes_equal', 'value': value})


@pytest.mark.parametrize(
    'key',
    [
        'standard-off-hand',
        'war-cry-weapon-swap',
        'war-cry-off-hand-swap',
        'whirlwind-weapon-swap',
        'whirlwind-off-hand-swap',
        'leap-only-weapon',
        'leap-only-off-hand',
    ],
)
def test_goldfind_variants_require_complete_six_lem_payload(key):
    profile = next((p for p in build()['profiles'] if p['id'] == f'gold-find-{key}-lem-sword'), None)
    assert profile is not None

    def assess(item, player='Barbarian'):
        return assess_roles(item, [profile], {'player_class': player})

    role = assess(sword())[0]
    assert role['rule_trace']['truth'] == 'true'
    assert role['dependencies'][0]['status'] == 'true'
    assert assess(sword(['Lem Rune'] * 5 + ['Ist Rune']))[0]['dependencies'][0]['status'] == 'false'
    assert assess(facts('Crystal Sword'))[0]['status'] == 'partial'
    assert assess(sword(), 'Druid')[0]['status'] == 'failed'
    assert not assess(replace(sword(), rarity='magic'))
    assert assess(replace(sword(), base_code=facts('Broad Sword').base_code))[0]['status'] == 'failed'
