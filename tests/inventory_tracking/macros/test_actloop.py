"""Shards over the limit (macros/actloop.py OVERFLOW; the player, 2026-10-21 ~15:22: "if we engounter such stone - we
just use it, so our game turns into clearing act 5 after the act 3"; "only for shards that are over the limit"): which
acts are terrorized too, in which order they are played, a refused use, a carried shard used at a visit, the game's cap,
the restart state, and the switch off. Over test_tzloop.py's scripted game, the shard's clicks recorded. Offline: the
game's own refusal is the 15:08:41 one on 2026-10-21 (an act terrorized already)."""

import json
import time
from dataclasses import replace

import pytest

from inventory_tracking.game.records import Carried, Pack, StashView
from inventory_tracking.game.stash import STACK_MOST
from inventory_tracking.macros import actloop, midgame, terrorize
from inventory_tracking.macros.actuator import Abort, Hand
from inventory_tracking.macros.agenda import Agenda
from inventory_tracking.macros.loop import ACT_KINDS, ACT_SECONDS, TOWN, TZ_SHARD, TZ_WAYPOINT, GameId, Loop
from inventory_tracking.macros.route import PERFORMED
from inventory_tracking.macros.town import Exit
from inventory_tracking.macros.tzroutine import Itinerary, itinerary
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.progress import Progress
from inventory_tracking.routes.tz_groups import manual_zone
from tests.inventory_tracking.macros.fakes import stash_with
from tests.inventory_tracking.macros.test_tzloop import CATACOMBS, FORTRESS, GAME, Script


WESTERN, EASTERN, SOUTHERN, DEEP, NORTHERN = 674, 675, 676, 677, 678
SHARD_OF = {act: shard for shard, act in terrorize.SHARDS.items()}


def view(**stacks: int) -> StashView:
    names = {'western': WESTERN, 'eastern': EASTERN, 'southern': SOUTHERN, 'deep': DEEP, 'northern': NORTHERN}
    return StashView((), tuple(sorted((names[name], count) for name, count in stacks.items())))


def act_game(monkeypatch, act: int = 3, stacks: dict[int, int] | None = None, outcomes: dict | None = None) -> Script:
    """A game of act `act`'s kind in the Fortress: the stash holds `stacks` (the kind's shard at 97 and the Northern
    at the cap by default), each act's use does as `outcomes` says ('used' by default, 'refused': the shard stays
    carried, 'stops': an Abort, 'hand': the player's hand); the uses recorded in `game.calls`."""
    game = Script(FORTRESS, monkeypatch, zone=CATACOMBS)
    game.loop.kind = ACT_KINDS[f'act{act}']
    game.play.stash_pages = [('.' * 10,) * 10]
    game.play.stacks = dict(stacks if stacks is not None else {SHARD_OF[act]: 97, NORTHERN: STACK_MOST})
    monkeypatch.setattr(terrorize, 'CLICKS', True)
    told = outcomes or {}

    def outcome(used_act: int, shard: int, carried: bool) -> terrorize.Used | None:
        how = told.get(used_act, 'used')
        if how == 'stops':
            raise Abort('no game window')
        if how == 'hand':
            raise Hand('the player pressed a key')
        before = game.play.stacks.get(shard, 0)
        if how == 'refused':
            if not carried:
                game.play.stacks[shard] -= 1  # taken out, not used: it stays carried
            return terrorize.Used(shard, used_act, before, before - (not carried), gone=False, carried=carried)
        if not carried:
            game.play.stacks[shard] -= 1
        return terrorize.Used(shard, used_act, before, before - (not carried), gone=True, listed=False, carried=carried)

    def used(run, key, used_act, terrorized, _floor=0):
        game.calls.append(('terrorize', used_act))
        return outcome(used_act, SHARD_OF[used_act], carried=False)

    def carried(run, item, key, terrorized):
        game.calls.append(('carried', terrorize.SHARDS[item.txt], item.unit_id))
        return outcome(terrorize.SHARDS[item.txt], item.txt, carried=True)

    monkeypatch.setattr(actloop, 'terrorize', used)
    monkeypatch.setattr(actloop, 'use_carried', carried)
    return game


def shard_uses(game: Script) -> list[tuple]:
    return [call for call in game.calls if call[0] in ('terrorize', 'carried')]


def zones_of(game: Script) -> list[str]:
    plan = game.loop.agenda.plan
    assert isinstance(plan, Itinerary)
    return plan.zone.split(' + ')


def first_trip_act(game: Script) -> int:
    """The act of the plan's first excursion."""
    plan = game.loop.agenda.plan
    assert isinstance(plan, Itinerary)
    first = plan.excursions[0].areas[0]
    return next(act for act in range(1, 6) if (zone := manual_zone(act)) is not None and first in zone.areas)


# -- which acts, in which order ----------------------------------------------------------------------------------------


def test_the_cap_is_the_stashs_99_and_a_shard_at_it_is_over_the_limit():
    # game/layout.py STACK_MOST (a resource tab's stack refused at 99, the player, 2026-10-17), game/records.py
    # `StashView.full`: the 15:08:10 stash view on 2026-10-21 named the Western, Eastern and Northern shards full
    assert STACK_MOST == 99
    assert terrorize.over_limit(view(northern=99, southern=90, western=98)) == (NORTHERN,)
    assert terrorize.over_limit(view(western=99, eastern=99, northern=99)) == (WESTERN, EASTERN, NORTHERN)
    assert terrorize.over_limit(view(western=99)) == tuple(sorted(view(western=99).full()))
    assert terrorize.over_limit(None) == ()


