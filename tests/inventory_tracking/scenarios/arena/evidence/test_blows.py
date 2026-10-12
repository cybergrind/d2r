"""blows.py on takes made by hand (synthetic.py): each class of a drop from the least that makes it."""

from inventory_tracking.combat.hurts import COLD
from inventory_tracking.combat.sim.monsters import CHAMPION_FLAG, SUPER_FLAG, UNIQUE_FLAG
from inventory_tracking.macros.world import MINION_FLAG, NO_OWNER
from tests.inventory_tracking.scenarios.arena.evidence import blows
from tests.inventory_tracking.scenarios.arena.evidence.blows import (
    DEATH,
    DEATH_MISSILE,
    FOE,
    FRIEND,
    HERO,
    MISSILE,
    MONSTER_KIND,
    NOBODY,
    NONE,
    NOVA,
    OTHER,
    PLAYER_KIND,
    SEVERAL,
    SOLE_MELEE,
    SOLE_RANGED,
    SWING,
    UNKNOWN,
)
from tests.inventory_tracking.scenarios.arena.evidence.synthetic import (
    DEAD,
    HERO_UNIT,
    MELEE_TXT,
    NOVA_MISSILE,
    OWN_MISSILE,
    RANGED_TXT,
    STRIKE,
    aims,
    at_hero,
    born,
    flying,
    frame,
    monster,
    owner_record,
    take,
    target_record,
)


def only(rows):
    assert len(rows) == 1, rows
    return rows[0]


def test_a_swing_beside_the_character_is_a_sole_melee_blow():
    foe = monster(7, mode=STRIKE, flags=CHAMPION_FLAG)
    row = only(blows.blows(take([frame(0, 1000, [foe]), frame(1, 900, [foe])])))
    assert (row['class'], row['lost'], row['life'], row['frame'], row['dead']) == (SOLE_MELEE, 100, 900, 1, False)
    assert row['share'] == 0.1
    suspect = only(row['by'])
    assert (suspect['unit'], suspect['txt'], suspect['rank'], suspect['away'], suspect['via']) == (
        7, MELEE_TXT, blows.CHAMPION, 2.0, SWING,
    )  # fmt: skip
    assert suspect['aimed'] is None  # no path record in the take
    assert suspect['mods'] is None  # nor enchantments


def test_a_swing_from_afar_counts_only_with_the_character_as_its_target():
    far = monster(7, at=(108.0, 100.0), mode=STRIKE)
    frames = [frame(0, 1000, [far]), frame(1, 900, [far])]
    assert only(blows.blows(take(frames)))['class'] == NONE
    row = only(blows.blows(take(frames, paths=[at_hero(0, 7)])))
    assert row['class'] == SOLE_MELEE
    assert (row['by'][0]['away'], row['by'][0]['aimed']) == (8.0, 1)
    after_a_pet = take(frames, paths=[aims(0, (7, MONSTER_KIND, 99))])
    assert only(blows.blows(after_a_pet))['class'] == NONE


def test_one_idle_beside_the_character_is_no_suspect():
    foe = monster(7)
    row = only(blows.blows(take([frame(0, 1000, [foe]), frame(1, 900, [foe])])))
    assert (row['class'], row['by'], row['foes_near'], row['nearest_striking']) == (NONE, [], 1, None)


def test_a_missile_near_is_put_on_its_owner():
    archer = monster(8, RANGED_TXT, at=(115.0, 100.0))
    frames = [
        frame(0, 1000, [archer], [flying(50, NOVA_MISSILE, (102.0, 100.0))]),
        frame(1, 940, [archer]),
    ]
    row = only(blows.blows(take(frames, missiles=[born(0, 50, NOVA_MISSILE, 8)])))
    assert row['class'] == SOLE_RANGED
    suspect = only(row['by'])
    assert (suspect['unit'], suspect['via'], suspect['missile'], suspect['away']) == (8, MISSILE, NOVA_MISSILE, 15.0)
    assert row['missiles'] == [[NOVA_MISSILE, 2.0, 8, False]]


