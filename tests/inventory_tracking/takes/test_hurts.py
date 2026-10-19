"""What took the character's life: the suspects of a drop (takes/hurts.py)."""

import json
from types import SimpleNamespace

from inventory_tracking.takes.hurts import (
    BESIDE,
    HURT_LEAST,
    Foe,
    beside,
    enchantments,
    hurts,
    lost,
    missile_point,
    rank,
    report,
    sightings,
    sole,
    suspects,
    target_unit,
)


ME, NOBODY = 1, 0xFFFFFFFF
HERE = (5000.0, 5000.0)
WALK, ATTACK = 2, 4


def foe(unit, away, mode=ATTACK, target=ME, flags=0, mods=()):
    return Foe(unit, 55, flags, mode, HERE[0] + away, HERE[1], target, mods)


def test_a_suspect_strikes_or_is_aimed_at_the_character_within_reach_or_stands_beside_it():
    found = suspects(
        ME,
        HERE,
        [
            foe(1, 8.0),  # swinging 8 units off, at the character
            foe(2, 8.0, target=77),  # swinging at another: a suspect all the same (its record may be stale)
            foe(3, 9.0, WALK),  # on its way to the character
            foe(4, 9.0, WALK, target=77),  # on its way to another: none
            foe(5, 3.0, WALK, target=77),  # beside the character, whatever it does
            foe(6, 14.0),  # too far
            foe(7, 6.0, WALK, target=None),  # no path record: nothing says it is after the character
        ],
    )
    assert [(row[0], row[4], row[5]) for row in found] == [(5, 3.0, 0), (1, 8.0, 1), (2, 8.0, 0), (3, 9.0, 1)]


def test_of_the_frames_around_a_drop_the_swing_is_kept_over_the_step():
    before, after = foe(1, 3.6, WALK, mods=(28, 17)), foe(1, 3.2, ATTACK, mods=(28, 17))
    assert suspects(ME, HERE, [before, after]) == [[1, 55, 0, ATTACK, 3.2, 1, [28, 17]]]
    assert suspects(ME, HERE, [after, before]) == [[1, 55, 0, ATTACK, 3.2, 1, [28, 17]]]
    # Enchantments that are not known stay unknown; none is an empty list.
    assert suspects(ME, HERE, [Foe(2, 55, 0, ATTACK, HERE[0], HERE[1])])[0][5:] == [None, None]


def test_the_missiles_beside_the_character_that_can_hurt_are_listed():
    # 195 a spark, 194 a cold nova; 706 its own blade, 18 blood and 686 its sigil's mark take nothing off it.
    flying = [(195, (5002.0, 5000.0)), (706, (5001.0, 5000.0)), (194, (5000.0, 5001.0)), (195, (5008.0, 5000.0))]
    flying += [(18, (5000.5, 5000.0)), (686, (5000.0, 5000.5))]
    assert beside(HERE, flying) == [[194, 1.0], [195, 2.0]]


def test_a_path_record_names_the_target_and_a_missiles_head_its_place():
    record = bytes(0x7C) + (4265411866).to_bytes(4, 'little') + bytes(16)
    assert target_unit(record) == 4265411866
    assert target_unit(record[:0x40]) is None
    assert missile_point('00801c310040702b') == (12572.5, 11120.25)


def test_a_blow_is_put_on_a_monster_only_when_it_alone_was_striking_and_nothing_flew_by():
    alone = {'by': [[1, 55, 16, ATTACK, 3.2, 1, [17]], [2, 55, 16, WALK, 4.0, 1, [17]]], 'near': []}
    assert sole(alone) == alone['by'][0]
    assert sole({**alone, 'near': [[195, 1.0]]}) is None  # a spark flew by
    two = [*alone['by'], [3, 55, 8, ATTACK, 8.0, 1, [17]]]
    assert sole({'by': two, 'near': []}) is None
    # Further off, a swing counts when the character is its target (a swing lands from further than it looks).
    assert sole({'by': [[3, 55, 8, ATTACK, BESIDE + 3, 0, [17]]], 'near': []}) is None
    assert sole({'by': [[3, 55, 8, ATTACK, BESIDE + 3, 1, [17]]], 'near': []}) is not None
    assert [rank(flags) for flags in (0, 0x10, 0x08, 0x04, 0x0A)] == ['plain', 'minion', 'leader', 'leader', 'leader']


def frame(n, life, monsters, missiles=()):
    character = [ME, 1, 25, *HERE, 0, 388, life, 1783, 500, 500]
    return {'t': n * 0.04, 'n': n, 'p': character, 'm': monsters, 'x': missiles}