@pytest.mark.parametrize(
    ('stacks', 'own', 'most', 'due'),
    [
        ({'northern': 99, 'southern': 90}, 3, 1, (5,)),  # the player's case: act 5 after act 3
        ({'northern': 98, 'southern': 90}, 3, 1, ()),  # under the cap: only its own kind uses it
        ({'southern': 99}, 3, 1, ()),  # the kind's own shard at the cap is the kind's own use
        ({'western': 99, 'eastern': 99, 'northern': 99}, 3, 1, (5,)),  # one a game: the acts after the kind's first
        ({'western': 99, 'eastern': 99, 'northern': 99}, 3, None, (5, 1, 2)),
        ({'western': 99, 'eastern': 99, 'northern': 99}, 5, None, (1, 2)),
        ({'deep': 99, 'northern': 99}, 3, 1, (4,)),
    ],
)
def test_the_acts_due_are_those_of_shards_at_the_cap_the_acts_after_the_kinds_first(
    monkeypatch, stacks, own, most, due
):
    monkeypatch.setattr(actloop, 'OVERFLOW_MOST', most)
    assert tuple(act for act, _ in actloop.overflow_due(view(**stacks), Agenda(), own)) == due


def test_an_act_terrorized_or_tried_is_not_due_again_and_one_a_game_is_played(monkeypatch):
    monkeypatch.setattr(actloop, 'OVERFLOW_MOST', 1)  # the bound of 2026-10-21 ("one extra act")
    agenda = Agenda(acts=(3,), overflow={2: actloop.REFUSED})
    stash = view(western=99, eastern=99, northern=99)
    assert [act for act, _ in actloop.overflow_due(stash, agenda, 3)] == [5]  # act 2 refused: not tried again
    agenda.acts, agenda.overflow[5] = (3, 5), actloop.USED
    assert actloop.overflow_due(stash, agenda, 3) == ()  # OVERFLOW_MOST played
    monkeypatch.setattr(actloop, 'OVERFLOW_MOST', None)
    assert [act for act, _ in actloop.overflow_due(stash, agenda, 3)] == [1]
    monkeypatch.setattr(actloop, 'OVERFLOW', False)
    assert actloop.overflow_due(stash, Agenda(), 3) == ()


def test_a_carried_shard_of_a_full_stack_is_used_before_one_from_the_stack():
    cube, inventory = Carried(8, NORTHERN, 0, 0, (1, 1)), Carried(9, NORTHERN, 4, 1, (1, 1))
    ((act, item),) = actloop.overflow_due(view(northern=99), Agenda(), 3, (inventory, cube))
    assert (act, item) == (5, inventory)  # the inventory's first
    assert actloop.overflow_due(view(northern=99), Agenda(), 3, (Carried(7, WESTERN, 0, 0, (1, 1)),))[0][1] is None


def test_an_act_3_game_with_the_northern_at_the_cap_plays_act_3_then_act_5(monkeypatch, caplog):
    game = act_game(monkeypatch)
    with caplog.at_level('INFO'):
        assert game.leg() == TZ_SHARD
    assert shard_uses(game) == [('terrorize', 3), ('terrorize', 5)]  # the kind's own first
    agenda = game.loop.agenda
    assert agenda.acts == (3, 5)
    assert agenda.overflow == {5: actloop.USED}
    assert agenda.shard == actloop.USED
    assert game.play.stacks == {SOUTHERN: 96, NORTHERN: 98}
    assert 'Macro: act: Northern shard over the limit (99): act 5 terrorized too, played after act 3' in caplog.text
    assert game.leg() == TZ_WAYPOINT
    assert zones_of(game)[:2] == ['Act3-Manual', 'Act5-Manual']
    assert first_trip_act(game) == 3  # Mephisto's trip first, the kind's boss
    assert game.calls[-1] == ('waypoint', 101)
    assert len(shard_uses(game)) == 2  # never a shard again in the game


def test_the_kinds_act_is_played_first_whatever_the_acts_numbers(monkeypatch):
    # Act 5's kind with the Southern at the cap: act 5 first, then act 3 (routes/tz_groups.py `match_zones` puts the
    # acts in act order; the itinerary takes the game's order)
    game = act_game(monkeypatch, act=5, stacks={NORTHERN: 95, SOUTHERN: STACK_MOST})
    assert game.leg() == TZ_SHARD
    assert game.loop.agenda.acts == (5, 3)
    game.leg()
    assert zones_of(game)[:2] == ['Act5-Manual', 'Act3-Manual']
    assert first_trip_act(game) == 5
    act3, act5 = (manual_zone(act) for act in (3, 5))
    assert act3 is not None
    assert act5 is not None
    both = act3.core | act5.core
    first = itinerary(both, (5, 3))
    assert first is not None
    assert first.zone.startswith('Act5-Manual + Act3-Manual')
    acts_order = itinerary(both)
    assert acts_order is not None
    assert acts_order.zone.startswith('Act3-Manual + Act5-Manual')  # no order given: the acts' numbers, as before


def test_with_the_switch_off_only_the_kinds_own_shard_is_used(monkeypatch):
    monkeypatch.setattr(actloop, 'OVERFLOW', False)
    game = act_game(monkeypatch)
    assert game.leg() == TZ_SHARD
    assert shard_uses(game) == [('terrorize', 3)]
    assert game.loop.agenda.acts == (3,)
    assert game.loop.agenda.overflow == {}
    assert game.play.stacks[NORTHERN] == STACK_MOST
    game.leg()
    assert 'Act5-Manual' not in zones_of(game)


