"""Handovers and repeated work: what the loop does between two things, and what it does twice.

On the scripted game's clock, except the runner's own handover, which is real threads and wall time
with a bound far above what it takes (2 ms in the logs, evidence b1) and far below the pause it
guards against (the card's 4 s).
"""

import threading
import time

import pytest

from inventory_tracking.config import APPRAISAL
from inventory_tracking.levels import model
from inventory_tracking.levels.model import Level, Target
from inventory_tracking.loot.materials import material_classes
from inventory_tracking.macros.actuator import Cancelled
from inventory_tracking.macros.hunt import SLICE
from inventory_tracking.macros.pickup import pick_up
from inventory_tracking.macros.runner import ATTACK, TELEPORT, MacroRunner
from inventory_tracking.macros.teleport import Way, landing
from inventory_tracking.macros.view import Viewport
from inventory_tracking.macros.world import ITEM_UNIT, TRACE_RVAS, GameMemory, Player, monsters_and_dead
from inventory_tracking.native.layout import UI_PANELS_RVA
from tests.inventory_tracking.macros.fakes import SLOTS
from tests.inventory_tracking.scenarios.loop.helpers import (
    ASPECT,
    CHAMPION,
    NO_MARK_SLOTS,
    ROOMS,
    TICK,
    CountedMemory,
    attack_mode,
    busiest_frame,
    foe,
    game,
    hunter,
    keys,
    left_click,
    monster_table,
    recorded,
    skill_table,
)


TABLE, BASE = 0x100000, 0x10000000


def test_attack_mode_is_back_the_moment_a_step_is_over():
    # The card of a run that ended stays 4 s (runner.CARD_SECONDS): the mode must not wait for it.
    ended, resumed = [], []
    back = threading.Event()

    def execute(cancelled, routine):
        if routine == ATTACK:
            if ended:
                resumed.append(time.monotonic())
                back.set()
            assert cancelled.wait(5)
            raise Cancelled
        ended.append(time.monotonic())

    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=None, execute=execute)
    try:
        assert runner.request(10.0, 10.1, ATTACK)
        assert runner.request(10.3, 10.4, TELEPORT)  # the mode pauses for the step
        assert back.wait(5)
        assert resumed[0] - ended[0] < 0.5
    finally:
        runner.close()


def test_a_click_during_a_fight_lets_the_strike_go_within_a_tick():
    play = game(foe(10, 5008.0, 5000.0), slots=NO_MARK_SLOTS)
    play.toughness[10] = 1000
    attack_mode(play, hunter(play), until=3.0, events=[left_click(play, 1.0)])
    released = min(at for at in play.strike_releases() if at >= 1.0)
    assert released - 1.0 <= TICK
    assert len(play.walks) == 1  # and the click the cast swallowed is made for the player


@pytest.mark.xfail(
    strict=True,
    reason='a click made while Death Mark is being cast in a fight is seen at once and served last: the mark, its '
    'pause and the aim back on the line all run first, and the strike stays held 0.50 s here (a mark every 8 s, '
    '328 ms each in the logs, evidence a4)',
)
def test_a_click_during_death_mark_lets_the_strike_go_within_a_tick():
    plain = game(foe(10, 5008.0, 5000.0))
    plain.toughness[10] = 10**6
    attack_mode(plain, hunter(plain), until=10.0)
    mark = plain.keys.names['d']
    second = [at for at, code in plain.pressed_at if code == mark][1]  # the mark cast with the strike held
    aiming = min(at for at, _ in plain.moved_at if second - 0.4 < at <= second)  # its aim begins
    clicked = aiming + 0.01
    again = game(foe(10, 5008.0, 5000.0))
    again.toughness[10] = 10**6
    attack_mode(again, hunter(again), until=10.0, events=[left_click(again, clicked)])
    released = min(at for at in again.strike_releases() if at >= clicked)
    assert released - clicked <= TICK


@pytest.mark.xfail(
    strict=True,
    reason='every press of the pickup step walks the item table again (five walks a scan, world.GameMemory.loot) '
    'though nothing has died since the scan that found nothing: 3 scans for 3 presses here; in the logs 307 of 345 '
    'scans found nothing and 80 came within 1 s of the one before (evidence e). A scan is about 5 ms: little time',
)
def test_hunting_one_elite_does_not_scan_the_ground_again_on_every_hop():
    play = game(foe(10, 5080.0, 5000.0, CHAMPION))
    hunt = hunter(play)
    level = Level(101, ROOMS, ())
    scans = []
    for _ in range(3):  # three presses, a hop each, within half a second of the clock
        run = play.run()
        loot = run.loot
        assert loot is not None

        def counted(loot=loot):
            scans.append(play.clock.now)
            return loot()

        run.loot = counted
        assert pick_up(run, level, keys, lambda run=run: hunt.seek(run, keys)) is False
    assert scans[-1] - scans[0] < 1.0
    assert play.world.monsters  # nothing died meanwhile: nothing new can lie there
    assert len(scans) == 1


