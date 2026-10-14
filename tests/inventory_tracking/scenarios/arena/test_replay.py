"""Moments of the first schema 4 take played again from the take alone (replay.py, records4.py), and how
near the arena comes to the recording (rca/2026-10-13/replay-readiness.md has the tables over 25 seeds).

What holds today is asserted. What does not is `xfail(strict=True)` with its cause: each turns into a
failure the day the arena holds the mechanism, and the mark is then taken off. The moments are staged from
the fixtures (`python -m tests.inventory_tracking.scenarios.arena.replay --cut` stages them again from the
takes under inventory_tracking/runs/combat, which are not checked in).

A moment's eight plays are made once (`play`, `rows`); the stall's, the fight's and the seal's tests are an
`xdist_group` each (`-n auto --dist loadgroup`, tests/inventory_tracking/conftest.py), so the three moments
run on three workers."""

import functools
import json
import statistics
from pathlib import Path

import pytest

from inventory_tracking.macros.runner import ATTACK, PICKUP, TELEPORT
from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.scenarios.arena import records4, replay
from tests.inventory_tracking.scenarios.arena.driver import Press
from tests.inventory_tracking.scenarios.arena.game import Arena
from tests.inventory_tracking.scenarios.arena.incident import Row


SEEDS = tuple(range(1, 9))
STALL, FIGHT, SEAL, DIABLO, RIVER = (moment.name for moment in replay.MOMENTS)
STOP = 'no Blade Warp or walk leads toward'
SAMPLE = replay.FIXTURES / 'records-sample.json'


def misses(reason: str):
    """A comparison the arena fails today, with its cause: strict, so the day it holds the mark comes off."""
    return pytest.mark.xfail(strict=True, reason=reason)


STALL_PLAYS = pytest.mark.xdist_group('replay: the stall')
FIGHT_PLAYS = pytest.mark.xdist_group('replay: the fight')
SEAL_PLAYS = pytest.mark.xdist_group('replay: the seal')


@functools.cache
def staging(name: str) -> replay.Staging:
    found = replay.stored(next(moment for moment in replay.MOMENTS if moment.name == name))
    assert found is not None, 'stage it: python -m tests.inventory_tracking.scenarios.arena.replay --cut'
    return found


@functools.cache
def play(name: str, seed: int, hands_given: bool = False) -> tuple[replay.Seen, tuple[tuple[float, str], ...]]:
    told, lines = replay.played(staging(name), seed, hands_given=hands_given)
    return told, tuple(lines)


def plays(name: str) -> list[replay.Seen]:
    return [play(name, seed)[0] for seed in SEEDS]


@functools.cache
def rows(name: str) -> dict[str, Row]:
    found = staging(name)
    return {row.what: row for row in replay.compare(found.truth, plays(name), found.moment.marks)}


def median_end(name: str, what: str) -> float | None:
    found = [told.ends[what] for told in plays(name) if told.ends[what] is not None]
    return statistics.median(found) if found else None


# -- the raw records decode (records4.py) -----------------------------------------------------------------


@functools.cache
def sample() -> dict:
    return json.loads(SAMPLE.read_text(encoding='utf-8'))


def test_a_seal_boss_is_named_by_its_monster_data() -> None:
    units = {key: records4.unit_of(row) for key, row in sample()['units'].items()}
    found = {units[f'boss/{row}'].txt: records4.SEAL_BOSSES[units[f'boss/{row}'].boss] for row in (36, 37, 38)}  # type: ignore[index]
    # Venom Lord, Oblivion Knight, Storm Caster: the types of the three seal bosses
    assert found == {362: 'Infector of Souls', 312: 'Lord De Seis', 306: 'Grand Vizier of Chaos'}
    assert all(
        units[f'boss/{row}'].flags == 0x0A for row in (36, 37, 38)
    )  # super unique and unique, as the frames have


