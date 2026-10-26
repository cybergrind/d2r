"""The Act 2 TZ leveling kind (`act2tz`, macros/loop.py ACT2_TZ; macros/acts/act2.py TZ_LEVELING_STEPS). The player,
2026-10-25 ~17:15: "act 2 tz leveling: use worlstone shard for act 2 / go all canyon of the magi + all tals rasha tombs
(small + kaa + duriel) / go full arcane sanctuary (+kill summoner)"; ~17:47: "I want to have separate Act 2 TZ Leveling
with tal rasha's and arcane sanctuary". Its game: the Eastern shard, the Canyon and its seven tombs with Duriel's Lair
from the true tomb, the Arcane Sanctuary toured whole and the Summoner, then the game's end: no Palace Cellars, Harem,
sewers, rest of the act, rotation or other act's shard. "Shard: Act 2" (`act2`) and TZ leveling stay as before."""

import pytest

from inventory_tracking.game.records import Carried, StashView
from inventory_tracking.macros import actloop, kindpick, tzroutine, zonenav
from inventory_tracking.macros.acts import act2
from inventory_tracking.macros.agenda import FULL_CLEAR, NEW_GAME, PLUS, PLUS_WAY, Agenda
from inventory_tracking.macros.loop import ACT2_TZ, ACT_KINDS, LEAVE, TZ, TZ_KINDS, TZ_SHARD, loop_kinds
from inventory_tracking.routes.tz_groups import manual_zone
from tests.inventory_tracking.macros.acts.harness import TRUE_TOMB, ActGame, force_ready, trips_of
from tests.inventory_tracking.macros.acts.test_act2 import tomb_entrances
from tests.inventory_tracking.macros.test_tzloop import CANYON, CATACOMBS, LUT_GHOLEIN, NEAREST, TOMBS


LAIR, SANCTUARY = 73, 74
WESTERN, EASTERN = 674, 675  # misc.txt xa1, xa2 (terrorize.py SHARDS)


@pytest.fixture(autouse=True)
def caches_cleared():
    tzroutine.itinerary.cache_clear()
    zonenav.graph_of.cache_clear()
    yield
    tzroutine.itinerary.cache_clear()
    zonenav.graph_of.cache_clear()


def plan(monkeypatch, order: tuple[int, ...], alone: bool):
    force_ready(monkeypatch, 2)
    zone = manual_zone(2)
    assert zone is not None
    found = tzroutine.itinerary(zone.core | CATACOMBS, order, alone)
    assert found is not None
    return found


# The kinds offered before Act 2 TZ leveling (2026-10-25 ~17:50), keys and names in the picker's order. The player: "you
# must not touch any existing entries"
EXISTING = [
    ('lk', 'Lower Kurast'),
    ('andariel', 'Andariel'),
    ('baal', 'Baal'),
    ('tz', 'TZ leveling'),
    ('tzclear', 'Full clear TZ'),
    *((f'act{act}', f'Shard: Act {act}') for act in range(1, 6)),
]


def test_the_existing_kinds_are_as_they_were_and_the_new_one_comes_last():
    kinds = loop_kinds()
    assert [(key, kind.name) for key, kind in kinds.items()] == [*EXISTING, ('act2tz', 'Act 2 TZ leveling')]
    assert [row.key for row in kindpick.entries()] == [*(key for key, _ in EXISTING), 'act2tz']
    assert [kind.word for kind in kinds.values()] == [
        'LK', 'AND', 'BAAL', 'TZ+', 'TZC', 'ACT1', 'ACT2', 'ACT3', 'ACT4', 'ACT5', 'A2TZ'
    ]  # fmt: skip
    assert not any(kind.alone for key, kind in kinds.items() if key != 'act2tz')


def test_shard_act_2s_trips_are_the_ones_of_before(monkeypatch):
    # "Shard: Act 2" in its own game (the act first: the order (2,)): the whole act, then the rotation, as before
    from tests.inventory_tracking.macros.acts.test_act2 import PLAN

    found = plan(monkeypatch, (2,), alone=False)
    assert PLAN.startswith(f'Macro: tz: zone {found.zone}: {tzroutine.trips_said(found.excursions)}')
    assert not any(trip.whole for trip in found.excursions)


