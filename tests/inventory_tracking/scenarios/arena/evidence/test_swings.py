"""swings.py on takes made by hand (synthetic.py): how a swing's end is told, what a fall of a monster's
life is followed by, and what a set of tallies measures."""

import json

import pytest

from tests.inventory_tracking.scenarios.arena.evidence import blows, scan, swings
from tests.inventory_tracking.scenarios.arena.evidence.blows import HERO, SOLE_MELEE
from tests.inventory_tracking.scenarios.arena.evidence.swings import DEAD, DIED, RAN_OUT, STAGGERED, UNSEEN
from tests.inventory_tracking.scenarios.arena.evidence.synthetic import (
    DEAD as LYING,
    IDLE,
    MELEE_TXT,
    STRIKE,
    at_hero,
    frame,
    monster,
    take,
    write,
)


# A mode that is neither an attack nor the one a monster stands in: here the one it staggers in. Which mode
# that is in the game is not typed in anywhere: swings.py finds it as the mode entered with a fall of life.
REELING = IDLE + 1
assert REELING not in swings.ATTACK_MODES
assert REELING != LYING
FULL = 128


def foe(unit: int, mode: int, life: int = FULL, at=(102.0, 100.0)) -> list:
    row = monster(unit, at=at, mode=mode)
    row[5] = life
    return row


def tallied(found):
    moments = list(blows.walk(found))
    return swings.tally(found.directory.name, moments, blows.blows(found, None, moments))


def fight(name='20261011T120000Z-25'):
    """Three monsters two units from a character that stands still, thirty frames:

    - 7 swings through frames 2 to 9 and takes 100 points at frame 8, stands five frames, swings again
      through 15 to 22 and takes nothing;
    - 8 swings from frame 4, loses a quarter of its life at frame 7 and reels through 7 to 10;
    - 9 swings from frame 20 and lies dead at frame 23.

    Monster 7 stands alone at its first swing's drop as far as blows.py goes: 8 reels by then."""
    frames = []
    for index in range(30):
        first = foe(7, STRIKE if 2 <= index <= 9 or 15 <= index <= 22 else IDLE)
        if 4 <= index <= 6:
            second = foe(8, STRIKE, at=(100.0, 102.0))
        elif 7 <= index <= 10:
            second = foe(8, REELING, FULL - 32, at=(100.0, 102.0))
        else:
            second = foe(8, IDLE, FULL if index < 7 else FULL - 32, at=(100.0, 102.0))
        if index < 20:
            third = foe(9, IDLE, at=(98.0, 100.0))
        elif index < 23:
            third = foe(9, STRIKE, at=(98.0, 100.0))
        else:
            third = foe(9, LYING, 0, at=(98.0, 100.0))
        frames.append(frame(index, 900 if index >= 8 else 1000, [first, second, third]))
    return take(frames, paths=[at_hero(0, 7, 8, 9)], name=name)


def run_of(found, unit, nth=0):
    return [run for run in found['runs'] if run['unit'] == unit][nth]


def test_a_run_is_told_by_the_frame_after_it():
    found = tallied(fight())
    first, again = run_of(found, 7), run_of(found, 7, 1)
    assert (first['txt'], first['mode'], first['frames'], first['away'], first['aim']) == (
        MELEE_TXT,
        STRIKE,
        8,
        2.0,
        HERO,
    )
    assert (first['then'], first['struck'], first['begun'], first['moved'], first['crowd']) == (IDLE, 0, 1, 0.0, 3)
    assert first['drops'] == [[6, SOLE_MELEE, 1, 1]]  # six frames into the run, its own, nobody else's
    assert (first['rest'], first['next_away']) == (5, 2.0)
    assert (again['then'], again['drops'], again['rest']) == (IDLE, [], None)
    reeled = run_of(found, 8)
    assert (reeled['frames'], reeled['then'], reeled['struck']) == (3, REELING, 1)
    killed = run_of(found, 9)
    assert (killed['frames'], killed['then']) == (3, DEAD)


def test_a_fall_of_life_is_tallied_with_what_followed_it():
    found = tallied(fight())
    # A quarter of the life (4 of 16 parts, the last band), from the attack mode into the reeling one, in reach.
    assert found['falls'] == {f'4|{STRIKE}|{REELING}|1': 1}
    assert found['entered'][f'{REELING}|1'] == 1
    assert found['entered'][f'{STRIKE}|0'] == 4
    assert found['spells'][f'{REELING}|4'] == 1
    assert found['deaths'] == 1
    assert found['near'] == 30 + 30 + 23  # frames alive within reach


