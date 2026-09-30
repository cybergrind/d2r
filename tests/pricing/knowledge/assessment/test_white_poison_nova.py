from dataclasses import replace

import pytest

from pricing.knowledge.assessment.base_use import assess_runeword_base
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def white(sockets=2, nova=2):
    return replace(
        facts('Bone Wand', name='White'),
        runeword='White',
        sockets=sockets,
        socket_contents='filled',
        stats={'107:92': {'status': 'decoded', 'value': nova}},
    )


def test_white_poison_nova_uses_guide_threshold_not_perfect_planner_roll():
    role = next((r for r in build()['profiles'] if r['id'] == 'poison-nova-white-alternative'), None)
    assert role is not None

    def assess(item):
        return assess_roles(item, [role], {'player_class': 'Necromancer'})[0]

    assert assess(white(nova=2))['status'] == 'matched'
    assert assess(white(nova=3))['status'] == 'matched'
    assert assess(white(nova=1))['status'] == 'failed'
    assert assess(replace(white(), stats={}))['status'] == 'partial'
    assert assess(replace(white(), ethereal=True))['status'] == 'matched'
    assert assess(replace(white(), base_code=facts('Wand').base_code))['status'] == 'failed'
    assert assess(replace(white(), socket_contents='empty'))['status'] == 'failed'
    assert assess(white(sockets=1))['status'] == 'failed'
    assert not assess_roles(replace(white(), rarity='magic'), [role], {'player_class': 'Necromancer'})
    assert set(role['important_stats']) == {'107:92', '188:17', '105:0', '9:0', '35:0', '107:68'}


@pytest.mark.parametrize('nova', [None, 1, 2, 3])
def test_empty_white_base_explains_poison_nova_staffmod_target(nova):
    item = replace(white(), name='Bone Wand', runeword=None, socket_contents='empty')
    if nova is None:
        item = replace(item, stats={})
    else:
        item = replace(item, stats={'107:92': {'status': 'decoded', 'value': nova}})
    row = next(r for r in assess_runeword_base(item) if r['runeword'] == 'White')
    text = ' '.join(row['strengths'] + row['missing'])
    assert 'Poison Nova' in text
    if nova in (2, 3):
        assert any(f'+{nova} Poison Nova' in s for s in row['strengths'])
    else:
        assert any('+2' in s and 'Poison Nova' in s for s in row['missing'])
    assert row['status'] != 'perfect preferred base'
    assert any('poison-nova-necromancer' in s for s in row['sources'] if s)


@pytest.mark.parametrize(
    'base',
    [
        'Bone Wand',
        'Grim Wand',
        'Petrified Wand',
        'Tomb Wand',
        'Grave Wand',
        'Polished Wand',
        'Ghost Wand',
        'Lich Wand',
        'Unearthed Wand',
    ],
)
def test_poison_nova_base_advice_covers_each_legal_white_wand(base):
    item = replace(facts(base), sockets=2, stats={'107:92': {'status': 'decoded', 'value': 2}})
    rows = [r for r in assess_runeword_base(item) if r['runeword'] == 'White']
    assert len(rows) == 1
    assert any('+2 Poison Nova' in s for s in rows[0]['strengths'])
    assert rows[0]['status'] != 'perfect preferred base'
    blank = replace(item, sockets=0, item_level=50)
    preparation = next(r for r in assess_runeword_base(blank) if r['runeword'] == 'White')
    assert preparation['status'] == 'needs sockets'
    assert any('83.3%' in s for s in preparation['missing'])
    superior = next(r for r in assess_runeword_base(replace(blank, rarity='superior')) if r['runeword'] == 'White')
    assert not any('83.3%' in s for s in superior['missing'])


@pytest.mark.parametrize('base', ['Wand', 'Yew Wand', 'Burnt Wand'])
def test_one_socket_wands_never_receive_white_base_advice(base):
    item = replace(facts(base), stats={'107:92': {'status': 'decoded', 'value': 3}})
    assert not any(r['runeword'] == 'White' for r in assess_runeword_base(item))
