"""The merc lost, or the belt low on healing potions: a town trip at the first safe moment (macros/merc.py). The
player, 2026-10-21 ~19:00: "also, we have lost merc -> probably better retreat to the town and refill hp potions in the
belt" (rca/2026-10-21/merc-lost-findings.md)."""

import json
import logging
from dataclasses import replace

import pytest

from inventory_tracking.game.layout import CHAMPION_FLAG
from inventory_tracking.game.records import Monster
from inventory_tracking.macros import merc
from inventory_tracking.macros.agenda import RESUME, STACK, THROUGH_PORTAL, TOWN_ROUTINE, Objective, room_package
from inventory_tracking.native.layout import DEAD_MODES
from tests.inventory_tracking.macros.fakes import player, world


ME = player(128).unit_id
MERC = Monster(377627261, 338, 1, 5002.0, 5000.0, ME, ally=True)
CORPSE = replace(MERC, mode=12)
SUPER_HEALING, FULL_REJUVENATION = 606, 531
FULL_BELT = (SUPER_HEALING, SUPER_HEALING, FULL_REJUVENATION, FULL_REJUVENATION) * 4
NO_HEALING = (None, None, FULL_REJUVENATION, FULL_REJUVENATION) + (None,) * 12


def foe(unit: int, at: float = 5005.0, **changes) -> Monster:
    return replace(Monster(unit, 638, 1, at, 5000.0), **changes)


def look(*monsters: Monster, dead: frozenset[int] = frozenset(), area: int = 128, game: str = 'cyber32'):
    return world(area, monsters=monsters, dead=dead, game_name=game, player=player(area))


def watch_with_merc(now: float = 0.0) -> merc.MercWatch:
    watch = merc.MercWatch()
    assert watch.see(look(MERC), FULL_BELT, now, 95) is None
    return watch


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    monkeypatch.setattr(merc, 'LEVELS', {})
    monkeypatch.setattr(merc, 'UNREVIVED', set())
    monkeypatch.setattr(merc, 'NO_POTIONS', set())


def test_the_revive_costs_fifteen_halves_of_the_level_squared_at_most_fifty_thousand():
    # hireling.txt resurrectcostmultiplier 15, resurrectcostdivisor 2, resurrectcostmax 50000 (D2MOO Monsters.cpp)
    assert merc.revive_cost(30) == 6750
    assert merc.revive_cost(95) == 50_000  # the player's merc on 2026-10-21
    assert merc.revive_cost(None) == merc.COST_MOST  # unread: the most it can cost


def test_the_corpse_held_three_seconds_makes_the_merc_trip_due():
    # 18:55:54 on 2026-10-21: mode 0, then 12, its unit in the unit table to the take's end (World.dead)
    watch = watch_with_merc()
    assert watch.see(look(dead=frozenset({MERC.unit_id})), FULL_BELT, 2.0) is None
    assert watch.see(look(dead=frozenset({MERC.unit_id})), FULL_BELT, 4.0) is None  # 2 s: under CORPSE_HOLD
    assert watch.see(look(dead=frozenset({MERC.unit_id})), FULL_BELT, 5.0) == merc.WHY_MERC
    assert merc.LEVELS == {'CybergrindAA': 95}


def test_one_missed_sample_makes_no_trip():
    # osd.log at 18:53:00, 18:53:05, 18:53:37 on 2026-10-21: one "Mercenary sample: None", then the merc 0.2 s later
    watch = watch_with_merc()
    for now in range(2, 60, 2):
        seen = look() if now % 10 == 0 else look(MERC)  # a look with no merc now and then, never two in a row
        assert watch.see(seen, FULL_BELT, float(now)) is None


def test_no_merc_read_at_all_is_lost_only_after_the_absence_hold():
    watch = watch_with_merc()
    assert watch.see(look(), FULL_BELT, 2.0) is None
    assert watch.see(look(), FULL_BELT, 2.0 + merc.ABSENT_HOLD - 1) is None
    assert watch.see(look(), FULL_BELT, 2.0 + merc.ABSENT_HOLD) == merc.WHY_MERC