def take():
    herald = [7, 55, ATTACK, 5008.0, 5000.0, 92, 128, 0x08, NOBODY, 0]
    minion = [8, 55, WALK, 5003.0, 5000.0, 10, 128, 0x10, NOBODY, 0]
    pet = [9, 361, ATTACK, 5001.0, 5000.0, 100, 128, 0, ME, 1]
    corpse = [10, 55, 12, 5001.0, 5000.0, 0, 128, 0, NOBODY, 0]
    east, south = (5002).to_bytes(2, 'little').hex(), (5000).to_bytes(2, 'little').hex()
    spark = [50, 195, 3, 0, 0, f'0080{east}0080{south}']
    aimed = (bytes(0x7C) + ME.to_bytes(4, 'little')).hex()
    return SimpleNamespace(
        frames=[
            frame(1, 1500, [herald, minion, pet, corpse]),
            frame(2, 1498, [herald, minion, pet, corpse]),  # two points: not a blow
            frame(3, 1290, [herald, minion, pet, corpse], [spark]),
            frame(4, 1300, [herald, minion, pet, corpse], [spark]),  # a potion: no drop
            frame(5, 0, [herald, minion, pet, corpse]),
        ],
        units=[{'unit': 7, 'txt': 55, 'mods': [30, 28, 17]}, {'unit': 8, 'txt': 55}],
        paths=[{'t': 0.04, 'n': 1, 'm': [[7, aimed]]}],
    )


def test_the_drops_of_a_take_are_read_with_the_suspects_of_the_two_frames_around_each():
    rows = hurts(take(), {8: (28, 17), 7: (1,)})
    drops = [(row['t'], row['lost'], row['life'], row['dead']) for row in rows]
    assert drops == [(0.12, 208, 1290, False), (0.2, 1300, 0, True)]
    # The Herald by its path record and its swing; the minion beside the character, with no record. The
    # take's own enchantments count before the ones handed in; the pet and the corpse are no suspects.
    assert rows[0]['by'] == [[8, 55, 0x10, WALK, 3.0, None, [28, 17]], [7, 55, 0x08, ATTACK, 8.0, 1, [30, 28, 17]]]
    assert rows[0]['near'] == []  # the spark came with the frame of the drop: it was not there before
    assert rows[1]['near'] == [[195, 2.5]]
    # The first drop is the Herald's alone (the minion was walking); at the second a spark was by.
    assert report(rows).splitlines()[::2] == [
        '2 drops, 1 deaths, 1 with one monster striking alone',
        'leader lightning enchanted            1    208    208    208',
    ]


def test_enchantments_of_an_older_take_come_from_the_probe_log_of_the_same_game(tmp_path):
    def seen(unit, txt, clock, mods):
        data = bytearray(0x58)
        data[0x20 : 0x20 + len(mods)] = bytes(mods)
        return json.dumps({'event': 'seen', 't': clock, 'unit_id': unit, 'txt_id': txt, 'data_hex': data.hex()})

    log = tmp_path / 'terror-probe.jsonl'
    rows = [seen(7, 55, 100.0, (30, 28, 17)), seen(7, 55, 9000.0, (5,)), seen(8, 21, 100.0, (9,))]
    rows += [seen(9, 55, 100.0, ()), json.dumps({'event': 'gone', 'unit_id': 7})]
    log.write_text('\n'.join(rows) + '\n')
    found = sightings([log])
    units = [{'unit': 7, 'txt': 55}, {'unit': 8, 'txt': 55}, {'unit': 9, 'txt': 55}]
    old = SimpleNamespace(frames=[{'t': 130.0}], units=units)
    # Unit 7 of this game, not the one that got its id two hours on; unit 8 was another type; 9 has none.
    assert enchantments(found, old) == {7: (30, 28, 17), 9: ()}


def test_life_that_goes_with_the_most_it_can_be_is_no_blow():
    # Consume ends (1818 -> 1580), the weapons are swapped (1818 -> 1783): the life follows, nothing struck.
    assert lost(1818, 1818, 1580, 1580) == 0
    assert lost(1612, 1783, 1392, 1540) == 0  # in proportion, as the take of Cave Level 1 has it
    assert lost(1700, 1818, 1700, 1783) < HURT_LEAST
    assert lost(1612, 1783, 1292, 1540) == 100  # a blow in the same frame is still one
    assert lost(1500, 1783, 1290, 1783) == 210
    assert lost(1500, 1580, 1290, 1818) == 210  # a buff coming on hides nothing
    assert lost(1051, 1783, 0, 1540) == 1051  # a death ends the buffs: the whole life was the blow's