def test_the_skill_in_use_and_the_animation_read_sensibly() -> None:
    units = {key: records4.unit_of(row) for key, row in sample()['units'].items()}
    assert all(unit.sound and unit.tick_valid and unit.tick_length == unit.length for unit in units.values())
    # skills.txt: 196 FingerMageSpider, 319 MegademonInferno, 335 DoomKnightMissile, 87 Decrepify, 388 Echoing
    # Strike, 390 Blade Warp (pricing/raw/game-excel); the levels are those the missiles of the take carry but
    # the character's (its skill record has the points put in, 1; the missiles' level is 13 and 15 by weapon set).
    assert (units['skill/306/196'].skill, units['skill/306/196'].skill_level) == (196, 12)
    assert (units['skill/362/319'].skill, units['skill/362/319'].skill_level) == (319, 15)
    assert (units['skill/312/335'].skill, units['skill/312/87'].skill) == (335, 87)
    assert (units['hero/388'].skill, units['hero/390'].skill) == (388, 390)
    # A Storm Caster's cast: 14 frames at a third of a frame a tick, 43 ticks (simulator-plan.md §4 counted 41
    # frames of the casting mode in the takes); the character's cast: 16 frames at 1.5 a tick.
    caster, hero = units['skill/306/196'], units['hero/388']
    assert round(caster.length / caster.speed) == 43
    assert (hero.length, round(hero.speed, 2)) == (16.0, 1.51)
    # the tick-true frame is a whole number of steps from the mode's start
    assert hero.tick_frame == pytest.approx(round(hero.tick_frame / hero.speed) * hero.speed)


def test_a_path_record_names_whom_the_monster_is_after() -> None:
    found = {who: records4.target_of(path) for _, path, who in sample()['paths']}
    assert found['none'] is None
    assert found['the character'] == (records4.PLAYER_TYPE, sample()['hero'])
    assert found['a companion'] is not None
    assert found['a companion'][0] == records4.MONSTER_TYPE


def test_a_missile_names_its_owner_its_skill_and_its_level() -> None:
    shots = {row['txt_id']: records4.shot_of(row) for row in sample()['missiles']}
    hero = sample()['hero']
    assert (shots[706].owner_type, shots[706].owner, shots[706].skill, shots[706].level) == (0, hero, 388, 13)
    assert (shots[177].owner_type, shots[177].skill, shots[177].level) == (1, 196, 11)  # a Storm Caster's lightning
    assert (shots[144].skill, shots[329].skill) == (319, 211)  # Inferno, a bone spirit
    assert shots[706].counter != shots[720].counter  # the blade and its detonation: not one cast's number


# -- the staging: what the take gives -----------------------------------------------------------------------


def test_the_character_is_the_takes_not_the_defaults() -> None:
    hero = staging(STALL).scene.hero
    # `w` [0, 69, True]: the staff in hand and empty; `f`: the ward down; `b`: two cells of the belt empty
    assert (hero.hand, hero.sets[1].teleport_charges, hero.ward, hero.hex_purge) == (1, 0, False, True)
    assert hero.belt.count(None) == 3
    assert len(hero.belt) == 16
    assert hero.sets[1].resist == {'physical': 0.9, 'fire': 0.46, 'lightning': 0.92, 'cold': 0.82}  # `r` 10/154/108/118
    assert not {'hand', 'belt', 'ward', 'hex_purge', 'consume'} & set(staging(STALL).scene.assumed)
    assert staging(RIVER).scene.hero.sets[1].teleport_charges == 2  # "Blade Warp toward Chaos Sanctum: 2 charges kept"


def test_the_presses_are_the_takes_requests() -> None:
    found = staging(STALL)
    assert [routine for _, routine in found.presses] == [TELEPORT] * 8 + [PICKUP, PICKUP]
    # the frame the scene is cut at is 6.99 s into the take: the take's requests at 7.01 and 10.25 s
    assert found.presses[0][0] == pytest.approx(0.02, abs=0.01)
    assert found.presses[8][0] == pytest.approx(3.26, abs=0.01)
    assert not found.attack_mode  # `state`: off until the pickup key's sweep turns it on
    fight = staging(FIGHT)
    assert fight.attack_mode
    assert fight.presses[0] == (0.0, ATTACK)
    assert fight.sweep == 11
    assert {routine for _, routine in fight.presses[1:]} == {PICKUP}