def test_a_carried_shard_of_the_kinds_own_act_is_used_before_its_stack(monkeypatch):
    # 02:12:26 on 2026-10-23: two Western shards found in an act 1 game were put down, the stack full (OWN_CARRIED)
    monkeypatch.setattr(actloop, 'OVERFLOW', False)
    game = act_game(monkeypatch, act=1, stacks={WESTERN: STACK_MOST})
    game.play.pack = Pack(items=(Carried(7, WESTERN, 2, 0, (1, 1)),))
    assert game.leg() == TZ_SHARD
    assert shard_uses(game) == [('carried', 1, 7)]
    assert game.loop.agenda.acts == (1,)
    assert game.play.stacks[WESTERN] == STACK_MOST  # the stack kept whole
    monkeypatch.setattr(actloop, 'OWN_CARRIED', False)
    again = act_game(monkeypatch, act=1, stacks={WESTERN: STACK_MOST})
    again.play.pack = Pack(items=(Carried(7, WESTERN, 2, 0, (1, 1)),))
    assert again.leg() == TZ_SHARD
    assert shard_uses(again) == [('terrorize', 1)]


def test_no_shard_of_its_own_at_the_floor_still_plays_the_act_over_the_limit(monkeypatch):
    game = act_game(monkeypatch, stacks={SOUTHERN: 60, NORTHERN: STACK_MOST})
    assert game.leg() == TZ_SHARD
    assert shard_uses(game) == [('terrorize', 5)]
    assert game.loop.agenda.shard == actloop.NONE_HELD
    assert game.loop.agenda.acts == (5,)


# -- a refused or stopped use ------------------------------------------------------------------------------------------


@pytest.mark.parametrize('how', ['refused', 'stops'])
def test_a_refused_overflow_use_leaves_the_kinds_shard_and_the_game_alone(monkeypatch, caplog, how):
    # 15:08:41 on 2026-10-21: "the right click on the Southern Worldstone Shard at (4, 3) did not use it: it stays
    # carried" (its act terrorized already)
    game = act_game(monkeypatch, outcomes={5: how})
    with caplog.at_level('INFO'):
        assert game.leg() == TZ_SHARD  # no stop: the leg is made
    agenda = game.loop.agenda
    assert agenda.shard == actloop.USED
    assert agenda.shard_failures == 0  # the kind's own shard is not given up for it
    assert agenda.acts == (3,)
    assert agenda.overflow == {5: actloop.REFUSED if how == 'refused' else actloop.FAILED}
    if how == 'refused':
        assert 'Macro: act: Northern shard over the limit (99): refused (still carried): act 5 not played; the shard ' \
            'carried, stashed again at the next visit' in caplog.text  # fmt: skip
    else:
        assert 'Macro: act: Northern shard over the limit (99): not used (no game window): act 5 not played' in (
            caplog.text
        )
    assert game.leg() == TZ_WAYPOINT  # the game goes on: act 3, the rotation
    assert 'Act5-Manual' not in zones_of(game)
    assert len(shard_uses(game)) == 2  # never tried again in the game


def test_the_players_hand_on_an_overflow_use_notes_nothing_and_it_is_tried_at_the_next_visit(monkeypatch):
    game = act_game(monkeypatch, outcomes={5: 'hand'})
    with pytest.raises(Hand):
        game.leg()
    assert game.loop.agenda.shard == actloop.USED  # the kind's own is made
    assert game.loop.agenda.overflow == {}


# -- a capped shard picked up mid-game ---------------------------------------------------------------------------------


def test_a_carried_shard_whose_stack_is_full_is_used_at_the_next_visit_its_act_after_the_current(monkeypatch, caplog):
    game = act_game(monkeypatch, stacks={SOUTHERN: 97, NORTHERN: 98})
    assert game.leg() == TZ_SHARD
    assert shard_uses(game) == [('terrorize', 3)]  # 98: under the cap
    # Mid-game: a Northern stashed at a visit (99), another carried in the cube; the next visit is due
    game.play.stacks[NORTHERN] = STACK_MOST
    game.play.pack = Pack(in_cube=(Carried(77, NORTHERN, 0, 0, (1, 1)),), cube_items=frozenset({77}))
    game.loop.visiting = GAME
    visits: list = []

    def visit(exit) -> None:
        visits.append(shard_uses(game)[-1])  # the shard was used before the visit (which would put it down)
        game.loop.visited = GAME

    with caplog.at_level('INFO'):
        assert game.leg(visit=visit) == TOWN
    assert visits == [('carried', 5, 77)]
    assert game.loop.agenda.acts == (3, 5)
    assert game.play.stacks[NORTHERN] == STACK_MOST  # the carried one, not one from the stack
    assert (
        'Macro: act: Northern shard over the limit (99), a carried one: act 5 terrorized too, played after act 3'
        in (caplog.text)
    )


def test_no_overflow_at_a_visit_before_the_games_own_shard_step(monkeypatch):
    # The game's first visit (room for the shard) comes before the shard step: the kind's act is never second
    game = act_game(monkeypatch)
    game.loop.visiting = GAME
    assert game.leg(visit=lambda exit: setattr(game.loop, 'visited', GAME)) == TOWN
    assert shard_uses(game) == []
    assert game.leg() == TZ_SHARD
    assert shard_uses(game) == [('terrorize', 3), ('terrorize', 5)]


# -- the game's cap and the restart state ------------------------------------------------------------------------------