def test_the_kind_is_offered_with_its_own_name_and_word():
    kinds = loop_kinds()
    assert kinds['act2tz'] is ACT2_TZ
    assert (ACT2_TZ.name, ACT2_TZ.word, ACT2_TZ.alone) == ('Act 2 TZ leveling', 'A2TZ', True)
    assert not ACT_KINDS['act2'].alone
    assert not TZ.alone
    assert ACT2_TZ.key in TZ_KINDS
    assert list(kinds)[-1] == 'act2tz'  # last: the existing entries' order unchanged
    rows = kindpick.entries()
    row = next(row for row in rows if row.key == 'act2tz')
    assert (row.name, row.word, row.enabled) == ('Act 2 TZ leveling', 'A2TZ', True)
    assert actloop.act_of(ACT2_TZ) == 2  # the Eastern shard
    assert act2.SCRIPT.whole == frozenset((SANCTUARY,))
    assert tzroutine.WHOLE == PLUS


def test_the_kinds_plan_is_the_tombs_and_the_sanctuary_only(monkeypatch, caplog):
    with caplog.at_level('INFO'):
        alone = plan(monkeypatch, (2,), alone=True)
    assert trips_of(alone) == [
        ("Tal Rasha's Tombs", 46, (46, *TOMBS, LAIR)),  # the Canyon, every tomb, Duriel from the true one
        ('Summoner', 74, (74,)),  # the Arcane Sanctuary from its waypoint, the Summoner
    ]  # no Palace Cellars, Harem, sewers, rest of the act, no rotation (the Catacombs read with it)
    assert alone.zone == 'Act2-Manual'
    assert alone.skipped == ()
    assert 'Macro: act: act 2 alone (Act 2 TZ leveling)' in caplog.text
    tombs, sanctuary = alone.excursions
    assert tombs.whole == frozenset()
    assert sanctuary.whole == frozenset((SANCTUARY,))
    # "full arcane sanctuary": its rooms toured (TZ+), not the way to the Summoner only (tz+ on the way, a big level)
    assert tzroutine.policy_of(SANCTUARY, sanctuary) == PLUS
    assert tzroutine.policy_of(SANCTUARY, tzroutine.replace(sanctuary, whole=frozenset())) == PLUS_WAY
    assert {tzroutine.policy_of(area, tombs) for area in (CANYON, *TOMBS, LAIR)} == {PLUS}  # "all canyon", "all tombs"
    assert tzroutine.policy_of(SANCTUARY, sanctuary, full_clear=True) == FULL_CLEAR


def test_shard_act_2_and_act_2_elsewhere_play_the_whole_order(monkeypatch):
    # "Shard: Act 2" (its own act first, no alone), terrorized by hand, another act kind's overflow act: as before
    for order in ((2,), (), (1, 2)):
        tzroutine.itinerary.cache_clear()
        found = plan(monkeypatch, order, alone=False)
        routes = [trip.route for trip in found.excursions]
        assert {'Radament', 'Harem', 'Halls of the Dead', 'Andariel'} <= set(routes), order
        assert not any(trip.whole for trip in found.excursions)


@pytest.mark.parametrize('graph', [False, True], ids=['itinerary', 'zone navigation'])
def test_a_game_is_the_shard_the_tombs_duriel_the_sanctuary_and_the_games_end(monkeypatch, graph):
    if graph:
        monkeypatch.setattr(zonenav, 'ACTS', frozenset({2}))  # zone navigation on for act 2, as live
    act = ActGame(2, monkeypatch)
    act.game.loop.kind = ACT2_TZ
    tomb_entrances(act)
    walk = act.play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.legs[0] == TZ_SHARD
    assert walk.shard == [2]
    third = NEAREST.index(TRUE_TOMB) + 1
    assert walk.runs == [CANYON, *NEAREST[:third], LAIR, *NEAREST[third:], SANCTUARY]  # each level once, nothing more
    assert walk.kills == ['Duriel', 'The Summoner']
    home = ('portal', LUT_GHOLEIN)
    assert walk.moves[0] == ('waypoint', CANYON)
    assert walk.moves[-2:] == [home, ('waypoint', SANCTUARY)]  # Save and Exit from the Arcane Sanctuary
    assert walk.legs[-1] == LEAVE