def test_a_character_never_seen_with_a_merc_is_never_lost_one():
    watch = merc.MercWatch()
    for now in range(0, 60, 2):
        assert watch.see(look(), FULL_BELT, float(now)) is None


def test_the_merc_alive_again_calls_the_trip_off_and_a_new_game_starts_afresh():
    watch = watch_with_merc()
    dead = frozenset({MERC.unit_id})
    watch.see(look(dead=dead), FULL_BELT, 2.0)
    assert watch.see(look(dead=dead), FULL_BELT, 6.0) == merc.WHY_MERC
    assert watch.see(look(MERC), FULL_BELT, 8.0) is None
    watch.see(look(dead=dead), FULL_BELT, 10.0)
    assert watch.see(look(game='cyber33'), FULL_BELT, 11.0) is None  # another game: its own hold
    assert watch.trips == 0


def test_a_game_the_trip_came_back_from_unrevived_has_no_merc_trip_again():
    watch = watch_with_merc()
    merc.UNREVIVED.add('cyber32')
    dead = frozenset({MERC.unit_id})
    watch.see(look(dead=dead), FULL_BELT, 2.0)
    assert watch.see(look(dead=dead), FULL_BELT, 30.0) is None


def test_trips_a_game_are_bounded():
    watch = watch_with_merc()
    for _ in range(merc.TRIPS_A_GAME):
        watch.tripped()
    dead = frozenset({MERC.unit_id})
    watch.see(look(dead=dead), FULL_BELT, 2.0)
    assert watch.see(look(dead=dead), FULL_BELT, 30.0) is None


LOW_BELT = (FULL_REJUVENATION, FULL_REJUVENATION, SUPER_HEALING, None) * 3 + (None,) * 4  # 3 healing potions


def test_the_low_mark_is_one_healing_column_of_the_configured_belt():
    # config.py BELT.layout: rejuvenation, rejuvenation, healing, healing; 4 rows (BELT_SIZE / BELT_COLUMNS)
    assert (merc.HEALING_CAPACITY, merc.BELT_LOW) == (8, 4)
    assert merc.healing_on_belt(LOW_BELT) == 3


def test_the_belt_low_makes_its_trip_due_in_a_quiet_level_too():
    # the player, 2026-10-21 ~20:00: "we shouldn't get to the no hp potions and just 2 rejuv potions"
    watch = watch_with_merc()
    assert watch.see(look(MERC), LOW_BELT, 2.0) is None
    assert watch.see(look(MERC), LOW_BELT, 2.0 + merc.BELT_HOLD - 1) is None
    assert watch.see(look(MERC), LOW_BELT, 2.0 + merc.BELT_HOLD) == merc.WHY_BELT
    # back to a column's worth off the ground before the trip's moment: no trip for the belt
    assert watch.see(look(MERC), (SUPER_HEALING,) * merc.BELT_LOW + (None,) * 12, 10.0) is None


def test_the_belt_low_with_a_dangerous_pack_near_comes_due_sooner():
    watch = watch_with_merc()
    pack = tuple(foe(unit) for unit in range(10, 10 + merc.DANGEROUS_PACK))
    assert watch.see(look(MERC, *pack), LOW_BELT, 2.0) is None
    assert watch.see(look(MERC, *pack), LOW_BELT, 2.0 + merc.BELT_HOLD_DANGER) == merc.WHY_BELT


def test_a_belt_at_a_column_of_healing_potions_makes_no_trip():
    watch = watch_with_merc()
    full_column = (FULL_REJUVENATION, FULL_REJUVENATION, SUPER_HEALING, None) * 4
    for now in range(2, 40, 2):
        assert watch.see(look(MERC), full_column, float(now)) is None


def test_no_belt_trip_after_one_that_bought_no_potion():
    merc.NO_POTIONS.add('cyber32')
    watch = watch_with_merc()
    for now in range(2, 40, 2):
        assert watch.see(look(MERC), NO_HEALING, float(now)) is None