def test_the_games_cap_covers_the_overflow_act(monkeypatch):
    game = act_game(monkeypatch)
    loop = game.loop
    before = loop.allowed_seconds(GAME)
    assert before == ACT_SECONDS[3]
    assert game.leg() == TZ_SHARD
    assert loop.allowed_seconds(GAME) == ACT_SECONDS[3] + ACT_SECONDS[5]
    assert loop.allowed_seconds('another game') == ACT_SECONDS[3]  # the agenda's game only
    now = time.monotonic()
    loop.seen = (GAME, now - ACT_SECONDS[3] - 60)  # an hour and a minute into the game
    assert not loop.overdue(GAME, now)
    loop.seen = (GAME, now - ACT_SECONDS[3] - ACT_SECONDS[5] - 60)
    assert loop.overdue(GAME, now)


def test_the_ordered_acts_and_the_overflow_ride_the_restart_state(monkeypatch):
    game = act_game(monkeypatch, act=5, stacks={NORTHERN: 95, SOUTHERN: STACK_MOST, WESTERN: STACK_MOST},
                    outcomes={1: 'refused'})  # fmt: skip
    monkeypatch.setattr(actloop, 'OVERFLOW_MOST', None)
    assert game.leg() == TZ_SHARD
    assert game.loop.agenda.acts == (5, 3)
    kept = midgame.snapshot(game.loop, game.progress)
    assert kept is not None
    assert kept['agenda']['acts'] == [5, 3]  # in their order, not sorted
    assert kept['agenda']['overflow'] == [[1, actloop.REFUSED], [3, actloop.USED]]
    loop = Loop(on=True, kind=ACT_KINDS['act5'], chosen=True)
    loop.start()
    from inventory_tracking.terror.tracker import ZoneTracker

    loop.records = ZoneTracker()  # the game's record (midgame.py RECORD), as `keep` writes it
    loop.records.record_note(f'{GAME}#1', 'loop', {name: value for name, value in kept.items() if name != 'at'})
    game.loop = loop
    game.progress = Progress(ROUTES, PERFORMED, lambda: frozenset(game.killed), wanted=lambda a: a in game.zone)
    game.progress.note(GAME, game.area)
    assert game.leg() == TZ_WAYPOINT  # no shard again after the restart
    assert len(shard_uses(game)) == 3
    assert loop.agenda.acts == (5, 3)
    assert loop.agenda.overflow == {1: actloop.REFUSED, 3: actloop.USED}
    assert loop.agenda.game == GameId(GAME, 1)
    assert zones_of(game)[:2] == ['Act5-Manual', 'Act3-Manual']
    assert loop.allowed_seconds(GAME) == ACT_SECONDS[5] + ACT_SECONDS[3]


def test_a_state_written_before_the_overflow_is_taken_up():
    # The live service's resume.json of 2026-10-21 has no 'overflow' (written before it)
    old = Agenda(shard=actloop.USED, acts=(3,)).state()
    del old['overflow']
    old['acts'] = [3]
    agenda = Agenda()
    agenda.take_up(json.loads(json.dumps(old)), GameId(GAME, 1))
    assert agenda.acts == (3,)
    assert agenda.overflow == {}


def test_a_games_leg_bounds_take_one_more_acts_worth_for_each_overflow_act(monkeypatch):
    from inventory_tracking.macros.loop import REPEATS, TZ_PORTAL, TZ_SHARD as SHARD_LEG
    from tests.inventory_tracking.macros.test_tzloop import at

    game = act_game(monkeypatch)
    assert game.leg() == TZ_SHARD
    loop, here = game.loop, at(FORTRESS)
    for _ in range(2 * REPEATS[TZ_PORTAL]):
        loop.count(here, TZ_PORTAL)  # two acts' worth of Town Portals
    with pytest.raises(Abort, match='again and again'):
        loop.count(here, TZ_PORTAL)
    for _ in range(REPEATS[SHARD_LEG] - 1):  # one made by the shard's leg
        loop.count(here, SHARD_LEG)
    with pytest.raises(Abort, match='again and again'):
        loop.count(here, SHARD_LEG)  # the shard step's own bound is not an act's
    loop.agenda.overflow.clear()  # no overflow act: one act's worth, as before
    loop.made.clear()
    for _ in range(REPEATS[TZ_PORTAL]):
        loop.count(here, TZ_PORTAL)
    with pytest.raises(Abort, match='again and again'):
        loop.count(here, TZ_PORTAL)


# -- a full stack's shard on the ground (PICK_OVER_LIMIT; the player, 2026-10-21 ~15:55: "Pick up and use") ------------


def test_a_full_stacks_shard_is_picked_up_only_while_the_overflow_slot_is_free(monkeypatch):
    monkeypatch.setattr(actloop, 'OVERFLOW_MOST', 1)  # the bound of 2026-10-21 ("one extra act")
    game = act_game(monkeypatch, stacks={SOUTHERN: 97, NORTHERN: 98})
    loop = game.loop
    loop.agenda.begin(GameId(GAME, 1))
    assert actloop.picked_shards(loop) == frozenset()  # before the game's own shard step
    loop.agenda.shard, loop.agenda.acts = actloop.USED, (3,)
    assert actloop.picked_shards(loop) == {WESTERN, EASTERN, DEEP, NORTHERN}  # the kind's own act's never
    loop.agenda.overflow[2] = actloop.REFUSED
    assert EASTERN not in actloop.picked_shards(loop)  # tried in this game
    loop.done = GAME
    assert actloop.picked_shards(loop) == frozenset()  # the game's end under way
    loop.done = None
    loop.agenda.acts, loop.agenda.overflow[5] = (3, 5), actloop.USED
    assert actloop.picked_shards(loop) == frozenset()  # OVERFLOW_MOST played
    monkeypatch.setattr(actloop, 'OVERFLOW_MOST', None)
    assert actloop.picked_shards(loop) == {WESTERN, DEEP}
    monkeypatch.setattr(actloop, 'PICK_OVER_LIMIT', False)
    assert actloop.picked_shards(loop) == frozenset()
    loop.kind = replace(ACT_KINDS['act3'], key='tz')
    monkeypatch.setattr(actloop, 'PICK_OVER_LIMIT', True)
    assert actloop.picked_shards(loop) == frozenset()  # no act kind