@pytest.mark.parametrize('name', [STALL, FIGHT, SEAL, DIABLO, RIVER])
def test_the_card_of_the_play_leads_with_the_mark_the_take_has(name: str) -> None:
    found = staging(name)
    arena = Arena(found.scene)
    made = replay.TakePlay(
        arena, [Press(0.0, TELEPORT)], 1.0, 1, found.marks, found.opened, found.bosses, dead_before=found.dead_before
    )
    target = made.card.target()
    assert target is not None
    assert found.card is not None
    area, label, kind, spot, use, _ = found.card
    assert (target.area, target.label, target.kind, list(target.point), target.use) == (area, label, kind, spot, use)


def test_the_seals_and_the_bosses_are_the_takes() -> None:
    found = staging(SEAL)
    assert found.bosses == [(3404433791, 'Grand Vizier of Chaos')]  # records.jsonl, monster data +0x2A = 38
    (pack,) = found.packs
    assert (pack.label, pack.delay, len(pack.mobs)) == ('Vizier seal 1', 0.99, 6)
    seals = {prop.txt: prop for prop in found.scene.things if prop.txt in (395, 396)}
    assert (seals[396].unit, seals[396].at, seals[396].mode) == (307542651, (7655.0, 5315.0), 0)
    spot = next(mark.spot for mark in found.marks if mark.label == 'Vizier seal 1')
    assert (spot[0] * TILE_UNITS, spot[1] * TILE_UNITS) == seals[396].at
    late = staging(DIABLO)
    assert late.dead_before == ['Grand Vizier of Chaos', 'Infector of Souls', 'Lord De Seis']
    assert len(late.opened) == 5
    assert [name for _, name in late.bosses] == ['Diablo']
    assert [round(at, 1) for at, _ in late.arrivals] == [2.3]  # he appears 2.3 s in, 12 units from the character


# -- the stall (a): the macro's decisions replay --------------------------------------------------------------


@STALL_PLAYS
def test_the_stall_replays_press_for_press() -> None:
    truth = staging(STALL).truth
    assert truth.said[STOP] == 8
    for seed in SEEDS:
        told, lines = play(STALL, seed)
        stops = [at for at, text in lines if STOP in text]
        assert len(stops) == 8, seed
        assert told.gone[:3] == [0.0, 0.0, 0.0], seed
        assert not [at for at in told.strikes if at < 3.2], seed
        on = [at for at, text in lines if 'Attack mode on' in text]
        assert on, seed
        assert on[0] == pytest.approx(3.3, abs=0.1), seed  # the pickup key's sweep; the take has it at 3.29


@STALL_PLAYS
def test_a_run_made_as_the_fakes_make_it_swaps_where_the_game_did_not() -> None:
    """The take has no swap in the stall: the staff stayed in hand, empty, until attack mode's "Main weapons
    for the fight" 4.4 s in. A run with `battle_hands` given (macros/fakes.py `Game.run`, kp4.py) swaps at the
    first press: the teleport step's `take_battle_weapons` works there and is a no-op in the game."""
    assert not any('Swap Weapons' in text for at, text in play(STALL, 1)[1] if at < 3.0)
    assert any('Swap Weapons' in text for at, text in play(STALL, 1, True)[1] if at < 3.0)


@STALL_PLAYS
@misses(
    "SIM-CASTERS (rca/2026-10-13/sim-casters.md): the casters' blows from the tables with no Psychic Ward"
    ' or Health Link share: least life 794 at the median, 1242 recorded'
)
def test_the_stall_costs_what_it_cost() -> None:
    assert rows(STALL)['least life'].inside  # 1,242 recorded
    assert rows(STALL)['life lost by 5 s'].inside


@STALL_PLAYS
@misses(
    'MODEL: a monster beyond 20 units goes for nobody (sim/monsters.py AWARE); in the take 8 of the '
    '38 beyond 20 units were walking at the character already (path target), 11 stood within 25 units'
    ' after 3 s, 7 in the arena'
)
def test_the_pack_closes_in_on_the_stalled_character() -> None:
    assert rows(STALL)['hostiles within 25 at 3 s'].inside


@STALL_PLAYS
@misses(
    'MODEL: the companions deal no damage (game.py); the mercenary and the Defiler killed two Doom '
    'Knights before the first strike'
)
def test_the_companions_kill_while_nothing_is_struck() -> None:
    assert rows(STALL)['kills by 4 s'].median >= 1