def test_the_belt_low_by_a_dangerous_pack_takes_the_portal_sooner():
    watch = watch_with_merc()
    watch.due, watch.due_at = merc.WHY_BELT, 10.0
    pack = tuple(foe(unit, at=5000.0 + merc.SAFE_NEAR + 5) for unit in range(10, 10 + merc.DANGEROUS_PACK))
    assert watch.moment(look(*pack), (2907, 2907), 10.0 + merc.SAFE_WAIT_DANGER) is not None
    watch.due = merc.WHY_MERC  # the merc's trip waits as before
    assert watch.moment(look(*pack), (2907, 2907), 10.0 + merc.SAFE_WAIT_DANGER) is None


def test_several_trips_fit_a_game():
    assert merc.TRIPS_A_GAME == 4  # loop.py MERC_TRIPS must equal it


def test_a_herald_or_a_leader_alone_is_a_dangerous_pack():
    assert merc.dangerous(look(foe(10, tier=5)))
    assert merc.dangerous(look(foe(10, flags=CHAMPION_FLAG)))
    assert not merc.dangerous(look(foe(10), foe(11)))


def test_the_safe_moment_waits_out_hostiles_in_reach_then_allows_one_far_with_the_life_high(caplog):
    watch = watch_with_merc()
    watch.due, watch.due_at = merc.WHY_MERC, 10.0
    with caplog.at_level(logging.INFO):
        assert watch.moment(look(foe(10)), (2907, 2907), 11.0) is None  # 5 away
        assert watch.moment(look(foe(10)), (2907, 2907), 12.0) is None
    assert sum('waits for a safe moment' in r.message for r in caplog.records) == 1  # said once
    later = 10.0 + merc.SAFE_WAIT
    assert watch.moment(look(foe(10)), (2907, 2907), later) is None  # still within SAFE_NEAR
    far = foe(10, at=5000.0 + merc.SAFE_NEAR + 5)
    assert watch.moment(look(far), (1000, 2907), later) is None  # the life low
    assert watch.moment(look(far), (2907, 2907), later) is not None
    assert watch.moment(look(), (500, 2907), 11.0) == f'no hostile within {merc.SIGHT:.0f}'
    dead_me = look()
    dead_me = replace(dead_me, player=replace(player(128), mode=17))
    assert watch.moment(dead_me, (0, 2907), 11.0) is None


@pytest.mark.parametrize('area', [128, 107])  # act 5: by the Fortress's waypoint; act 4: the portal's town is it
def test_the_package_is_the_room_trips_with_the_revive_after_the_visit(area):
    # the player, 2026-10-21 ~20:36: "every time we visit town and traders - we need to to the routine"; "do not invent
    # any IFs here: reuse routines"
    room = list(room_package(area))
    goals = list(merc.merc_package(area))
    visit = next(index for index, goal in enumerate(room) if goal.kind == TOWN_ROUTINE)
    assert goals == [*room[: visit + 1], Objective(merc.MERC_ROUTINE, 'the merc revived', STACK), *room[visit + 1 :]]
    assert [goal.kind for goal in goals][-2:] == [THROUGH_PORTAL, RESUME]
    assert goals[-2].to == area


def test_the_hireling_table_and_the_revivers_are_the_game_datas():
    import csv
    from pathlib import Path

    rows = Path(__file__).resolve().parents[3] / 'pricing' / 'raw' / 'game-excel' / 'monstats.txt'
    if not rows.exists():
        pytest.skip('no game tables here (pricing/raw is git-ignored)')
    with rows.open(encoding='latin-1') as handle:
        table = {int(row['*hcIdx']): row for row in csv.DictReader(handle, delimiter='\t') if row['*hcIdx']}
    assert {txt for txt, row in table.items() if row['AI'] == 'Hireable'} == merc.HIRELINGS
    assert {table[txt]['Id'] for txt in merc.REVIVERS.values()} == {
        'kashya', 'greiz', 'asheara', 'tyrael2', 'qual-kehk'
    }  # fmt: skip


# --- the routine in town ---------------------------------------------------------------------------------------------


class Belted:
    def __init__(self, belt) -> None:
        self.belt, self.belt_read = belt, True