def test_the_pickup_takes_a_full_stacks_shard_with_the_slot_free_and_leaves_other_full_materials(monkeypatch):
    # 15:32:20 on 2026-10-21: "ground: normal Northern Worldstone Shard ...: taken (material)" was the read's verdict;
    # the pickup left it (its stack full: loop.py `sold_full`), only its loot mark after
    from types import SimpleNamespace

    from inventory_tracking.game.records import VALUABLE, Drop, Loot
    from inventory_tracking.items.metadata import metadata
    from inventory_tracking.macros.running import valuables

    [essence] = [
        int(cid) for cid, base in metadata()['bases'].items() if base['name'] == 'Twisted Essence of Suffering'
    ]
    monkeypatch.setattr(actloop, 'SHARD_ALWAYS_PICKED', False)  # the overflow slot's rule alone (2026-10-21)
    game = act_game(monkeypatch)
    loop = game.loop
    loop.agenda.begin(GameId(GAME, 1))
    loop.stash = stash_with({NORTHERN, essence})
    shard = Drop(1, 0.0, 0.0, 'Northern Worldstone Shard', VALUABLE, source='material', txt=NORTHERN)
    other = Drop(2, 0.0, 0.0, 'an essence', VALUABLE, source='material', txt=essence)
    monkeypatch.setattr(valuables, 'taken', lambda loot, mode, tome=None: loot)
    runner = SimpleNamespace(loop=loop, pickup_mode='most')
    loot = Loot(drops=(shard, other))

    def picked() -> list[int]:
        return [drop.unit_id for drop in valuables._picked(runner, loot).drops]  # pyrefly: ignore[bad-argument-type] the fake runner

    assert picked() == []  # before the shard step: as before
    loop.agenda.shard, loop.agenda.acts = actloop.USED, (3,)
    assert picked() == [1]  # the shard, never the essence
    loop.agenda.acts, loop.agenda.overflow[5] = (3, 5), actloop.USED
    assert picked() == []  # the slot taken: left, as before


# 08:59:23 on 2026-10-22 (TZ leveling, Catacombs 4): "ground: normal Eastern Worldstone Shard ...: taken (material)",
# then "pickup: 4 drops (healing) ... nothing to pick up" and Save and Exit with it on the ground. The full stacks were
# runs/alt-d/full-stacks.json's of 23:24 the night before (Eastern 99); the stash read at 08:59:42 had it at 97. The
# player: "I expected it to be picked up for stash (not 99 yet) or used to terrorize whole zone"
def test_every_shard_is_picked_up_and_held_by_the_guard_whatever_its_stack_or_the_kind(monkeypatch):
    from types import SimpleNamespace

    from inventory_tracking.game.records import VALUABLE, Drop, Loot
    from inventory_tracking.items.metadata import metadata
    from inventory_tracking.macros.lootpolicy import GUARD, verdict
    from inventory_tracking.macros.running import valuables

    [essence] = [
        int(cid) for cid, base in metadata()['bases'].items() if base['name'] == 'Twisted Essence of Suffering'
    ]
    eastern = next(shard for shard, act in terrorize.SHARDS.items() if act == 2)
    monkeypatch.setattr(valuables, 'taken', lambda loot, mode, tome=None: loot)
    shard = Drop(1, 0.0, 0.0, 'Eastern Worldstone Shard', VALUABLE, source='material', txt=eastern)
    other = Drop(2, 0.0, 0.0, 'an essence', VALUABLE, source='material', txt=essence)
    loot = Loot(drops=(shard, other))
    for stash in (stash_with({eastern, essence}), stash_with()):  # its stack full, then under the cap
        loop = Loop(on=True, stash=stash)  # the TZ leveling game: no act kind, no overflow slot
        runner = SimpleNamespace(loop=loop, pickup_mode='most')
        picked = valuables._picked(runner, loot).drops  # pyrefly: ignore[bad-argument-type] the fake runner
        assert [drop.unit_id for drop in picked] == ([1] if essence in loop.stash.full() else [1, 2])
        assert verdict(shard, GUARD, room=True, shown=False, looped=True).hold  # the game is not left with it down
    # The switch off: a full stack's shard outside an act kind is left, as at 08:59:26
    monkeypatch.setattr(actloop, 'SHARD_ALWAYS_PICKED', False)
    loop = Loop(on=True, stash=stash_with({eastern}))
    runner = SimpleNamespace(loop=loop, pickup_mode='most')
    assert valuables._picked(runner, Loot(drops=(shard,))).drops == ()  # pyrefly: ignore[bad-argument-type]