def test_the_shooter_striking_itself_is_one_suspect_and_another_striker_makes_several():
    archer = monster(8, RANGED_TXT, at=(110.0, 100.0), mode=STRIKE)
    arrow = flying(50, NOVA_MISSILE, (101.0, 100.0))
    first = [born(0, 50, NOVA_MISSILE, 8)]
    alone = take([frame(0, 1000, [archer], [arrow]), frame(1, 940, [archer])], paths=[at_hero(0, 8)], missiles=first)
    assert only(blows.blows(alone))['class'] == SOLE_RANGED
    brute = monster(7, mode=STRIKE)
    both = take([frame(0, 1000, [archer, brute], [arrow]), frame(1, 940, [archer, brute])], missiles=first)
    row = only(blows.blows(both))
    assert row['class'] == SEVERAL
    assert sorted((s['unit'], s['via']) for s in row['by']) == [(7, SWING), (8, MISSILE)]


def test_two_strikers_are_several():
    foes = [monster(7, mode=STRIKE), monster(9, at=(100.0, 103.0), mode=STRIKE)]
    row = only(blows.blows(take([frame(0, 1000, foes), frame(1, 900, foes)])))
    assert row['class'] == SEVERAL
    assert [s['unit'] for s in row['by']] == [7, 9]  # nearest first


def test_the_characters_own_and_a_companions_missiles_are_nobodys_blow():
    pet = monster(30, at=(101.0, 100.0), owner=HERO_UNIT)
    flights = [flying(50, NOVA_MISSILE, (101.0, 100.0)), flying(51, NOVA_MISSILE, (100.0, 101.0))]
    firsts = [born(0, 50, NOVA_MISSILE, HERO_UNIT, PLAYER_KIND), born(0, 51, NOVA_MISSILE, 30)]
    row = only(blows.blows(take([frame(0, 1000, [pet], flights), frame(1, 950, [pet])], missiles=firsts)))
    assert (row['class'], row['missiles']) == (NONE, [])


def test_a_missile_nobody_owns_leaves_the_drop_unknown_and_spoils_a_sole_blow():
    stray = flying(50, NOVA_MISSILE, (101.0, 100.0))
    frames = [frame(0, 1000, [], [stray]), frame(1, 950)]
    row = only(blows.blows(take(frames, missiles=[born(0, 50, NOVA_MISSILE, None)])))
    assert (row['class'], row['by']) == (NONE, [])
    assert row['missiles'] == [[NOVA_MISSILE, 1.0, None, False]]
    foe = monster(7, mode=STRIKE)
    frames = [frame(0, 1000, [foe], [stray]), frame(1, 950, [foe])]
    assert only(blows.blows(take(frames, missiles=[born(0, 50, NOVA_MISSILE, None)])))['class'] == SEVERAL


def test_a_missile_gone_by_the_next_frame_counts_from_further_off():
    archer = monster(8, RANGED_TXT, at=(115.0, 100.0))
    arrow = flying(50, NOVA_MISSILE, (105.0, 100.0))
    first = [born(0, 50, NOVA_MISSILE, 8)]
    ended = take([frame(0, 1000, [archer], [arrow]), frame(1, 940, [archer])], missiles=first)
    row = only(blows.blows(ended))
    assert (row['class'], row['missiles']) == (SOLE_RANGED, [[NOVA_MISSILE, 5.0, 8, True]])
    flying_on = take([frame(0, 1000, [archer], [arrow]), frame(1, 940, [archer], [arrow])], missiles=first)
    assert only(blows.blows(flying_on))['class'] == NONE


def test_the_missile_of_a_dead_monster_is_its_deaths():
    alive, corpse = monster(9, at=(106.0, 100.0)), monster(9, at=(106.0, 100.0), mode=DEAD)
    frames = [
        frame(0, 1000, [alive]),
        frame(1, 1000, [corpse], [flying(50, NOVA_MISSILE, (102.0, 100.0))]),
        frame(2, 820, [corpse]),
    ]
    row = only(blows.blows(take(frames, missiles=[born(1, 50, NOVA_MISSILE, 9)]), {9: [COLD]}))
    assert row['class'] == NOVA
    suspect = only(row['by'])
    assert (suspect['unit'], suspect['via'], suspect['missile'], suspect['away'], suspect['mods']) == (
        9, DEATH_MISSILE, NOVA_MISSILE, 6.0, [COLD],
    )  # fmt: skip