def test_the_mode_of_a_struck_monster_is_found_not_given():
    found = swings.measure([tallied(fight())])
    assert found['recovery'] == {'mode': REELING, 'entered': 1, 'with_fall': 1}
    assert swings.recovery_of([]) == {'mode': None, 'entered': 0, 'with_fall': 0}
    assert [swings.end_of({'then': then}, REELING) for then in (IDLE, REELING, DEAD, None, STRIKE)] == [
        RAN_OUT,
        STAGGERED,
        DIED,
        UNSEEN,
        RAN_OUT,
    ]


def test_the_swings_are_measured_by_how_they_ended():
    found = swings.measure([tallied(fight())])
    assert found['runs'] == 4
    assert {end: row['n'] for end, row in found['ends'].items()} == {RAN_OUT: 2, STAGGERED: 1, DIED: 1, UNSEEN: 0}
    assert found['ends'][STAGGERED]['struck'] == 1
    # Of the two that ran out one took life, and it was put on that monster alone: both bounds a half.
    assert found['ran_out']['stood'] == {'n': 2, 'low': 0.5, 'high': 0.5, 'value': 0.5}
    assert found['ran_out']['alone']['n'] == 0  # three hostiles beside the character
    assert found['ran_out']['frames'] == 8
    assert found['blow'] == {'n': 1, 'share': 0.625, 'p10': 0.625, 'p90': 0.625}  # shown at frame 6 of 8: landed by 5
    assert (found['rest']['n'], found['rest']['p50'], found['rest']['longer']) == (1, 5, 0)
    assert found['rest']['knots'] == [5] * 11
    assert found['after_stagger'] == {'n': 0, 'p50': None}  # the monster that reeled did not swing again
    last = found['stagger']['bands'][-1]
    assert (last['from'], last['n'], last['staggered'], last['chance']) == (4, 1, 1, 1.0)
    assert found['stagger']['recovery'] == {'n': 1, 'p50': 4, 'knots': [4] * 11}
    assert found['struck'] == {'seconds': pytest.approx(83 / 25, abs=0.05), 'falls': [0, 0, 0, 0, 1], 'deaths': 1}
    assert found['types'][str(MELEE_TXT)]['runs'] == 4


def test_a_swing_at_a_character_that_left_is_not_one_it_stood_through():
    frames = []
    for index in range(12):
        here = (100.0, 100.0) if index < 5 else (100.0, 103.0)
        frames.append(frame(index, 1000, [foe(7, STRIKE if 2 <= index <= 8 else IDLE)], at=here))
    found = swings.measure([tallied(take(frames, paths=[at_hero(0, 7)]))])
    assert found['ran_out']['all']['n'] == 1
    assert found['ran_out']['stood']['n'] == 0


def test_a_chance_is_the_middle_of_the_drops_alone_and_the_drops_shared():
    runs = [
        {'drops': [[5, SOLE_MELEE, 1, 1]]},
        {'drops': [[5, 'several', 3, 1]]},
        {'drops': [[5, 'several', 3, 0]]},  # a drop in its frames that does not name it
        {'drops': []},
    ]
    assert swings.chance(runs) == {'n': 4, 'low': 0.25, 'high': 0.5, 'value': 0.375}
    assert swings.chance([]) == {'n': 0, 'low': None, 'high': None, 'value': None}


def test_the_command_writes_both_files_from_the_takes_of_the_split(tmp_path):
    root, out = tmp_path / 'takes', tmp_path / 'out'
    out.mkdir()
    names = ['20261011T120000Z-25', '20261011T120100Z-25', '20261011T120200Z-25', '20261011T120300Z-25']
    for name in names:
        write(fight(name), root)
    split = {half: [name for name in names if scan.half(name) == half] for half in (scan.TRAIN, scan.CHECK)}
    assert split[scan.TRAIN]
    assert split[scan.CHECK]
    (out / 'split.json').write_text(json.dumps(split))
    args = ['--root', str(root), '--out', str(out), '--split', str(out / 'split.json'), '--jobs', '1']
    assert swings.main(args) == 0
    found = json.loads((out / 'swings.json').read_text())
    assert found[scan.TRAIN]['takes'] == len(split[scan.TRAIN])
    assert found[scan.CHECK]['ends'][RAN_OUT]['n'] == 2 * len(split[scan.CHECK])
    text = (out / 'SWINGS.md').read_text()
    assert f'Mode {REELING} is the mode most often entered' in text
    assert '| ran out |' in text
    before = text
    assert swings.main([*args, '--render']) == 0
    assert (out / 'SWINGS.md').read_text() == before
