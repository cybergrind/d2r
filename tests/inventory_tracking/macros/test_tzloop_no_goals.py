"""The "no goals left" stop with act bosses alive (game cybergg10, 2026-10-24 19:32:37 and the loop turned on again at
19:34:01; rca/2026-10-24/no-goals-stop-findings.md): a shard game whose act 1 an overflow shard terrorized mid-game, the
Outer Steppes' run ending with no way on into the Plains of Despair (agenda.py `no_way_on`), then the agenda. Before
the fix the empty queue ended the game, `unrouted` blocked every owed level, Andariel's among them, and the loop
stopped; turned on again it stopped at once (tzloop.py WAYLESS_BLOCKS, UNROUTED_AFTER_BOSSES)."""

import pytest

from inventory_tracking.macros import tzloop, zonenav
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.loop import LEAVE, TZ_PORTAL, TZ_WAYPOINT, GameId
from inventory_tracking.routes.tz_groups import manual_zone
from tests.inventory_tracking.macros.test_tzloop import GAME, Script


STEPPES, PLAINS = 104, 105
ANDARIEL = (35, 36, 37)  # Catacombs 2-4: the waypoint's level, Level 3, her Level 4
STOPPED = 'no goals left, but Andariel (Catacombs Level 4) alive: the loop stops here for the player'


def steppes_game(monkeypatch: pytest.MonkeyPatch) -> Script:
    """Act 4's shard game in the Outer Steppes, the rest of act 4 done (Diablo and the seal bosses dead), act 1
    terrorized mid-game by an overflow shard (actloop.py OVERFLOW / END_USE: its act added to `Agenda.acts`) and all of
    it done but Andariel's levels; the Steppes' run over with no way on into the Plains (the fight in the way)."""
    act1, act4 = manual_zone(1), manual_zone(4)
    assert act1 is not None
    assert act4 is not None
    monkeypatch.setattr(zonenav, 'ACTS', frozenset({1, 2, 3, 4, 5}))  # as served: every act by the zone's graph
    game = Script(STEPPES, monkeypatch, zone=frozenset(act1.areas) | frozenset(act4.areas))
    agenda, loop = game.loop.agenda, game.loop
    loop.game_id = GameId(GAME, 1)
    agenda.begin(loop.game_id)
    agenda.shard, agenda.acts = 'used', (4,)
    game.killed.update(('Diablo', 'Grand Vizier of Chaos', 'Lord De Seis', 'Infector of Souls'))
    agenda.kept = set(act4.areas) - {STEPPES, PLAINS}
    # The overflow shard over the limit: act 1 terrorized too, played after act 4 (19:31:35)
    agenda.acts, agenda.overflow = (4, 1), {1: 'used'}
    agenda.kept |= set(act1.areas) - set(ANDARIEL)
    agenda.entered |= agenda.kept  # done before (the game's record: entered, cleared)
    agenda.worked.update(dict.fromkeys(agenda.kept, 9))  # their other bosses' runs spent (STOPS_FOR_ACT_BOSSES)
    # The Steppes' run: every room seen, the way into the Plains never made (19:32:37)
    agenda.entered.add(STEPPES)
    agenda.mapped.add(STEPPES)
    agenda.explored.add(STEPPES)
    agenda.ran(STEPPES)
    agenda.no_way_on(STEPPES)

    def run_of(area: int) -> None:
        if area == ANDARIEL[-1]:
            game.killed.add('Andariel')

    game.on_run = run_of
    return game


def legs_until_left(game: Script, count: int = 30) -> list[str]:
    legs: list[str] = []
    for _ in range(count):
        if not game.play.world.in_game:
            break
        legs.append(game.leg())
        if legs[-1] == LEAVE:
            break
    return legs


def test_no_way_on_from_the_steppes_goes_on_to_andariel_and_the_game_ends_after_her(monkeypatch, caplog):
    game = steppes_game(monkeypatch)
    with caplog.at_level('INFO'):
        legs = legs_until_left(game)
    assert legs[:2] == [TZ_PORTAL, TZ_WAYPOINT]  # Town Portal for the next part of the zone, the waypoint to her act
    assert game.calls[1] == ('waypoint', ANDARIEL[0])
    assert 'Andariel' in game.killed
    assert legs[-1] == LEAVE  # the game ends once she is dead
    assert PLAINS not in game.runs
    assert all(level not in game.loop.agenda.blocked for level in ANDARIEL)
    assert 'the loop stops' not in caplog.text


def test_before_the_fix_the_wayless_steppes_stopped_the_loop_and_the_loop_turned_on_again_stopped_at_once(monkeypatch):
    monkeypatch.setattr(tzloop, 'WAYLESS_BLOCKS', False)
    monkeypatch.setattr(tzloop, 'UNROUTED_AFTER_BOSSES', False)
    game = steppes_game(monkeypatch)
    with pytest.raises(Abort) as first:
        game.leg()
    assert str(first.value) == STOPPED
    assert first.value.cause == 'idle'
    agenda = game.loop.agenda
    assert all(agenda.blocked[level].startswith(tzloop.UNROUTED) for level in ANDARIEL)  # the record's
    game.loop.start()  # the loop turned on again in the same game (19:34:01)
    with pytest.raises(Abort) as again:
        game.leg()
    assert str(again.value) == STOPPED
    assert game.calls == []  # never left the Steppes


def test_the_loop_turned_on_again_after_the_stop_routes_to_andariel(monkeypatch, caplog):
    # The old service's stop and its record (the unrouted blocks, the Steppes wayless), then today's code at the next
    # leg (a loop-on, or a restart taking the record up): the blocks dropped, the zone goes on to her
    monkeypatch.setattr(tzloop, 'WAYLESS_BLOCKS', False)
    monkeypatch.setattr(tzloop, 'UNROUTED_AFTER_BOSSES', False)
    game = steppes_game(monkeypatch)
    with pytest.raises(Abort):
        game.leg()
    agenda = game.loop.agenda
    unrouted = {level for level, why in agenda.blocked.items() if why.startswith(tzloop.UNROUTED)}
    assert set(ANDARIEL) <= unrouted
    monkeypatch.setattr(tzloop, 'WAYLESS_BLOCKS', True)
    game.loop.start()  # turned on again
    with pytest.raises(Abort, match='Andariel'):
        game.leg()  # the Plains blocked alone: her levels still blocked by the record, the same stop
    monkeypatch.setattr(tzloop, 'UNROUTED_AFTER_BOSSES', True)
    game.loop.start()
    with caplog.at_level('INFO'):
        legs = legs_until_left(game)
    assert 'the levels blocked as unrouted are routed again' in caplog.text
    assert legs[:2] == [TZ_PORTAL, TZ_WAYPOINT]
    assert 'Andariel' in game.killed
    assert legs[-1] == LEAVE


def test_no_level_is_blocked_unrouted_while_an_act_boss_is_alive(monkeypatch):
    monkeypatch.setattr(tzloop, 'WAYLESS_BLOCKS', False)  # the empty queue's game end, as live
    game = steppes_game(monkeypatch)
    with pytest.raises(Abort) as stopped:
        game.leg()
    assert 'Andariel (Catacombs Level 4) alive' in str(stopped.value)  # BOSS_STAYS kept: the game is not left
    assert not any(why.startswith(tzloop.UNROUTED) for why in game.loop.agenda.blocked.values())
    assert 'Save and Exit' not in game.play.said