def test_a_death_nearby_is_blamed_only_when_the_dead_one_can_burst():
    alive, corpse = monster(9, at=(104.0, 100.0)), monster(9, at=(104.0, 100.0), mode=DEAD)
    frames = [frame(0, 1000, [alive]), frame(1, 1000, [corpse]), frame(2, 900, [corpse])]
    enchanted = only(blows.blows(take(frames), {9: [COLD]}))
    assert (enchanted['class'], enchanted['by'][0]['via'], enchanted['by'][0]['unit']) == (NOVA, DEATH, 9)
    plain = only(blows.blows(take(frames), {9: []}))
    assert (plain['class'], plain['by'], plain['death_near'], plain['death_control']) == (NONE, [], True, False)
    assert blows.can_burst(MELEE_TXT, None) is False
    assert all(blows.can_burst(txt, None) for txt in blows.exploding())


def test_a_monster_raised_again_is_alive_and_its_missile_a_shot():
    alive, corpse = monster(9, at=(106.0, 100.0)), monster(9, at=(106.0, 100.0), mode=DEAD)
    frames = [
        frame(0, 1000, [alive]),
        frame(1, 1000, [corpse]),
        frame(2, 1000, [alive], [flying(50, NOVA_MISSILE, (102.0, 100.0))]),
        frame(3, 900, [alive]),
    ]
    row = only(blows.blows(take(frames, missiles=[born(2, 50, NOVA_MISSILE, 9)])))
    assert (row['class'], row['by'][0]['via']) == (SOLE_RANGED, MISSILE)


def test_a_drop_is_counted_across_an_unread_frame_and_a_fall_of_the_most_life_is_none():
    foe = monster(7, mode=STRIKE)
    across = take([frame(0, 1000, [foe]), frame(1, None, [foe]), frame(2, 880, [foe])])
    row = only(blows.blows(across))
    assert (row['lost'], row['frame'], row['class'], row['gap']) == (120, 2, SOLE_MELEE, 0.08)
    # Consume ending (hurts.lost): 1818 of 1818 to 1580 of 1580 is no blow.
    assert blows.blows(take([frame(0, 1818, most=1818), frame(1, 1580, most=1580)])) == []
    assert blows.blows(take([frame(0, 1000), frame(1, 997)])) == []  # under hurts.HURT_LEAST


def test_over_a_pause_of_the_recorder_nobody_is_blamed():
    foe = monster(7, mode=STRIKE)
    row = only(blows.blows(take([frame(0, 1000, [foe]), frame(40, 800, [foe])])))
    assert (row['class'], row['by'], row['gap']) == (NONE, [], 1.6)


def test_a_death_and_schema_1():
    foe = monster(7, mode=STRIKE)
    row = only(blows.blows(take([frame(0, 300, [foe]), frame(1, 0, [foe])])))
    assert (row['dead'], row['lost'], row['class']) == (True, 300, SOLE_MELEE)
    assert blows.blows(take([frame(0, 1000, [foe]), frame(1, 900, [foe])], schema=1)) == []


def test_level_tier_and_enchantments_come_from_the_units_file():
    foe = monster(7, mode=STRIKE, flags=UNIQUE_FLAG)
    units = [{'unit': 7, 'txt': MELEE_TXT, 'stats': {'12': 88, '367': 2}, 'mods': [5, COLD]}]
    row = only(blows.blows(take([frame(0, 1000, [foe]), frame(1, 900, [foe])], units=units)))
    suspect = row['by'][0]
    assert (suspect['level'], suspect['tier'], suspect['mods'], suspect['rank']) == (88, 2, [5, COLD], blows.UNIQUE)