def test_a_shard_act_2_game_still_plays_the_act_and_the_rotation(monkeypatch):
    act = ActGame(2, monkeypatch)
    tomb_entrances(act)
    walk = act.play()
    assert walk.stopped is None, (walk.stopped, walk.where)
    assert {52, 49, 47, 35} <= set(walk.runs)  # the Palace Cellars, Radament's sewers, Sewers 1, the rotation


def test_the_kinds_game_uses_no_shard_over_the_limit():
    full = StashView((), ((WESTERN, 99), (EASTERN, 99)))
    agenda = Agenda()
    assert actloop.alone(ACT2_TZ)
    assert not actloop.alone(ACT_KINDS['act2'])
    assert not actloop.alone(TZ)
    assert not actloop.alone(None)
    assert actloop.overflow_due(full, agenda, 2, alone=True) == ()  # its game: no other act
    assert [act for act, _ in actloop.overflow_due(full, agenda, 2)] == [1]  # Shard: Act 2's game: as before
    eastern = Carried(1, EASTERN, 0, 0, (1, 1))
    # TZ leveling: a carried Eastern over the limit is its overflow act, as before
    assert [act for act, _ in actloop.overflow_due(full, agenda, None, (eastern,), carried_only=True)] == [2]


# -- no other level, no other shard (the player, 2026-10-25 ~19:12: "act 2 tz leveling must do the: - use shard for act
# 2 - canyon of the magi - all tal rasha tombs - duriel - arcane sanctuary + summoner - loop"; "no other levels, no
# other shards"): a game whose act 2 is not terrorized ends unplayed, the loop stops where no shard can be used

CATACOMBS_2 = 35


def lobby_choice(loop):
    """The loop's next goal in the lobby (tzloop.py `choose`)."""
    from types import SimpleNamespace

    from inventory_tracking.macros import tzloop

    return tzloop.choose(SimpleNamespace(in_game=False), None, loop, None)  # pyrefly: ignore[bad-argument-type]


def test_a_game_joined_in_a_field_level_is_left_unplayed_and_the_next_game_takes_the_shard(monkeypatch, caplog):
    from inventory_tracking.macros.tzloop import ALONE_ENDS

    act = ActGame(2, monkeypatch, area=CATACOMBS_2)  # a TZ leveling game, mid-way in the Catacombs
    act.game.loop.kind = ACT2_TZ
    with caplog.at_level('INFO'):
        walk = act.play(legs=10)
    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.shard == []  # no shard in a field level
    assert walk.runs == []  # no zone of it played: the Catacombs' rotation neither
    assert walk.legs == [LEAVE]
    assert act.game.loop.agenda.shard == actloop.JOINED
    said = 'Macro: act: Act 2 TZ leveling: the game was joined in a field level, act 2 not terrorized: the game ends'
    assert said in caplog.text
    assert lobby_choice(act.game.loop).kind == NEW_GAME  # the next game, the loop on
    assert ALONE_ENDS in tzloop_unplayed()


def tzloop_unplayed() -> frozenset[str]:
    from inventory_tracking.macros.tzloop import UNPLAYED

    return UNPLAYED


# The Eastern's floor (2026-10-26 ~09:05, the player, the Eastern stack at 89: "Floor 40: Act 2 TZ leveling uses Eastern
# shards down to 40, as the Northern for Baal does ('floor is 40, use up to it')"): one taken while the stack holds
# more than 40 (game/stash.py EASTERN_FLOOR, actloop.py `own_floor`), as the Baal game's Northern


@pytest.mark.parametrize('shards', [89, 41])
def test_an_eastern_stack_over_40_gives_the_kinds_shard(monkeypatch, shards):
    floors: list[int] = []
    act = ActGame(2, monkeypatch, shards=shards)
    act.game.loop.kind = ACT2_TZ
    given = actloop.terrorize

    def used(run, key, used_act, terrorized, floor=0):
        floors.append(floor)
        return given(run, key, used_act, terrorized)

    monkeypatch.setattr(actloop, 'terrorize', used)
    act.play(legs=3)
    assert act.shard == [2]
    assert floors == [41]
    assert act.game.loop.agenda.shard == actloop.USED
    assert actloop.own_floor(ACT2_TZ) == 41
    assert actloop.own_floor(ACT_KINDS['act2']) == actloop.SHARD_FLOOR == 90  # "Shard: Act 2" and the others: 90


