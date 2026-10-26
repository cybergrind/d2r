"""Act 3 then act 5 in one game (macros/actloop.py OVERFLOW; the player, 2026-10-21 ~15:22: "our game turns into
clearing act 5 after the act 3"): the act harness's walk with the Northern shard at the stash's cap, both acts
terrorized at the shard step and played in that order, each act's boss first, no stop."""

import logging
from dataclasses import replace

from inventory_tracking.game.records import Carried, Pack
from inventory_tracking.game.stash import STACK_MOST
from inventory_tracking.macros import actloop, terrorize
from inventory_tracking.macros.loop import LEAVE, REPEATS, TRIPS_A_ZONE_GAME, TZ_PORTAL
from inventory_tracking.routes.tz_groups import manual_zone
from tests.inventory_tracking.macros.acts.harness import SHARD_OF, ActGame, crossing, force_ready


NORTHERN = SHARD_OF[5]


def test_an_act_3_game_with_the_northern_at_the_cap_clears_act_3_then_act_5(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    force_ready(monkeypatch, 5)
    game = crossing(ActGame(3, monkeypatch, rotation=frozenset()))
    game.game.play.stacks[NORTHERN] = STACK_MOST
    own = actloop.terrorize

    def used(run, key, act, terrorized, _floor=0):
        if act == 3:
            return own(run, key, act, terrorized)
        game.shard.append(act)
        game.game.play.stacks[NORTHERN] -= 1
        return terrorize.Used(NORTHERN, act, STACK_MOST, STACK_MOST - 1, gone=True, listed=False)

    monkeypatch.setattr(actloop, 'terrorize', used)
    walk = game.play(legs=600)
    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.shard == [3, 5]
    act3, act5 = manual_zone(3), manual_zone(5)
    assert act3 is not None
    assert act5 is not None
    runs = [area for area in walk.runs if area in act3.areas or area in act5.areas]
    last_of_3 = max(index for index, area in enumerate(runs) if area in act3.areas)
    first_of_5 = min(index for index, area in enumerate(runs) if area in act5.areas)
    assert last_of_3 < first_of_5, runs  # act 3 whole, then act 5
    # Each act's boss first: Mephisto, then act 3's; Baal's Throne first in act 5 (acts/act5.py)
    assert walk.kills[:5] == ['Mephisto', 'Ismail Vilehand', 'Battlemaid Sarina', 'Witch Doctor Endugu',
                              'Sszark the Burning']  # fmt: skip
    assert walk.kills[5:7] == ['Lister the Tormentor', 'Baal']
    assert {'Nihlathak Boss', 'Pindleskin'} <= set(walk.kills[7:])
    assert walk.legs[-1] == LEAVE
    # The game's legs over one act's bounds (loop.py ACT_LEGS): two acts' worth allowed (an act's portals, its trips
    # for room aside: TRIPS_A_ZONE_GAME, 2026-10-21)
    assert walk.legs.count(TZ_PORTAL) > REPEATS[TZ_PORTAL] - TRIPS_A_ZONE_GAME


# Game cyberg65 on 2026-10-22 ("Shard: Act 1"): Northerns picked up in act 1's levels, the Northern stack at 98, two put
# down at the 20:07:55 visit and act 5 never played. The player's ruling of the day: "use all overflow shards => maybe
# more acts"; every carried shard over the limit is used at a town stop, the game's end's included (actloop.py
# CARRIED_COUNT, END_USE), and its act played whole
def northern_walk(monkeypatch, picked_in: int | None = None) -> tuple[ActGame, list[tuple[int, int]]]:
    """An act 1 game, the Northern stack at 98; two Northerns picked up on the first run of `picked_in` (None: the
    game's first level run); the carried uses recorded."""
    force_ready(monkeypatch, 5)
    game = crossing(ActGame(1, monkeypatch, rotation=frozenset(), shards=96))
    play = game.game.play
    play.stacks[NORTHERN] = STACK_MOST - 1
    uses: list[tuple[int, int]] = []

    def carried(run, item, key, terrorized):
        pack = play.pack
        assert pack is not None
        before = play.stacks.get(item.txt, 0)
        play.pack = replace(pack, items=tuple(i for i in pack.items if i.unit_id != item.unit_id))
        act = terrorize.SHARDS[item.txt]
        uses.append((act, item.unit_id))
        return terrorize.Used(item.txt, act, before, before, gone=True, listed=False, carried=True)

    monkeypatch.setattr(actloop, 'use_carried', carried)
    picked: list[int] = []

    def on_run(area: int) -> None:
        if picked or (picked_in is not None and area != picked_in):
            return
        picked.append(area)
        play.pack = Pack(items=(Carried(901, NORTHERN, 0, 3, (1, 1)), Carried(902, NORTHERN, 1, 3, (1, 1))))

    game.on_run = on_run
    play.pack = Pack()
    return game, uses


def assert_act_5_played_after_act_1(walk) -> None:
    act1, act5 = manual_zone(1), manual_zone(5)
    assert act1 is not None
    assert act5 is not None
    runs = [area for area in walk.runs if area in act1.areas or area in act5.areas]
    assert any(area in act5.areas for area in runs), runs
    last_of_1 = max(index for index, area in enumerate(runs) if area in act1.areas)
    first_of_5 = min(index for index, area in enumerate(runs) if area in act5.areas)
    assert last_of_1 < first_of_5, runs
    assert 'Baal' in walk.kills


def test_a_northern_picked_up_in_act_1_is_used_at_the_next_town_stop_and_act_5_is_cleared(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    game, uses = northern_walk(monkeypatch)
    walk = game.play(legs=800)
    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.shard == [1]  # the kind's own from its stack; act 5 by a carried Northern
    assert uses == [(5, 901)]  # one: the second has no use left (act 5 terrorized), the visit stashes or drops it
    assert game.game.loop.agenda.acts == (1, 5)
    assert_act_5_played_after_act_1(walk)
    assert walk.legs[-1] == LEAVE


def test_a_northern_picked_up_on_act_1s_last_level_is_used_at_the_games_end_and_the_game_goes_on(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    plain, _ = northern_walk(monkeypatch, picked_in=-1)  # no Northern: where act 1's game ends
    last = plain.play(legs=800).runs[-1]
    game, uses = northern_walk(monkeypatch, picked_in=last)
    walk = game.play(legs=800)
    assert walk.stopped is None, (walk.stopped, walk.where)
    assert uses == [(5, 901)]  # Save and Exit's leg went home by Town Portal and used it there
    assert walk.moves[-1] == ('portal', 1)
    assert 'Save and Exit' not in game.game.play.said
    walk = game.play(legs=800)  # the game goes on (the walk's lists are the game's whole)
    assert walk.stopped is None, (walk.stopped, walk.where)
    assert 'Macro: act: the game goes on: act 5 terrorized at its end' in caplog.text
    assert_act_5_played_after_act_1(walk)
    assert walk.legs[-1] == LEAVE