def test_a_picked_up_shard_is_used_at_a_waypoint_leg_from_town_but_no_stack_is_opened_there(monkeypatch):
    game = act_game(monkeypatch, stacks={SOUTHERN: 97, NORTHERN: 98})
    assert game.leg() == TZ_SHARD
    game.play.stacks[NORTHERN] = STACK_MOST  # filled up since: no shard carried, no stash walk at a waypoint leg
    assert game.leg() == TZ_WAYPOINT
    assert shard_uses(game) == [('terrorize', 3)]
    game.go('portal', FORTRESS)  # back in town, a picked up Northern carried
    game.play.pack = Pack(items=(Carried(78, NORTHERN, 2, 3, (1, 1)),))
    game.leg()
    assert shard_uses(game)[-1] == ('carried', 5, 78)
    assert game.loop.agenda.acts == (3, 5)


# The coordinator, 2026-10-22, on the rulings ("Overflow shards: one extra act; pick up and use") and the player's "I
# expected it to be picked up for stash (not 99 yet) or used to terrorize whole zone": in TZ leveling a picked-up shard
# whose stack is full terrorizes its act at the next town stop while the extra-act slot is free (OVERFLOW_KINDS)
def tz_game(monkeypatch, stacks: dict[int, int], carried: tuple[Carried, ...]) -> Script:
    from inventory_tracking.macros.loop import TZ

    game = act_game(monkeypatch, stacks=stacks)
    game.loop.kind = TZ
    game.play.pack = Pack(in_cube=carried, cube_items=frozenset(item.unit_id for item in carried))
    game.loop.visiting = GAME
    return game


def test_tz_leveling_uses_a_picked_up_shard_over_the_limit_before_the_visit(monkeypatch, caplog):
    eastern = Carried(81, EASTERN, 0, 0, (1, 1))
    game = tz_game(monkeypatch, {EASTERN: STACK_MOST, NORTHERN: STACK_MOST}, (eastern,))
    visits: list = []

    def visit(exit) -> None:
        visits.append(list(shard_uses(game)))  # used before the visit, which would put it down
        game.loop.visited = GAME

    with caplog.at_level('INFO'):
        assert game.leg(visit=visit) == TOWN
    assert visits == [[('carried', 2, 81)]]  # the carried Eastern; never the Northern from its stack
    assert game.loop.agenda.acts == (2,)
    assert game.play.stacks == {EASTERN: STACK_MOST, NORTHERN: STACK_MOST}
    assert 'Macro: act: Eastern shard over the limit (99), a carried one: act 2 terrorized too' in caplog.text


def test_tz_leveling_keeps_its_shards_with_the_slot_taken_the_stack_under_the_cap_or_the_switch_off(monkeypatch):
    eastern = Carried(81, EASTERN, 0, 0, (1, 1))
    # the slot taken: an act of an over-the-limit shard already played in this game (the bound of 2026-10-21)
    monkeypatch.setattr(actloop, 'OVERFLOW_MOST', 1)
    game = tz_game(monkeypatch, {EASTERN: STACK_MOST, WESTERN: STACK_MOST}, (eastern,))
    game.loop.agenda.begin(GameId(GAME, 1))
    game.loop.agenda.acts, game.loop.agenda.overflow[1] = (1,), actloop.USED
    assert game.leg(visit=lambda exit: setattr(game.loop, 'visited', GAME)) == TOWN
    assert shard_uses(game) == []  # the visit puts the Eastern down
    assert game.loop.agenda.acts == (1,)
    # under the cap: the stash takes it at the visit, no act
    game = tz_game(monkeypatch, {EASTERN: 97}, (eastern,))
    assert game.leg(visit=lambda exit: setattr(game.loop, 'visited', GAME)) == TOWN
    assert shard_uses(game) == []
    assert game.loop.agenda.acts == ()
    # the switch off: the overflow is the act kinds' alone, as before
    monkeypatch.setattr(actloop, 'OVERFLOW_KINDS', frozenset())
    game = tz_game(monkeypatch, {EASTERN: STACK_MOST}, (eastern,))
    assert game.leg(visit=lambda exit: setattr(game.loop, 'visited', GAME)) == TOWN
    assert shard_uses(game) == []


# -- every overflow shard used (2026-10-22; the player: "no save/exits on games with worldstone hards spent! you must
# finish the game correctly => all levels + use all overflow shards => maybe more acts + rotating TZ"; ~21:00 "why we
# don't use northern shards and just ddroppped them"; rca/2026-10-22/overflow-findings.md) ---------------------------


def test_the_rulings_switches_of_2026_10_22_are_on():
    assert actloop.OVERFLOW_MOST is None  # every act over the limit, no longer "one extra act"
    assert actloop.CARRIED_COUNT
    assert actloop.SPARE_USABLE
    assert actloop.END_USE


def northern(unit: int, x: int = 0, y: int = 0) -> Carried:
    return Carried(unit, NORTHERN, x, y, (1, 1))


@pytest.mark.parametrize(
    ('stack', 'carried', 'over'),
    [
        (98, 3, True),  # game cyberg65 at 20:07:59: room for one, three carried
        (98, 2, True),
        (98, 1, False),  # the stash takes it
        (97, 2, False),
        (99, 0, True),  # the stack at the cap: an act kind takes one from it, as before
        (99, 1, True),
        (60, 5, False),
    ],
)
def test_a_carried_shard_counts_toward_its_stack(stack, carried, over):
    held = tuple(northern(100 + n) for n in range(carried))
    assert (NORTHERN in terrorize.over_limit(view(northern=stack), held)) is over
    assert terrorize.over_limit(view(northern=stack)) == ((NORTHERN,) if stack >= STACK_MOST else ())  # the stack's own


def test_the_count_switch_off_reads_the_stack_alone(monkeypatch):
    monkeypatch.setattr(actloop, 'CARRIED_COUNT', False)
    assert actloop.overflow_due(view(northern=98), Agenda(acts=(1,)), 1, (northern(1), northern(2))) == ()