@pytest.mark.parametrize('shards', [40, 0])
def test_no_eastern_at_the_floor_ends_the_game_and_stops_the_loop_in_the_lobby(monkeypatch, caplog, shards):
    from inventory_tracking.macros.actuator import Abort

    act = ActGame(2, monkeypatch, shards=shards)
    act.game.loop.kind = ACT2_TZ
    with caplog.at_level('INFO'):
        walk = act.play(legs=10)
    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.legs == [TZ_SHARD, LEAVE]  # the shard step finds none: the game ends, no rotation
    assert walk.shard == []
    assert walk.runs == []
    assert 'Macro: act: no shard for act 2 at 41 or more' in caplog.text
    assert 'the game ends unplayed (its kind plays no other level)' in caplog.text
    with pytest.raises(Abort) as stop:
        lobby_choice(act.game.loop)
    assert str(stop.value) == (
        'no Eastern Worldstone Shard at 41+ for Act 2 TZ leveling: the loop stops for the player to pick another kind'
    )
    assert stop.value.cause == 'idle'  # stops.py: STOP
    assert lobby_choice(act.game.loop).kind == NEW_GAME  # said once: the player's turn-on goes on


def test_a_shard_that_did_not_take_ends_the_game_and_after_two_in_a_row_the_loop_stops(monkeypatch, caplog):
    from inventory_tracking.macros.actuator import Abort

    act = ActGame(2, monkeypatch, outcome='failed')
    act.game.loop.kind = ACT2_TZ
    with caplog.at_level('INFO'):
        walk = act.play(legs=10)
    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.shard == [2]  # tried
    assert walk.runs == []  # no rotation
    assert walk.legs[-1] == LEAVE
    agenda = act.game.loop.agenda
    assert (agenda.shard, agenda.shard_failures) == (actloop.FAILED, 1)
    assert 'Act 2 TZ leveling: the Eastern Worldstone Shard did not take, the next game tries again' in caplog.text
    assert lobby_choice(act.game.loop).kind == NEW_GAME  # one failure: the next game tries again
    # Two in a row: the next game's shard step gives up, the game ends, the loop stops in the lobby
    again = ActGame(2, monkeypatch, outcome='failed')
    again.game.loop.kind = ACT2_TZ
    again.game.loop.agenda.shard_failures = actloop.SHARD_FAILURES
    walk = again.play(legs=10)
    assert walk.shard == []
    assert walk.runs == []
    assert walk.legs == [LEAVE]
    with pytest.raises(Abort) as stop:
        lobby_choice(again.game.loop)
    assert str(stop.value).startswith(
        'the Eastern Worldstone Shard did not take 2 games in a row: no Act 2 TZ leveling'
    )


def test_shard_act_2_without_a_shard_still_plays_the_rotation(monkeypatch, caplog):
    with caplog.at_level('INFO'):
        walk = ActGame(2, monkeypatch, shards=89).play(legs=4)
    assert walk.shard == []
    assert 'Macro: act: no shard for act 2 at 90 or more' in caplog.text
    assert 'TZ+ on the rotation this game' in caplog.text  # as before
    assert walk.runs  # the rotation's levels


def test_the_plan_holds_act_2_alone_whatever_rotation_is_read(monkeypatch):
    # The rotation read in act 2 itself (the Tal Rasha's zone, the Far Oasis), or nothing but the act read
    force_ready(monkeypatch, 2)
    zone = manual_zone(2)
    assert zone is not None
    from inventory_tracking.routes.tz_groups import installed_active_zones

    act2_rotations = [each for each in installed_active_zones() if each.name.startswith('Act2-')]
    assert act2_rotations
    for read in (frozenset(), *(each.core for each in act2_rotations), CATACOMBS):
        tzroutine.itinerary.cache_clear()
        found = tzroutine.itinerary(zone.core | read, (2,), True)
        assert found is not None
        assert found.zone == 'Act2-Manual'
        assert {area for trip in found.excursions for area in trip.areas} == {CANYON, *TOMBS, LAIR, SANCTUARY}