class Reads:
    def __init__(self, coins: int | None, bank: int = 9_000_000) -> None:
        self.coins, self.bank = coins, bank
        self.belt: tuple[int | None, ...] = FULL_BELT  # the visit's Jamella stop filled it

    def loot(self):
        return Belted(self.belt)

    def carried(self):
        return None


class TownRun:
    """What `town_routine` reads of a run: the world, the gold."""

    def __init__(self, coins: int | None, alive: bool = False) -> None:
        self.reads = Reads(coins)
        self.alive = alive

    def world(self):
        return look(MERC, area=103) if self.alive else look(area=103)


@pytest.fixture
def town(monkeypatch):
    from inventory_tracking.macros import repair, shop

    calls: list[str] = []

    def gold(run, stat=14):
        return run.reads.coins if stat == 14 else run.reads.bank

    monkeypatch.setattr(repair, 'gold', gold)
    monkeypatch.setattr(shop, 'restock', lambda *args, **kwargs: calls.append('restock'))  # never: the visit's

    def resurrect(run):
        calls.append('resurrect')
        run.reads.coins -= merc.COST_MOST
        return True

    monkeypatch.setattr(merc, 'resurrect', resurrect)
    monkeypatch.setattr(merc, 'STASH_TOUCHED', merc.Path('/nonexistent/revive-touched-stash.txt'))
    return calls


def test_the_routine_after_the_visit_revives_the_merc_with_the_carried_gold(town, caplog):
    run = TownRun(coins=300_000)
    with caplog.at_level(logging.INFO):
        merc.town_routine(run)  # pyrefly: ignore[bad-argument-type]  # a run's reads only
    assert town == ['resurrect']  # no shop pass of its own: the visit's Jamella stop is the belt's
    assert 'Macro: merc: revived at Tyrael for 50000 gold (carried 300000 -> 250000' in caplog.text
    assert 'cyber32' not in merc.UNREVIVED


def test_carried_gold_short_of_the_revive_refills_the_belt_only_and_says_so(town, caplog):
    run = TownRun(coins=40_000)
    with caplog.at_level(logging.INFO):
        merc.town_routine(run)  # pyrefly: ignore[bad-argument-type]  # a run's reads only
    assert town == []  # never the stash's gold: no revive clicked
    assert (
        'carried gold 40000 does not cover the revive (50000 for level unread): the belt refilled only' in caplog.text
    )
    assert 'cyber32' in merc.UNREVIVED  # no merc trip again in this game


def test_a_merc_alive_in_town_is_not_revived(town):
    merc.town_routine(TownRun(coins=300_000, alive=True))  # pyrefly: ignore[bad-argument-type]  # a run's reads only
    assert town == []


def test_a_stash_gold_drop_at_the_revive_turns_revives_off(town, monkeypatch, tmp_path, caplog):
    flag = tmp_path / 'revive-touched-stash.txt'
    monkeypatch.setattr(merc, 'STASH_TOUCHED', flag)
    run = TownRun(coins=300_000)

    def resurrect(r):
        r.reads.bank -= 10_000
        return True

    monkeypatch.setattr(merc, 'resurrect', resurrect)
    with caplog.at_level(logging.INFO):
        merc.town_routine(run)  # pyrefly: ignore[bad-argument-type]  # a run's reads only
    assert flag.exists()
    assert 'revives are off for good' in caplog.text
    assert not merc.revive(run, 'CybergrindAA')  # pyrefly: ignore[bad-argument-type]  # a run's reads only


def test_the_dead_modes_are_the_natives():
    assert CORPSE.mode in DEAD_MODES
    assert merc.owned_merc(look(CORPSE)) is None


# --- a click that takes the character out of the Fortress (Tyrael's "Travel to Harrogath") --------------------------


class SeenRun:
    """A run whose `seen` gives the worlds in turn (the first that holds, as `Run.seen` waits for it)."""

    def __init__(self, *worlds) -> None:
        self.worlds = list(worlds)

    def seen(self, holds, seconds):
        while self.worlds:
            found = self.worlds.pop(0)
            if holds(found):
                return found
        return None

    def world(self):
        return look(area=103)


