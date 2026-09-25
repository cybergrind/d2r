from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def profile(variant='standard'):
    row = next((r for r in build()['profiles'] if r['id'] == f'fissure-{variant}-pelt'), None)
    assert row is not None
    return row


def pelt(base='Dream Spirit', skills=None):
    values = {'188:42': 3, '107:234': 3} if skills is None else skills
    return replace(facts(base, 'magic'), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()})


def assess(item, variant='standard', player='Druid'):
    return assess_roles(item, [profile(variant)], {'player_class': player})


def facet(name='Rainbow Facet', element='fire'):
    keys = ('329:0', '333:0') if element == 'fire' else ('331:0', '335:0')
    return {
        'name': name,
        'item_type': 'jewl',
        'stats_complete': True,
        'stats': {k: {'status': 'decoded', 'value': 3} for k in keys},
    }


def prepared():
    return replace(
        pelt(),
        sockets=2,
        socket_contents='filled',
        socket_items=[
            {'name': "Defender's Fire", 'item_type': 'cjwl'},
            facet(),
        ],
    )


@pytest.mark.parametrize('variant', ['standard', 'magic-find'])
def test_core_pelt_combination_is_candidate_before_socket_preparation(variant):
    for base in ('Dream Spirit', 'Antlers'):
        role = assess(pelt(base), variant)[0]
        assert role['rule_trace']['truth'] == 'true'
        assert role['status'] == 'partial'
        assert any('socket' in m.lower() for m in role['missing'])
    assert assess(prepared(), variant)[0]['dependencies'][-1]['status'] == 'true'


@pytest.mark.parametrize('change', ['elemental', 'fissure', 'wrong-tab', 'ethereal', 'class', 'rare', 'circlet'])
def test_rejects_wrong_skill_combination_or_item(change):
    item = pelt()
    if change in ('elemental', 'fissure'):
        key = '188:42' if change == 'elemental' else '107:234'
        item = replace(item, stats={**item.stats, key: {'status': 'decoded', 'value': 2}})
    elif change == 'wrong-tab':
        item = pelt(skills={'188:41': 3, '107:234': 3})
    elif change == 'ethereal':
        item = replace(item, ethereal=True)
    elif change == 'rare':
        item = replace(item, rarity='rare')
    elif change == 'circlet':
        item = pelt('Diadem')
    result = assess(item, player='Sorceress' if change == 'class' else 'Druid')
    assert not result or result[0]['status'] == 'failed'


def test_unknown_skill_does_not_satisfy_required_bonus():
    item = replace(pelt(), stats={'188:42': {'status': 'decoded', 'value': 3}}, capture_complete=False)
    assert assess(item)[0]['rule_trace']['truth'] == 'unknown'


@pytest.mark.parametrize(
    'mode', ['cold', 'name-only', 'wrong-name', 'unknown-name', 'totals', 'one-socket', 'invalid-roll']
)
def test_fire_facet_must_be_verified_on_its_own_child(mode):
    item = prepared()
    if mode == 'cold':
        item = replace(item, socket_items=[item.socket_items[0], facet(element='cold')])
    elif mode == 'name-only':
        item = replace(item, socket_items=[item.socket_items[0], {'name': 'Rainbow Facet', 'item_type': 'jewl'}])
    elif mode == 'wrong-name':
        item = replace(item, socket_items=[item.socket_items[0], facet(name='Other Jewel')])
    elif mode == 'unknown-name':
        item = replace(item, socket_items=[item.socket_items[0], facet(name=None)])
    elif mode == 'invalid-roll':
        child = facet()
        child['stats']['329:0']['value'] = 6
        item = replace(item, socket_items=[item.socket_items[0], child])
    elif mode == 'totals':
        item = replace(item, socket_items=[item.socket_items[0]], stats={**item.stats, **facet()['stats']})
    else:
        item = replace(item, sockets=1)
    assert assess(item)[0]['dependencies'][-1]['status'] != 'true'


def test_standard_secondary_staffmods_are_preferences_not_core_requirements():
    item = pelt(skills={'188:42': 3, '107:234': 3, '107:250': 3, '107:247': 3})
    role = assess(item)[0]
    assert role['rule_trace']['truth'] == 'true'
    assert [p['status'] for p in role['preferences']] == ['true', 'true']
    assert [p['status'] for p in assess(pelt())[0]['preferences']] == ['false', 'false']
    assert assess(item, 'magic-find')[0]['preferences'] == []


def test_fire_facet_alone_does_not_prove_the_defender_jewel():
    item = replace(prepared(), socket_items=[facet(), facet()])
    role = assess(item)[0]
    assert any("Defender's Fire" in missing for missing in role['missing'])