def test_a_hop_is_planned_on_one_ground_not_one_per_spot_tried(monkeypatch):
    take, _, rooms, grids = recorded()
    frame = busiest_frame(take)
    row = frame['p']
    stand = Player(row[0], 'CybergrindAA', 1, row[2], row[3], row[4], False)
    mark = (rooms[0].x + 0.5, rooms[0].y + 0.5)
    target = Target(row[2], rooms, mark, 'the elite', 'hunt', False, grids)
    way = Way(target, Viewport(ASPECT))
    built = []
    init = model.Ground.__init__

    def counted(self, grids):
        built.append(1)
        init(self, grids)

    monkeypatch.setattr(model.Ground, '__init__', counted)
    landing(target, stand, way, ASPECT)
    assert len(built) <= 2


def test_the_world_is_read_once_a_tick_at_most_idle_or_fighting():
    for place in (5060.0, 5008.0):  # out of reach: the mode idles; in reach: it fights
        play = game(foe(10, place, 5000.0), slots=NO_MARK_SLOTS)
        play.toughness[10] = 10**6
        attack_mode(play, hunter(play), until=3.0)
        assert sum(1 for at in play.reads if 1.0 <= at < 2.0) <= 1 / TICK + 1


@pytest.mark.xfail(
    strict=True,
    reason='the nap looks, then sleeps through the pace, which looks before and after its own slice: 324 looks a '
    'second idle and 375 in a fight here, each a round trip to the X server, where 100 would see every click',
)
@pytest.mark.parametrize('place', [5060.0, 5008.0], ids=['idle', 'fighting'])
def test_the_left_button_is_looked_at_once_a_slice(place):
    play = game(foe(10, place, 5000.0), slots=NO_MARK_SLOTS)
    play.toughness[10] = 10**6
    looks, state = [], play.keys.pointer_state

    def counted():
        looks.append(play.clock.now)
        return state()

    play.keys.pointer_state = counted
    attack_mode(play, hunter(play), until=3.0)
    assert sum(1 for at in looks if 1.0 <= at < 2.0) <= 1.1 / SLICE


def memory_of(counted: CountedMemory) -> GameMemory:
    """`GameMemory` over the counted blocks: no process is opened."""
    memory = object.__new__(GameMemory)
    memory.base, memory.table, memory.fd = BASE, TABLE, -1
    memory.read = counted.read  # type: ignore[method-assign]
    return memory


@pytest.mark.xfail(
    strict=True,
    reason='GameMemory.loot walks the item table five times a call: the runes, the marked materials, the uniques, '
    'the potions and the belt each walk it on their own',
)
def test_one_look_at_the_loot_walks_the_item_table_once():
    counted = CountedMemory()
    counted.block(TABLE + ITEM_UNIT * 1024, 1024)  # no item units: every walk is the read of the heads
    memory = memory_of(counted)
    memory._player = lambda: Player(1, 'CybergrindAA', 1, 35, 5000.0, 5000.0, False)  # type: ignore[method-assign]
    loot = memory.loot(rune_minimum='r01', unique_minimum=1.0, materials=material_classes(APPRAISAL.material_marks))
    assert loot.drops == ()
    assert len(counted.reads) == 1


@pytest.mark.xfail(
    strict=True,
    reason="every look at the world reads the 20 research bytes of TRACE_RVAS one by one (the new-game routine's "
    'load trace): 24 reads before the first unit, 25 times a second in a fight',
)
def test_a_look_at_the_world_reads_no_research_bytes():
    counted = CountedMemory()
    image = counted.block(BASE, 0x2600000)
    image[UI_PANELS_RVA] = 1  # in a game
    image[0x1E011B0 : 0x1E011B0 + len(skill_table(SLOTS))] = skill_table(SLOTS)
    memory = memory_of(counted)
    memory._player = lambda: None  # type: ignore[method-assign]
    world = memory.world()
    assert world.in_game
    assert world.slots == SLOTS
    assert not [address for address, size in counted.reads if size == 1 and address - BASE in TRACE_RVAS]
    assert len(counted.reads) <= 5  # the panels, the game's name, the skill slots, the view byte


def test_the_monster_walk_reads_six_times_a_live_monster_at_most():
    # The unit, its path, its data and its stat list (header, values, header again): what a look costs today.
    counted = CountedMemory()
    monster_table(counted, TABLE, 60)
    live, dead = monsters_and_dead(counted.read, TABLE)
    assert len(live) == 60
    assert dead == frozenset()
    assert len(counted.reads) <= 1 + 6 * 60
    assert {(m.life, m.max_life) for m in live} == {(90, 128)}
