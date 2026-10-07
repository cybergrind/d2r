"""threats.json from the game's tables: the ranged attack's damage, casters, curses, auras."""

from inventory_tracking.terror.build_threats import build, table


def monstats(**columns):
    row = {'*hcIdx': '1', 'enabled': '1', 'killable': '1', 'npc': '', 'NameStr': 'key', 'BaseId': 'family'}
    return row | {name.replace('_H', '(H)'): str(value) for name, value in columns.items()}


def built(*rows, names=None):
    tables = {'monstats': list(rows), 'skills': [], 'monumod': []}
    return build(tables, names or {'key': 'Name'}, 'test')['monsters']


def test_a_melee_monster_counts_its_strongest_attack_and_its_elements_by_their_chance():
    row = monstats(A1MaxD_H=120, A2MaxD_H=150, El1Mode='A1', El1Type='cold', El1MaxD_H=80, El1Pct_H=50)

    assert built(row)['1'] == {
        'name': 'Name', 'family': 'family', 'physical': 1.5, 'elemental': 0.4, 'magic': 0.0, 'speed': 0,
    }  # fmt: skip


def test_a_monster_keeps_the_faster_of_its_walk_and_its_run():
    # Zombies: Velocity 1, Run 3. What a melee attacker needs to reach a player at all (danger.py).
    assert built(monstats(Velocity=1, Run=3))['1']['speed'] == 3
    assert built(monstats(Velocity=8, Run=7))['1']['speed'] == 8


def test_a_ranged_monster_counts_the_attack_that_fires_its_missile():
    # The Tainted: a melee bite (A1) and lightning from range (A2); a Gloam's lightning is a cast (SC).
    tainted = monstats(
        rangedtype=1, A1MaxD_H=100, MissA2='bighead1', El1Mode='A2', El1Type='ltng', El1MaxD_H=200, El1Pct_H=100
    )
    gloam = monstats(
        rangedtype=1, A1MaxD_H=115, MissC='bolt', El1Mode='SC', El1Type='ltng', El1MaxD_H=190, El1Pct_H=100
    )
    archer = monstats(rangedtype=1, A1MaxD_H=90, MissA1='cr_arrow1')

    assert [(m['physical'], m['elemental'], m['ranged']) for m in (built(tainted)['1'], built(gloam)['1'])] == [
        (0.0, 2.0, True),
        (0.0, 1.9, True),
    ]
    assert (built(archer)['1']['physical'], built(archer)['1']['elemental']) == (0.9, 0.0)


def test_a_caster_whose_damage_is_in_a_skill_counts_its_swing_as_magic_and_names_its_curses():
    knight = monstats(rangedtype=1, A1MaxD_H=135, Skill1='MonBoneSpirit', Skill2='Decrepify')

    assert built(knight)['1'] == {
        'name': 'Name', 'family': 'family', 'physical': 0.0, 'elemental': 0.0, 'magic': 1.35,
        'speed': 0, 'ranged': True, 'curses': ['Decrepify'],
    }  # fmt: skip


def test_poison_and_drains_are_not_burst_and_townsfolk_are_left_out():
    row = monstats(A1MaxD_H=100, El1Mode='A1', El1Type='pois', El1MaxD_H=300, El1Pct_H=100)

    assert built(row)['1']['elemental'] == 0.0
    assert built(monstats(npc=1), monstats(killable=''), {**monstats(), '*hcIdx': ''}) == {}


def test_auras_keep_their_range_and_monster_auras_their_plain_name():
    skills = [
        {'skill': 'Might', '*Id': '98', 'Param1': '16', 'Param2': '2'},
        {'skill': 'MonHolyShock', '*Id': '369', 'Param1': '6', 'Param2': '1'},
        {'skill': 'Vigor', '*Id': '115', 'Param1': '16', 'Param2': '3'},
    ]
    monumod = [{'id': '5', 'uniquemod': 'strong'}, {'id': '1', 'uniquemod': 'rndname'}]

    data = build({'monstats': [], 'skills': skills, 'monumod': monumod}, {}, 'test')

    assert data['auras'] == {'98': {'name': 'Might', 'range': [16, 2]}, '369': {'name': 'Holy Shock', 'range': [6, 1]}}
    assert data['modifiers'] == {'5': 'Extra Strong'}


def test_tables_are_tab_separated_with_a_header_row():
    assert table('Id\tNameStr\nfallen1\tFallen\n') == [{'Id': 'fallen1', 'NameStr': 'Fallen'}]


def test_skills_that_close_the_distance_or_double_the_swings_are_kept():
    horde = monstats(A1MaxD_H=110, Velocity=1, Run=5, Skill1='Self-resurrect', Skill2='Charge')
    lord = monstats(A1MaxD_H=150, Run=9, Skill1='BloodLordFrenzy')

    assert (built(horde)['1'].get('closes'), built(horde)['1'].get('frenzy')) == (True, None)
    assert (built(lord)['1'].get('closes'), built(lord)['1'].get('frenzy')) == (None, True)