@pytest.mark.parametrize(
    ('worlds', 'took'),
    [((look(area=103), look(MERC, area=103)), True), ((look(area=103),), False)],
)
def test_a_revive_click_takes_when_the_merc_shows_alive_in_the_fortress(worlds, took):
    assert merc.took_revive(SeenRun(*worlds)) is took  # pyrefly: ignore[bad-argument-type]  # seen only


@pytest.mark.parametrize(
    'worlds',
    [(look(area=109),), (replace(look(area=103), player=None), look(area=109))],  # in Harrogath; loading, then there
)
def test_a_click_that_takes_the_character_away_stops_the_scan_at_once(worlds):
    with pytest.raises(merc.LeftFortress, match='level 109'):
        merc.took_revive(SeenRun(*worlds))  # pyrefly: ignore[bad-argument-type]  # seen only


def test_the_revive_given_up_out_of_the_fortress_goes_back_by_the_waypoint(town, monkeypatch, caplog):
    travels: list[int] = []
    run = TownRun(coins=300_000)

    def away(r):
        r.alive = False
        r.away = True
        raise merc.LeftFortress('the click took the character to level 109')

    monkeypatch.setattr(merc, 'resurrect', away)
    monkeypatch.setattr(TownRun, 'world', lambda self: look(area=109 if getattr(self, 'away', False) else 103))
    monkeypatch.setattr(merc, 'travel', lambda r, to, marks=None: travels.append(to))
    with caplog.at_level(logging.INFO):
        merc.town_routine(run)  # pyrefly: ignore[bad-argument-type]  # a run's reads only
    assert 'merc: the click took the character out of the Fortress: revive given up for this game' in caplog.text
    assert travels == [103]
    assert 'cyber32' in merc.UNREVIVED  # no merc trip again in this game


def test_a_belt_still_low_after_the_visit_ends_the_belts_trips_for_the_game(town, caplog):
    merc.town_routine(TownRun(coins=300_000, alive=True))  # pyrefly: ignore[bad-argument-type]  # a run's reads only
    assert 'cyber32' not in merc.NO_POTIONS
    run = TownRun(coins=300_000, alive=True)
    run.reads.belt = LOW_BELT  # the carried gold under the reserve: the visit bought none
    with caplog.at_level(logging.INFO):
        merc.town_routine(run)  # pyrefly: ignore[bad-argument-type]  # a run's reads only
    assert 'cyber32' in merc.NO_POTIONS
    assert '3 healing potions on the belt after the visit: no belt trip again in this game' in caplog.text


# Past TRIPS_A_GAME (merc.py BELT_TRIPS_BY_GAIN, 2026-10-22): cyberg65, a shard game of 4+ hours, made its belt trips at
# 22:14, 22:58, 23:02 and 23:06; with the 4th made the belt was never refilled again in it


def capped(gained: int | None) -> merc.MercWatch:
    """A watch with TRIPS_A_GAME trips made in cyber32, the last putting `gained` healing potions on the belt."""
    watch = watch_with_merc()
    for _ in range(merc.TRIPS_A_GAME):
        watch.healing = 2
        watch.tripped()
    watch.book.back(None if gained is None else 2 + gained)
    return watch


def belt_trip_due(watch: merc.MercWatch) -> str | None:
    watch.see(look(MERC), LOW_BELT, 100.0)
    return watch.see(look(MERC), LOW_BELT, 100.0 + merc.BELT_HOLD)


def test_past_the_cap_a_belt_trip_comes_while_the_last_trip_refilled_the_belt():
    assert belt_trip_due(capped(6)) == merc.WHY_BELT  # 23:07:01: 2 -> 6 on the belt
    assert belt_trip_due(capped(0)) is None  # a trip that put none on: no ping-pong
    assert belt_trip_due(capped(None)) is None  # the belt unread after it: the cap holds


