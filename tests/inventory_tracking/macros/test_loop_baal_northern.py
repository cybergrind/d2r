"""A spare Northern Worldstone Shard kept and used before a Baal game (actloop.py NORTHERN_FOR_BAAL, loop.py
BAAL_SHARD; the player, 2026-10-25 ~12:50: "keep northern shards +1, if we can - use before running baal")."""

import pytest

from inventory_tracking.game.records import Carried, Pack
from inventory_tracking.macros import actloop, loop as looping, terrorize
from inventory_tracking.macros.actuator import Abort, Hand
from inventory_tracking.macros.loop import (
    ANDARIEL,
    BAAL,
    BAAL_SHARD,
    HARROGATH,
    LK,
    TO_THE_KEEP,
    LegHands,
    Loop,
    next_leg,
)
from inventory_tracking.macros.route import PERFORMED
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.progress import Progress
from tests.inventory_tracking.macros.fakes import KEYS, Game, player, world


NORTHERN, DEEP = 678, 677
GAME = 'cyber32'  # the fakes' game
PANDEMONIUM_FORTRESS = 103


def at(area: int, **changes):
    return world(area, player=player(area, **changes))


def keys(_world, skills=None):
    return {skill: {**KEYS, 220: 'x'}[skill] for skill in skills or ()}


def shard(unit: int, x: int = 0, y: int = 0, txt: int = NORTHERN) -> Carried:
    return Carried(unit, txt, x, y, (1, 1))


def progress(area: int) -> Progress:
    found = Progress(ROUTES, PERFORMED, lambda: frozenset())
    found.note(GAME, area)
    return found


@pytest.fixture
def northern_on(monkeypatch):
    monkeypatch.setattr(actloop, 'NORTHERN_FOR_BAAL', True)


def test_the_northern_is_act_5s_shard():
    # NORTHERN_FOR_BAAL: on since 2026-10-25 ~13:40 (the coordinator, for the player: "the terrorized Baal"); each test
    # here sets it as it needs
    assert isinstance(actloop.NORTHERN_FOR_BAAL, bool)
    assert actloop.NORTHERN == NORTHERN
    assert terrorize.SHARDS[NORTHERN] == actloop.NORTHERN_ACT == 5


@pytest.mark.parametrize('kind', [ANDARIEL, LK, BAAL])
def test_every_kind_keeps_one_northern_past_its_full_stack_and_a_second_falls(monkeypatch, kind):
    loop = Loop(kind=kind)
    first, second = shard(1), shard(2, 1)
    pack = Pack(items=(first,), in_cube=(second,), cube_items=frozenset({2}))
    monkeypatch.setattr(actloop, 'NORTHERN_FOR_BAAL', False)
    assert actloop.spared(loop, first, lambda: pack) is None  # off: a kind with no shard use puts it down
    monkeypatch.setattr(actloop, 'NORTHERN_FOR_BAAL', True)
    assert actloop.spared(loop, first, lambda: pack) == 'a Northern Worldstone Shard kept for a Baal game'
    assert actloop.spared(loop, second, lambda: pack) is None  # the second Northern falls
    deep = shard(3, 2, txt=DEEP)
    assert actloop.spared(loop, deep, lambda: Pack(items=(first, deep))) is None  # only the Northern is kept


def test_a_baal_game_uses_a_carried_northern_before_its_waypoint_once(northern_on, monkeypatch):
    used: list[str] = []
    monkeypatch.setattr(actloop, 'baal_shard', lambda loop, run, terrorized, key=None: used.append(GAME) or True)
    found = progress(HARROGATH)
    loop = Loop(kind=BAAL, prebuffed=GAME, chosen=True)
    loop.start()
    play = Game(at(HARROGATH))
    play.pack = Pack(items=(shard(1),))
    hands = LegHands(lambda: None, lambda: False)
    assert loop.leg(play.run(), keys, found, hands) == BAAL_SHARD
    assert used == [GAME]
    assert loop.northern == GAME
    assert next_leg(at(HARROGATH), found, loop) == TO_THE_KEEP  # once a game, whatever came of it


def test_with_nothing_spare_or_the_switch_off_the_baal_game_runs_as_now(monkeypatch):
    found = progress(HARROGATH)
    loop = Loop(kind=BAAL, prebuffed=GAME, chosen=True)
    loop.start()
    play = Game(at(HARROGATH))
    play.pack = Pack(items=(shard(1),))
    went: list[int] = []
    monkeypatch.setattr(looping, 'travel', lambda run, area, marks=None: went.append(area))
    monkeypatch.setattr(looping, 'gold', lambda run: 500_000)
    hands = LegHands(lambda: None, lambda: False)
    monkeypatch.setattr(actloop, 'NORTHERN_FOR_BAAL', False)
    assert loop.leg(play.run(), keys, found, hands) == TO_THE_KEEP  # the switch off: carried, not used
    monkeypatch.setattr(actloop, 'NORTHERN_FOR_BAAL', True)
    loop.done, loop.games = None, 0
    play.pack = Pack(items=())  # nothing carried, Harrogath: no stack to take one from
    loop.northern = None
    assert loop.leg(play.run(), keys, found, hands) == TO_THE_KEEP
    assert loop.northern_ready is None