# Game cyberg65 ("Shard: Act 1", act 1 terrorized by a Western at 18:59:15), the visit of 20:07:55 in the Fortress
# (runs/alt-d/20261022T164938Z-2f4f5df0, visits/200759.json): the Northern stack at 98, three Northerns carried
# (348915677 in the inventory, 3140070632 and 2239401155 in the cube); no `shard over the limit` line, the stash took
# 3140070632 (99) and the other two were put down (20:08:06, 20:08:13-14)
CYBERG65 = (northern(348915677, 4, 3),)
CYBERG65_CUBE = (northern(3140070632, 2, 0), northern(2239401155, 2, 2))


def cyberg65(monkeypatch, stacks: dict[int, int] | None = None) -> Script:
    """The act 1 game after its shard step (act 1 terrorized), its visit due, the three Northerns carried."""
    game = act_game(monkeypatch, act=1, stacks={WESTERN: 96, NORTHERN: 98})
    assert game.leg() == TZ_SHARD
    assert shard_uses(game) == [('terrorize', 1)]
    game.play.stacks.update(stacks or {})
    game.play.pack = Pack(
        items=CYBERG65, in_cube=CYBERG65_CUBE, cube_items=frozenset(item.unit_id for item in CYBERG65_CUBE)
    )
    game.loop.visiting = GAME
    return game


def test_cyberg65_the_visit_uses_a_carried_northern_before_the_stash_and_act_5_is_owed(monkeypatch, caplog):
    game = cyberg65(monkeypatch)
    before: list = []

    def visit(exit) -> None:
        before.append(list(shard_uses(game)))  # what was used before the stash step
        game.loop.visited = GAME

    with caplog.at_level('INFO'):
        assert game.leg(visit=visit) == TOWN
    assert before == [[('terrorize', 1), ('carried', 5, 348915677)]]  # the inventory's first
    assert game.loop.agenda.acts == (1, 5)
    assert game.loop.agenda.overflow == {5: actloop.USED}
    assert 'Macro: act: Northern shard over the limit (98), a carried one: act 5 terrorized too' in caplog.text
    game.leg()
    assert 'Act5-Manual' in zones_of(game)  # its levels planned, after act 1's


def test_a_second_northern_after_act_5_falls_said_while_another_full_acts_shard_is_used_too(monkeypatch, caplog):
    monkeypatch.setattr(actloop, 'NORTHERN_FOR_BAAL', False)  # the spare Northern: test_loop_baal_northern.py
    # Two carried Northerns over the cap and a Deep over its own: act 5 once, act 4 too; the second Northern has no use
    deep = Carried(93, DEEP, 5, 3, (1, 1))
    game = cyberg65(monkeypatch, {NORTHERN: STACK_MOST, DEEP: STACK_MOST})
    game.play.pack = Pack(
        items=(deep, *CYBERG65), in_cube=CYBERG65_CUBE[1:], cube_items=frozenset({CYBERG65_CUBE[1].unit_id})
    )
    assert game.leg(visit=lambda exit: setattr(game.loop, 'visited', GAME)) == TOWN
    assert shard_uses(game)[1:] == [('carried', 4, 93), ('carried', 5, 348915677)]  # the acts after act 1 first
    assert game.loop.agenda.acts == (1, 4, 5)
    second = CYBERG65_CUBE[1]
    with caplog.at_level('INFO'):
        assert actloop.spared(game.loop, second, lambda: game.play.pack) is None
    assert (
        'Macro: act: the Northern Worldstone Shard (unit 2239401155) may be put down: act 5 is terrorized in this game '
        'already' in caplog.text
    )


def test_a_usable_shard_is_spared_one_a_class_and_only_while_the_game_can_use_it(monkeypatch):
    monkeypatch.setattr(actloop, 'NORTHERN_FOR_BAAL', False)  # the spare Northern: test_loop_baal_northern.py
    game = act_game(monkeypatch, act=1, stacks={WESTERN: 96, NORTHERN: STACK_MOST})
    loop = game.loop
    loop.agenda.begin(GameId(GAME, 1))
    first, second = northern(1, 0, 0), northern(2, 1, 0)
    pack = Pack(items=(first,), in_cube=(second,), cube_items=frozenset({2}))
    read = lambda: pack  # ruff: ignore[lambda-assignment]
    # Before the game's own shard step: the overflow comes after it, so the Northern waits for it
    assert actloop.spared(loop, first, read) == 'a Northern Worldstone Shard act 5 can still use in this game'
    assert actloop.spared(loop, second, read) is None  # another is kept for act 5
    western = Carried(3, WESTERN, 2, 0, (1, 1))
    # The kind's own act: kept for the next game's act 1 (OWN_CARRIED, 2026-10-23); off, it falls as before
    assert actloop.spared(
        loop, western, lambda: Pack(items=(first, western), in_cube=(second,), cube_items=frozenset({2}))
    ) == ("a Western Worldstone Shard kept for the next game's act 1 (OWN_CARRIED)")
    another = Carried(5, WESTERN, 3, 0, (1, 1))
    both = lambda: Pack(items=(first, western, another), in_cube=(second,), cube_items=frozenset({2}))  # ruff: ignore[lambda-assignment]
    assert actloop.spared(loop, another, both) is None  # a second copy falls
    monkeypatch.setattr(actloop, 'OWN_CARRIED', False)
    assert actloop.spared(loop, western, read) is None  # its shard from its stack
    monkeypatch.setattr(actloop, 'OWN_CARRIED', True)
    loop.agenda.shard, loop.agenda.acts = actloop.USED, (1,)
    assert actloop.spared(loop, first, read) is not None
    loop.agenda.overflow[5] = actloop.REFUSED  # the game refused it
    assert actloop.spared(loop, first, read) is None
    loop.agenda.overflow[5] = actloop.FAILED  # a stop, no refusal: kept (the next game uses it)
    assert actloop.spared(loop, first, read) is not None
    loop.agenda.acts = (1, 5)
    assert actloop.spared(loop, first, read) is None  # act 5 terrorized
    loop.agenda.acts, loop.agenda.overflow = (1,), {}
    for state in (actloop.JOINED, actloop.GIVEN_UP, actloop.CLICKS_OFF):  # no shard risked in the game
        loop.agenda.shard = state
        assert actloop.spared(loop, first, read) is None
    loop.agenda.shard = actloop.USED
    from inventory_tracking.macros.loop import LK

    loop.kind = LK  # no shard use at all
    assert actloop.spared(loop, first, read) is None
    loop.kind = ACT_KINDS['act1']
    assert actloop.spared(loop, Carried(4, 610, 0, 0, (1, 1)), read) is None  # not a shard
    monkeypatch.setattr(actloop, 'SPARE_USABLE', False)
    assert actloop.spared(loop, first, read) is None