def test_past_the_cap_a_merc_trip_is_still_capped():
    watch = capped(6)
    dead = frozenset({MERC.unit_id})
    watch.see(look(dead=dead), FULL_BELT, 2.0)
    assert watch.see(look(dead=dead), FULL_BELT, 30.0) is None


def test_the_switch_off_caps_the_belts_trips_as_before(monkeypatch):
    monkeypatch.setattr(merc, 'BELT_TRIPS_BY_GAIN', False)
    assert belt_trip_due(capped(6)) is None


def test_a_trip_pushed_keeps_the_belt_then_and_a_new_game_starts_the_count_afresh():
    watch = watch_with_merc()
    watch.see(look(MERC), LOW_BELT, 2.0)
    watch.tripped()
    assert (watch.book.game, watch.book.made, watch.book.belt, watch.book.gained) == ('cyber32', 1, 3, None)
    watch.see(look(MERC, game='cyber33'), FULL_BELT, 4.0)
    assert (watch.book.game, watch.trips) == ('cyber33', 0)


def test_the_trips_routine_tells_the_book_what_the_visit_put_on_the_belt(town, caplog):
    trips = merc.Trips('cyber32', 5, 2, None)
    with caplog.at_level(logging.INFO):
        merc.town_routine(TownRun(coins=300_000, alive=True), trips)  # pyrefly: ignore[bad-argument-type]  # reads only
    assert trips.gained == 8 - 2
    assert 'Macro: merc trip 5: 8 healing potions on the belt, 2 before the trip: 6 put on' in caplog.text
    other = merc.Trips('cyber99', 5, 2, None)  # another game's book: not touched
    merc.town_routine(TownRun(coins=300_000, alive=True), other)  # pyrefly: ignore[bad-argument-type]  # reads only
    assert other.gained is None


def test_the_trips_state_goes_through_the_record_and_a_malformed_one_is_ignored():
    trips = merc.Trips('cyber32', 6, 2, 4)
    kept = json.loads(json.dumps(trips.state()))
    back = merc.Trips()
    back.take_up('cyber32', kept)
    assert back == trips
    back.take_up('cyber32', {'made': 'x'})
    back.take_up('cyber32', None)
    assert back == trips


# --- a dead merc revived at any visit's end (merc.py MERC_AT_ANY_VISIT; cyberg46, 04:35:43-04:54 on 2026-10-23) ---


def test_a_dead_merc_is_revived_at_any_visits_end_once_its_owner_had_one(town, monkeypatch):
    run = TownRun(coins=300_000)
    player = run.world().player
    assert player is not None
    name = player.name
    merc.UNREVIVED.discard(run.world().game_name)
    monkeypatch.setitem(merc.LEVELS, name, 98)
    monkeypatch.setattr(merc, 'MERC_AT_ANY_VISIT', False)
    assert not merc.revive_after_visit(run)  # pyrefly: ignore[bad-argument-type]  # a run's reads only
    assert town == []
    monkeypatch.setattr(merc, 'MERC_AT_ANY_VISIT', True)
    assert merc.revive_after_visit(run)  # pyrefly: ignore[bad-argument-type]  # a run's reads only
    assert town == ['resurrect']
    assert not merc.revive_after_visit(TownRun(coins=300_000, alive=True))  # pyrefly: ignore[bad-argument-type]
    assert town == ['resurrect']  # alive: none


def test_a_visit_after_a_restart_revives_too_and_a_game_whose_revive_failed_does_not(town, monkeypatch):
    run = TownRun(coins=300_000)
    world = run.world()
    monkeypatch.setattr(merc, 'MERC_AT_ANY_VISIT', True)
    monkeypatch.setattr(merc, 'UNREVIVED', set())
    assert world.player is not None
    monkeypatch.delitem(merc.LEVELS, world.player.name, raising=False)  # a restart: no merc seen alive yet
    assert merc.revive_after_visit(run)  # pyrefly: ignore[bad-argument-type]
    assert town == ['resurrect']
    town.clear()
    monkeypatch.setattr(merc, 'UNREVIVED', {world.game_name})
    assert not merc.revive_after_visit(run)  # pyrefly: ignore[bad-argument-type]
    assert town == []