def test_rank_of():
    assert blows.rank_of(0) == blows.PLAIN
    assert blows.rank_of(MINION_FLAG | UNIQUE_FLAG) == blows.MINION
    assert blows.rank_of(SUPER_FLAG | UNIQUE_FLAG) == blows.SUPER
    assert blows.rank_of(CHAMPION_FLAG) == blows.CHAMPION
    assert blows.rank_of(UNIQUE_FLAG) == blows.UNIQUE


def test_records_are_read_at_their_offsets():
    assert blows.owner_of(owner_record(MONSTER_KIND, 77)) == (MONSTER_KIND, 77)
    assert blows.owner_of('00' * 40) is None  # a trimmed take keeps no record
    assert blows.target_of(target_record(PLAYER_KIND, HERO_UNIT)) == (PLAYER_KIND, HERO_UNIT)
    assert blows.target_of('') is None


def test_walk_sorts_out_a_frame():
    pet = monster(30, at=(101.0, 100.0), owner=HERO_UNIT)
    ally = monster(31, at=(99.0, 100.0), ally=1)
    foes = [monster(7), monster(8), monster(9), monster(10, mode=DEAD)]
    flights = [flying(50, NOVA_MISSILE, (103.0, 104.0)), flying(51, OWN_MISSILE, (100.0, 101.0)), [52, 1, 0, 0, 0, '']]
    paths = [aims(0, (7, PLAYER_KIND, HERO_UNIT), (8, MONSTER_KIND, 30), (9, PLAYER_KIND, 0), (10, MONSTER_KIND, 555))]
    firsts = [born(0, 50, NOVA_MISSILE, 7), born(0, 51, OWN_MISSILE, HERO_UNIT, PLAYER_KIND)]
    found = take([frame(0, 1000, [pet, ally, *foes], flights)], paths=paths, missiles=firsts)
    moment = only(list(blows.walk(found)))
    assert [m.unit for m in moment.friends] == [30, 31]
    assert [m.unit for m in moment.foes] == [7, 8, 9]
    assert [m.unit for m in moment.fallen] == [10]
    assert moment.aims == {7: HERO, 8: FRIEND, 9: NOBODY}
    assert blows.companions(found) == {30, 31}
    arrow, blade = moment.flying  # the row without a path record is passed over
    assert (arrow.kind, arrow.owner, arrow.at, arrow.hostile) == (FOE, 7, (103.0, 104.0), True)
    assert (blade.kind, blade.hostile) == (HERO, False)
    assert moment.read
    assert OTHER not in moment.aims.values()  # the dead one's record is not kept among the live


def test_a_missile_without_a_first_sight_is_the_characters_when_its_type_always_is():
    frames = [
        frame(0, 1000, [], [flying(50, NOVA_MISSILE, (101.0, 100.0)), flying(60, NOVA_MISSILE, (101.0, 101.0))]),
        frame(1, 1000, [], [flying(60, NOVA_MISSILE, (102.0, 101.0))]),
    ]
    mine = take(frames, missiles=[born(0, 50, NOVA_MISSILE, HERO_UNIT, PLAYER_KIND)])
    first, second = list(blows.walk(mine))
    assert [flight.kind for flight in first.flying] == [HERO, HERO]
    assert first.flying[1].key == second.flying[0].key  # one missile over two frames
    mixed = take(frames, missiles=[born(0, 50, NOVA_MISSILE, 99)])  # an owner the frames never held
    assert [flight.kind for flight in next(iter(blows.walk(mixed))).flying] == [UNKNOWN, UNKNOWN]


def test_deaths_are_the_last_live_rows():
    alive, corpse = monster(9, at=(106.0, 100.0)), monster(9, at=(107.0, 100.0), mode=DEAD)
    moments = list(blows.walk(take([frame(0, 1000, [alive]), frame(1, 1000, [corpse]), frame(2, 1000, [corpse])])))
    ((index, row),) = blows.deaths(moments)
    assert (index, row.unit, row.at) == (1, 9, (106.0, 100.0))
    assert row.owner == NO_OWNER
