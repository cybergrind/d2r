from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def rule(variant):
    result = next((r for r in build()['profiles'] if r['id'] == f'fissure-merc-{variant}-andariel'), None)
    assert result is not None
    return result


def jewel(ed=31, ias=15):
    return {
        'name': 'Ruby Jewel of Fervor',
        'item_type': 'jewl',
        'stats_complete': True,
        'stats': {f'{s}:0': {'status': 'decoded', 'value': v} for s, v in ((17, ed), (18, ed), (93, ias))},
    }


def helmet(children):
    return replace(
        facts('Demonhead', 'unique', "Andariel's Visage"), sockets=1, socket_contents='filled', socket_items=children
    )


CONTEXT = {'player_class': 'Druid', 'mercenary_type': 'Act 2 Might', 'mercenary_items': ['Infinity', 'Fortitude']}


@pytest.mark.parametrize(
    ('variant', 'ed', 'expected'),
    [
        ('magic-find', 31, 'true'),
        ('magic-find', 40, 'true'),
        ('magic-find', 30, 'false'),
        ('magic-find', 41, 'false'),
        ('standard', 40, 'true'),
        ('standard', 31, 'false'),
    ],
)
def test_variant_socket_targets_and_ethereal_preference(variant, ed, expected):
    profile = rule(variant)
    item = helmet([jewel(ed)])
    role = assess_roles(item, [profile], CONTEXT)[0]
    assert role['rule_trace']['truth'] == 'true'
    assert role['dependencies'][-1]['status'] == expected
    assert role['status'] == 'partial'
    assert assess_roles(replace(item, ethereal=True), [profile], CONTEXT)[0]['preferences'][0]['status'] == 'true'


@pytest.mark.parametrize('mode', ['fire-ruby', 'split', 'totals', 'incomplete'])
def test_jewel_name_parent_totals_or_separate_children_do_not_prove_payload(mode):
    profile = rule('magic-find')
    item = helmet([jewel()])
    if mode == 'fire-ruby':
        child = jewel(0)
        child['stats']['39:0'] = {'status': 'decoded', 'value': 30}
        item = helmet([child])
    elif mode == 'split':
        item = replace(helmet([jewel(40, 0), jewel(0, 15)]), sockets=2)
    elif mode == 'totals':
        item = replace(helmet([]), stats=jewel()['stats'])
    else:
        item = helmet([{'item_type': 'jewl', 'name': 'Ruby Jewel of Fervor'}])
    assert assess_roles(item, [profile], CONTEXT)[0]['dependencies'][-1]['status'] != 'true'


def test_empty_helmet_remains_a_candidate_with_preparation_and_loadout_missing():
    profile = rule('magic-find')
    item = facts('Demonhead', 'unique', "Andariel's Visage")
    role = assess_roles(item, [profile], {'player_class': 'Druid'})[0]
    assert role['rule_trace']['truth'] == 'true'
    assert role['status'] == 'partial'
    assert any(d['status'] == 'unknown' for d in role['dependencies'])
    assert role['dependencies'][-1]['status'] == 'false'
    assert assess_roles(item, [profile], {**CONTEXT, 'player_class': 'Sorceress'})[0]['status'] == 'failed'
