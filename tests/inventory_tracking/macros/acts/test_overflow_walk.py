"""Act 3 then act 5 in one game (macros/actloop.py OVERFLOW; the player, 2026-10-21 ~15:22: "our game turns into
clearing act 5 after the act 3"): the act harness's walk with the Northern shard at the stash's cap, both acts
terrorized at the shard step and played in that order, each act's boss first, no stop."""

import logging

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

    def used(run, key, act, terrorized):
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