@STALL_PLAYS
@misses(
    "MODEL: with fewer monsters about it the arena's hunt first walks to a better place; the recorded"
    ' one struck where it stood (moved 11 units in 9 s, the arena 34)'
)
def test_attack_mode_strikes_from_where_the_stall_left_it() -> None:
    assert rows(STALL)['moved'].inside


# -- the fight (b) ---------------------------------------------------------------------------------------------


@FIGHT_PLAYS
def test_the_fight_begins_with_the_recorded_step() -> None:
    """With the sweep's steps of `state` the hunt's first move is the recording's: 16 units toward the pack."""
    assert rows(FIGHT)['from the start at 2 s'].median == pytest.approx(15.6, abs=1.5)


@FIGHT_PLAYS
def test_the_fight_kills_at_the_recorded_rate_once_it_stands() -> None:
    for mark, recorded in ((6, 17), (8, 20), (10, 23)):
        row = rows(FIGHT)[f'kills by {mark} s']
        assert row.recorded == recorded, mark
        assert abs(row.median - recorded) <= 0.25 * recorded, mark


@FIGHT_PLAYS
@misses(
    "MODEL: the arena's hunt strikes 6 times in the first 4 s where the recorded one struck twice: it"
    ' jumped by Blade Warp where the game walked (1.2 s), stayed where the game stepped on after one '
    'cast, and a cast costs it no Psychic Ward (0.5 s)'
)
def test_the_fight_strikes_as_often_as_recorded() -> None:
    assert rows(FIGHT)['strikes by 4 s'].inside


@FIGHT_PLAYS
@misses(
    'WARD (rca/2026-10-13/sim-casters.md section 9): with Psychic Ward played (sim/guard.py) the arena loses 39 by '
    '12 s against 159: 113 without the ward, 77 with its pool and no stun, 39 also when the cut opens with it down '
    '(the macro casts it at once). The stun of a striker that lands (72 frames, seen in the records) keeps the '
    "casters' swings and casts out of this fight more than the game's own did; the cause is not found"
)
def test_the_fight_costs_the_life_it_cost() -> None:
    assert rows(FIGHT)['life lost by 12 s'].median >= 0.5 * 159


@FIGHT_PLAYS
@misses(
    "MODEL and DECODE: nothing drops from a kill in the arena and the take's `g` is not played back: "
    'the two pickups of the stretch (an Amulet, a Flawless Amethyst) have nothing to go for'
)
def test_the_pickup_key_picks_up_what_dropped() -> None:
    assert rows(FIGHT)['said "Picking up"'].median >= 1


# -- the seal and its boss (c) ---------------------------------------------------------------------------------


# Unmarked 2026-10-13 (rca/2026-10-13/latency-findings.md, fix 2): with Blade Warp keyed when its delay ends
# instead of 1.05 s from the key's release and a look later, 3 of the 8 plays open the seal within 1.5 s of the
# recording (0 before: 15.1 to 19.4 s).
@SEAL_PLAYS
def test_the_seal_is_opened_and_its_pack_appears_a_second_later() -> None:
    opened = [told.ends['Vizier seal 1 opened'] for told in plays(SEAL)]
    assert sum(1 for at in opened if at is not None) >= len(SEEDS) - 1
    # The recording has it at 5.65 s. Over 25 seeds 14 plays open it at 6.1 to 7.1 s; in 10 the opening step is
    # late for the last press of the burst (5.34 s) and the seal waits for the next presses, 13 s in.
    assert sum(1 for at in opened if at is not None and at <= 5.65 + 1.5) >= 3
    for told in plays(SEAL):
        dead, at = told.ends['Grand Vizier of Chaos dead'], told.ends['Vizier seal 1 opened']
        if dead is not None:
            assert at is not None
            assert dead > at + 0.99


@SEAL_PLAYS
@misses(
    'OPEN LOOP: the presses are replayed at their recorded times; a play half a second behind the game '
    '(the hunt\'s own jump in its first instant; the seal not under the pointer from 24 units, "not '
    'clicked") has no press left for the opening and waits 8 s for the next burst: 14 of 25 plays open '
    'the seal within 1.5 s of the recording'
)
def test_the_seal_is_opened_when_it_was_in_nearly_every_play() -> None:
    opened = [told.ends['Vizier seal 1 opened'] for told in plays(SEAL)]
    assert sum(1 for at in opened if at is not None and at <= 5.65 + 1.5) >= 0.8 * len(SEEDS)


