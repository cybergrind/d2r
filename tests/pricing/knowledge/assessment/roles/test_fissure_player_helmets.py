from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.roles.test_fissure_pelts import facet
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def profile(key):
    result = next((r for r in build()['profiles'] if r['id'] == f'fissure-player-{key}'), None)
    assert result is not None
    return result


def helmet(word='Lore', base='Antlers', bonus=3):
    return replace(
        facts(base, 'normal', word),
        runeword=word,
        sockets=2 if word == 'Lore' else 3,
        socket_contents='filled',
        stats={'107:234': {'status': 'decoded', 'value': bonus}},
    )


def assess(item, key, player='Druid'):
    return assess_roles(item, [profile(key)], {'player_class': player})


@pytest.mark.parametrize('base', ['Antlers', 'Dream Spirit'])
def test_starter_lore_pelt_requires_documented_fissure_bonus(base):
    assert assess(helmet(base=base), 'starter-lore')[0]['status'] == 'matched'
    assert assess(helmet(base=base, bonus=2), 'starter-lore')[0]['status'] == 'failed'
    assert not assess(helmet(base='Cap'), 'starter-lore')


@pytest.mark.parametrize(('key', 'word'), [('starter-lore', 'Lore'), ('standard-flickering-flame', 'Flickering Flame')])
@pytest.mark.parametrize('change', ['unmade', 'sockets', 'empty', 'ethereal', 'class', 'magic'])
def test_player_runeword_roles_do_not_accept_preparation_candidates_or_wrong_context(key, word, change):
    item = helmet(word)
    if change == 'unmade':
        item = replace(item, runeword=None)
    elif change == 'sockets':
        item = replace(item, sockets=1)
    elif change == 'empty':
        item = replace(item, socket_contents='empty')
    elif change == 'ethereal':
        item = replace(item, ethereal=True)
    elif change == 'magic':
        item = replace(item, rarity='magic')
    result = assess(item, key, 'Sorceress' if change == 'class' else 'Druid')
    assert not result or result[0]['status'] in ('failed', 'partial')
    assert not result or result[0]['rule_trace']['truth'] != 'true'


@pytest.mark.parametrize('base', ['Antlers', 'Bone Visage', 'Diadem'])
def test_flickering_flame_alternative_does_not_invent_an_ideal_base_threshold(base):
    result = assess(helmet('Flickering Flame', base, bonus=0), 'standard-flickering-flame')[0]
    assert result['status'] == 'matched'
    assert not result['preferences']


def test_druid_cannot_use_a_barbarian_runeword_helmet():
    assert not assess(helmet('Flickering Flame', 'Jawbone Cap'), 'standard-flickering-flame')


def test_ravenlore_standard_and_ubers_keep_distinct_socket_requirements():
    item = facts('Sky Spirit', 'unique', 'Ravenlore')
    assert assess(item, 'standard-ravenlore')[0]['status'] == 'matched'
    assert assess(item, 'ubers-ravenlore')[0]['status'] == 'partial'
    prepared = replace(item, sockets=1, socket_contents='filled', socket_items=[facet()])
    assert assess(prepared, 'ubers-ravenlore')[0]['status'] == 'matched'
    cold = replace(prepared, socket_items=[facet(element='cold')])
    assert assess(cold, 'ubers-ravenlore')[0]['status'] == 'partial'
    assert assess(replace(item, ethereal=True), 'standard-ravenlore')[0]['status'] == 'failed'
    assert not assess(facts('Sky Spirit', 'unique', 'Other'), 'standard-ravenlore')