def test_the_shard_step_reads_a_full_northern_stack_in_the_fortress_only(northern_on, monkeypatch):
    monkeypatch.setattr(actloop, 'NORTHERN_STACK', False)  # as before the floor (2026-10-25 ~13:48)
    play = Game(at(PANDEMONIUM_FORTRESS))
    rows: tuple[str, ...] = ('.' * 10,) * 10
    play.stash_pages, play.stacks = [rows] * 6, {NORTHERN: 99}
    play.pack = Pack(items=())
    run = play.run()
    assert actloop.northern_ready(run, PANDEMONIUM_FORTRESS) == 'stack'
    assert actloop.northern_ready(run, HARROGATH) is None
    play.pack = Pack(items=(shard(1),))
    assert actloop.northern_ready(play.run(), HARROGATH) == 'carried'


def test_baal_shard_uses_the_carried_one_and_a_refusal_or_stop_leaves_the_game_as_before(northern_on, monkeypatch):
    item = shard(7)
    play = Game(at(HARROGATH))
    play.pack = Pack(items=(item,))
    clicked: list[int] = []

    def use(run, carried, key, terrorized):
        clicked.append(carried.unit_id)
        return terrorize.Used(NORTHERN, 5, 99, 99, gone=True, listed=True, carried=True)

    monkeypatch.setattr(actloop, 'use_carried', use)
    assert actloop.baal_shard(Loop(kind=BAAL), play.run(), lambda area: None)
    assert clicked == [7]
    monkeypatch.setattr(actloop, 'use_carried', lambda *a: terrorize.Used(NORTHERN, 5, 99, 99, gone=False))
    assert not actloop.baal_shard(Loop(kind=BAAL), play.run(), lambda area: None)  # refused: still carried

    def stop(*a):
        raise Abort('the inventory did not open')

    monkeypatch.setattr(actloop, 'use_carried', stop)
    assert not actloop.baal_shard(Loop(kind=BAAL), play.run(), lambda area: None)

    def hand(*a):
        raise Hand('the player moved the mouse')

    monkeypatch.setattr(actloop, 'use_carried', hand)
    with pytest.raises(Hand):
        actloop.baal_shard(Loop(kind=BAAL), play.run(), lambda area: None)


def test_with_the_floor_the_stack_is_used_in_any_town_while_it_holds_more_than_40(northern_on, monkeypatch):
    # the player, 2026-10-25 ~13:48: "floor is 40, use up to it"
    monkeypatch.setattr(actloop, 'NORTHERN_STACK', True)
    rows: tuple[str, ...] = ('.' * 10,) * 10
    for area in (HARROGATH, PANDEMONIUM_FORTRESS):
        for count, ready in ((98, 'stack'), (41, 'stack'), (40, None), (12, None)):
            play = Game(at(area))
            play.stash_pages, play.stacks = [rows] * 6, {NORTHERN: count}
            play.pack = Pack(items=())
            assert actloop.northern_ready(play.run(), area) == ready, (area, count)


def test_with_the_floor_the_baal_shard_takes_one_from_the_stack_at_41_or_more(northern_on, monkeypatch):
    monkeypatch.setattr(actloop, 'NORTHERN_STACK', True)
    rows: tuple[str, ...] = ('.' * 10,) * 10
    floors: list[int] = []

    def used(run, key, act, terrorized, floor):
        floors.append(floor)
        return terrorize.Used(NORTHERN, 5, 98, 97, gone=True, listed=True)

    monkeypatch.setattr(actloop, 'terrorize', used)
    play = Game(at(HARROGATH))
    play.stash_pages, play.stacks = [rows] * 6, {NORTHERN: 98}
    play.pack = Pack(items=())
    assert actloop.baal_shard(Loop(kind=BAAL), play.run(), lambda area: None)
    assert floors == [41]
    play.stacks = {NORTHERN: 40}
    assert not actloop.baal_shard(Loop(kind=BAAL), play.run(), lambda area: None)  # at the floor: none taken
    assert floors == [41]


def test_choose_shard_takes_a_floor():
    from inventory_tracking.game.records import StashView

    assert terrorize.choose_shard(None, 5, 41) is None
    assert hasattr(StashView, 'count')