# Unmarked 2026-10-13 (fix 2, as above): 2.8 units from the recorded place at 3 s at the median (23.6 before).
@SEAL_PLAYS
def test_the_way_to_the_seal_is_the_recorded_one() -> None:
    """Three Blade Warps of 26 units: the arena is 5 units behind after 3 s (a jump of the hunt's own in its
    first instant, which the recorded hunt, under way, did not make)."""
    assert rows(SEAL)['apart from the recorded place at 3 s'].median <= 6.0
    assert rows(SEAL)['moved'].inside  # 227 units in 24 s


# Unmarked 2026-10-13 (fix 2, as above): 17.4 s at the median (21.9 before), 16.8 recorded.
@SEAL_PLAYS
def test_the_vizier_dies_about_when_he_died() -> None:
    assert median_end(SEAL, 'Grand Vizier of Chaos dead') == pytest.approx(16.8, abs=3.0)


@SEAL_PLAYS
def test_the_way_through_the_pack_costs_life() -> None:
    assert rows(SEAL)['life lost by 6 s'].median > 0


@SEAL_PLAYS
@misses(
    'MODEL: the fight after the seal is slower in the arena (23 kills by 12 s, 16 in the arena: the '
    'companions deal nothing, the hunt walks more), so the second seal is not reached within the '
    'window in most plays'
)
def test_the_second_seal_is_opened_within_the_window() -> None:
    reached = [told.ends['Vizier seal 2 opened'] for told in plays(SEAL)]
    assert sum(1 for at in reached if at is not None) > len(SEEDS) / 2


# -- Diablo -----------------------------------------------------------------------------------------------------


def test_diablo_is_struck_when_he_appears() -> None:
    assert median_end(DIABLO, 'first strike') == pytest.approx(2.7, abs=0.3)


@misses(
    "MODEL: Diablo has 146,250 points in the arena and loses 9% to two casts where the game's lost "
    "25% (Death Mark and Sigil: Lethargy change nothing in the arena; his points are the table's "
    "mean, not this game's); he dies 5.1 s after the first strike in the take and never within 6 s in"
    ' the arena'
)
def test_diablo_dies() -> None:
    assert any(told.ends['Diablo dead'] is not None for told in plays(DIABLO))


# -- hops and the way into the next level -------------------------------------------------------------------


def test_the_hops_end_where_the_recording_did() -> None:
    assert rows(RIVER)['apart from the recorded place at 4 s'].median <= 5.0  # three Blade Warps: 75 units
    assert rows(RIVER)['apart from the recorded place at 10.6 s'].median <= 5.0  # by the stairs
    # The recording spent the staff's last two charges on hops made while Blade Warp's delay ran. Since
    # 2026-10-13 (fix 2) a Blade Warp whose delay ends within PLAN_AHEAD (macros/travel.py) is the step, its key
    # held till the delay's end, and the two charges stay on the staff: the places above are kept all the same.
    assert all(told.said['=Macro: Teleport'] == 0 for told in plays(RIVER))


@misses(
    'MODEL: Blade Warp always casts: the game swallowed the key pressed while the character blocked '
    '(mode 9: "the character did not move", 1.6 s) and dropped the hop after it ("1164 ms too long '
    'after its key"); the arena is 80 units ahead at 6 s'
)
def test_the_refused_warp_holds_the_character_back() -> None:
    assert rows(RIVER)['apart from the recorded place at 6 s'].median <= 10.0


@misses(
    'MODEL: a scene is one level and has no way out of it (no stairs to click): "Walking into Chaos '
    'Sanctum" becomes eight stops'
)
def test_the_character_walks_into_the_next_level() -> None:
    assert all(told.said['Walking into'] >= 1 for told in plays(RIVER))


def test_the_fixtures_are_of_the_takes_named() -> None:
    assert Path(SAMPLE).exists()
    assert sample()['take'] == replay.TAKE
    assert {staging(name).scene.source['take'] for name in (STALL, FIGHT, SEAL, DIABLO)} == {replay.TAKE}  # type: ignore[index]
    assert staging(RIVER).scene.source['take'] == replay.RIVER  # type: ignore[index]