def test_a_restart_mid_game_keeps_the_overflow_state_and_the_next_visit_uses_the_shard(monkeypatch):
    from inventory_tracking.terror.tracker import ZoneTracker

    game = cyberg65(monkeypatch)
    kept = midgame.snapshot(game.loop, game.progress)
    assert kept is not None
    assert kept['agenda']['shard'] == actloop.USED
    assert kept['agenda']['acts'] == [1]
    # The service restarted (20:26, 20:38 ... on 2026-10-22): a new loop takes the game's record up at its first leg
    loop = Loop(on=True, kind=ACT_KINDS['act1'], chosen=True)
    loop.start()
    loop.records = ZoneTracker()
    loop.records.record_note(f'{GAME}#1', 'loop', {name: value for name, value in kept.items() if name != 'at'})
    loop.visiting = GAME
    game.loop = loop
    game.progress = Progress(ROUTES, PERFORMED, lambda: frozenset(game.killed), wanted=lambda a: a in game.zone)
    game.progress.note(GAME, game.area)
    assert game.leg(visit=lambda exit: setattr(loop, 'visited', GAME)) == TOWN
    assert loop.agenda.shard == actloop.USED  # taken up: never a second shard for act 1
    assert shard_uses(game)[1:] == [('carried', 5, 348915677)]
    assert loop.agenda.acts == (1, 5)
    record = loop.records.record(f'{GAME}#1')['loop']['agenda']
    assert record['acts'] == [1, 5]  # in the record at once (midgame.keep)
    assert record['overflow'] == [[5, actloop.USED]]


def test_a_carried_shard_at_the_games_end_visit_is_used_and_the_game_goes_on(monkeypatch, caplog):
    game = cyberg65(monkeypatch, {NORTHERN: STACK_MOST})
    game.play.pack = Pack(items=CYBERG65)
    game.loop.done = GAME  # the game's end under way: its last visit
    exits: list = []

    def visit(exit) -> None:
        exits.append(exit)
        game.loop.visited = GAME

    with caplog.at_level('INFO'):
        assert game.leg(visit=visit) == TOWN
    assert shard_uses(game)[1:] == [('carried', 5, 348915677)]
    assert exits == [Exit.WAYPOINT]  # not Save and Exit
    assert game.loop.done is None
    assert game.loop.agenda.acts == (1, 5)
    assert 'Macro: act: the game goes on: act 5 terrorized at its end by a carried shard over the limit' in caplog.text


def test_save_and_exit_in_a_town_uses_a_carried_shard_first_and_the_game_is_not_left(monkeypatch):
    from inventory_tracking.macros import tzloop
    from inventory_tracking.macros.agenda import EXCURSION, LEAVE_GAME, Objective
    from tests.inventory_tracking.macros.test_tzloop import keys

    game = cyberg65(monkeypatch, {NORTHERN: STACK_MOST})
    game.play.pack = Pack(items=CYBERG65)
    end = Objective(LEAVE_GAME, 'no goals left', EXCURSION)
    tzloop.perform(game.loop, game.play.run(), keys, game.progress, end, game.hands())
    assert 'Save and Exit' not in game.play.said
    assert game.loop.agenda.acts == (1, 5)
    # Nothing left to use: the end is the end
    monkeypatch.setattr(tzloop, 'owed', lambda agenda: None)
    left: list = []
    monkeypatch.setattr(game.loop, 'leave', lambda run, name: left.append(name))
    game.play.pack = Pack(items=CYBERG65)  # the one used is gone, a second Northern has no use
    tzloop.perform(game.loop, game.play.run(), keys, game.progress, end, game.hands())
    assert left == [GAME]
    assert len(shard_uses(game)) == 2


def test_with_the_end_switch_off_the_games_end_uses_no_shard(monkeypatch):
    monkeypatch.setattr(actloop, 'END_USE', False)
    game = cyberg65(monkeypatch, {NORTHERN: STACK_MOST})
    game.play.pack = Pack(items=CYBERG65)
    game.loop.done = GAME
    exits: list = []
    assert game.leg(visit=lambda exit: (exits.append(exit), setattr(game.loop, 'visited', GAME))) == TOWN
    assert shard_uses(game)[1:] == []
    assert exits == [Exit.LEAVE]
