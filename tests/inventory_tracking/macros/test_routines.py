from dataclasses import replace

import pytest

from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.routines import (
    SHOW_ITEMS_TRIES,
    prebuff,
    run_macro,
    screen_fraction,
    show_items_on,
)
from inventory_tracking.macros.world import Monster
from tests.inventory_tracking.macros.fakes import KEYS, OTHER_SET, PREBUFF_SET, Game, player, world


BOUND_DEMON = Monster(50, 700, 1, 4995.0, 5003.0, 0xFFFFFFFF)  # summons carry no owner (host, 2026-10-06)


def test_prebuff_consumes_its_own_defiler_and_keeps_the_bound_demon():
    game = Game(world(monsters=(BOUND_DEMON,)))
    prebuff(game.run())
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']
    assert game.character.consume
    assert [m.txt_id for m in game.world.monsters] == [700, 744]


DEFILER = Monster(60, 744, 1, 5006.0, 4996.0, 0xFFFFFFFF)


@pytest.mark.parametrize(
    ('consume', 'monsters', 'keys'),
    [
        (True, (DEFILER,), ['6', 'q', 'g', 'r']),  # both there: the buff may be about to run out
        (True, (), ['q', '6', 'q', 'g', 'r']),
        (False, (DEFILER,), ['6', 'q', 'g', 'r']),  # a standing Defiler is consumed, not summoned over
        (False, (), ['q', '6', 'q', 'g', 'r']),
    ],
)
def test_prebuff_always_casts_consume_and_ends_buffed_with_one_defiler(consume, monsters, keys):
    game = Game(world(player=player(consume=consume), monsters=monsters))
    prebuff(game.run())
    assert game.pressed() == keys
    assert game.character.consume
    assert [m.txt_id for m in game.world.monsters if m.txt_id != 513] == [744]


def test_prebuff_stops_when_consume_takes_the_bound_demon():
    game = Game(world(monsters=(BOUND_DEMON,)))
    game.consume_takes = BOUND_DEMON.unit_id
    with pytest.raises(Abort, match='Consume'):
        prebuff(game.run())
    assert game.pressed() == ['q', '6']


def test_no_summon_at_any_spot_stops_before_consume():
    game = Game(world())
    game.keys.on_event = lambda event: None  # the game ignores every key
    with pytest.raises(Abort, match='Defiler'):
        prebuff(game.run())
    assert game.pressed() == ['q'] * 5  # once per summon spot


def test_a_spot_that_takes_no_summon_is_followed_by_another():
    game = Game(world())
    game.blocked = lambda x, y: x > 0.6  # nothing can stand on the right of the view
    prebuff(game.run())
    assert game.pressed() == ['q', 'q', '6', 'q', 'q', 'g', 'r']
    assert game.character.consume


def test_a_held_key_stops_the_macro_before_anything_is_sent():
    game = Game(world())
    game.keys.held = True
    with pytest.raises(Abort, match='key'):
        prebuff(game.run())
    assert game.keys.events == []


def test_a_key_the_osd_presses_does_not_stop_the_macro():
    # Host, 13:11 on 2026-10-07: the OSD's Show Items `z` was down at the first summon of a new game.
    game = Game(world())
    game.keys.held = ('z',)
    run = game.run()
    with pytest.raises(Abort, match='key'):
        run.actuator.tap('q')
    run.actuator.allow('z')
    prebuff(run)
    assert game.character.consume
    game.keys.held = ('z', 'w')
    with pytest.raises(Abort, match='key'):
        run.actuator.tap('q')


def test_a_moved_mouse_stops_the_macro():
    game = Game(world())
    run = game.run()
    run.actuator.move(0.5, 0.5)
    game.keys.at = (game.keys.at[0] + 60, game.keys.at[1])
    with pytest.raises(Abort, match='mouse'):
        run.actuator.tap('q')


def test_lost_focus_stops_the_macro():
    game = Game(world())
    game.focused = False
    with pytest.raises(Abort, match='focus'):
        prebuff(game.run())
    assert game.keys.events == []


def test_cancel_stops_at_the_next_read():
    game = Game(world())
    run = game.run()
    run.cancelled.set()
    with pytest.raises(Abort, match='cancelled'):
        prebuff(run)


def test_in_the_temple_the_macro_leaves_makes_the_next_game_and_prebuffs():
    game = Game(world(121))
    run_macro(game.run(), lambda w: dict(KEYS))
    keys = game.pressed()
    assert keys[0] == 'Escape'
    assert keys[1 : keys.index('Return')] == ['End', 'BackSpace', '3']
    assert keys[keys.index('Return') + 1 :] == ['q', '6', 'q', 'g', 'r']
    assert game.world.game_name == 'cyber33'
    assert game.said[-1] == 'Prebuff done'


def test_outside_the_temple_the_macro_only_prebuffs():
    game = Game(world(112))  # Arreat Plateau
    run_macro(game.run(), lambda w: dict(KEYS))
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']


def test_an_open_panel_is_closed_before_the_quit_menu():
    game = Game(world(121, open_panels=('inventory',)))
    run_macro(game.run(), lambda w: dict(KEYS))
    assert game.pressed()[:2] == ['Escape', 'Escape']
    assert game.world.game_name == 'cyber33'


def test_a_game_name_without_a_number_stops_in_the_lobby_without_typing():
    game = Game(world(121, game_name='pindle'))
    with pytest.raises(Abort, match='number'):
        run_macro(game.run(), lambda w: dict(KEYS))
    assert game.pressed() == ['Escape']


def test_another_character_is_refused():
    other = Game(world(player=player(name='Mule')))
    with pytest.raises(Abort, match='Mule'):
        run_macro(other.run(), lambda w: dict(KEYS))
    assert other.keys.events == []


def lobby(name='cyber32'):
    return replace(world(game_name=name), in_game=False, player=None)


def test_in_the_lobby_the_macro_makes_the_next_game_and_prebuffs():
    game = Game(lobby())
    run = game.run()
    run.keys = {}
    run_macro(run, lambda w: dict(KEYS))
    keys = game.pressed()
    assert keys[: keys.index('Return') + 1] == ['End', 'BackSpace', '3', 'Return']
    assert keys[keys.index('Return') + 1 :] == ['q', '6', 'q', 'g', 'r']
    assert game.world.game_name == 'cyber33'
    assert game.ignored == []


def test_a_screen_out_of_a_game_that_is_not_the_lobby_gets_clicks_but_no_typing_and_no_enter():
    game = Game(lobby())
    game.deaf_clicks = 99  # character select: no name field under the click
    with pytest.raises(Abort, match='name field'):
        run_macro(game.run(), lambda w: dict(KEYS))
    assert set(game.pressed()) == {'End', 'BackSpace'}


def test_from_the_lobby_another_character_gets_no_skill_key():
    game = Game(lobby())
    react = game.keys.on_event

    def as_mule(event):
        react(event)
        if event == ('key', 'Return'):
            game.world = replace(game.world, player=player(name='Mule'))

    game.keys.on_event = as_mule
    with pytest.raises(Abort, match='Mule'):
        run_macro(game.run(), lambda w: dict(KEYS))
    assert 'q' not in game.pressed()


def test_a_unit_right_of_the_character_is_drawn_right_of_it():
    me = player()
    right = screen_fraction(me, me.x + 5, me.y - 5, 2560 / 1418)
    below = screen_fraction(me, me.x + 5, me.y + 5, 2560 / 1418)
    assert right[0] > 0.5
    assert right[1] == pytest.approx(0.494 - 0.035)
    assert below[0] == pytest.approx(0.5)
    assert below[1] > right[1]


def test_a_lobby_that_is_not_ready_yet_gets_another_click_not_blind_typing():
    game = Game(world(121))
    game.deaf_clicks = 2
    run_macro(game.run(), lambda w: dict(KEYS))
    assert game.world.game_name == 'cyber33'
    assert game.world.in_game


def test_a_field_that_never_takes_keys_stops_the_macro_before_enter():
    game = Game(world(121))
    game.deaf_clicks = 99
    with pytest.raises(Abort, match='name field'):
        run_macro(game.run(), lambda w: dict(KEYS))
    assert 'Return' not in game.pressed()
    assert not any(len(key) == 1 for key in game.pressed())


@pytest.mark.parametrize(
    ('last', 'edits', 'following'),
    [
        ('cyber36', ['BackSpace', '7'], 'cyber37'),
        ('cyber39', ['BackSpace', 'BackSpace', '4', '0'], 'cyber40'),
        ('cyber99', ['BackSpace', 'BackSpace', '1'], 'cyber1'),  # after 99 from 1 again (the player, 2026-10-17)
    ],
)
def test_only_the_changed_end_of_the_name_is_retyped(last, edits, following):
    game = Game(world(121, game_name=last))
    run_macro(game.run(), lambda w: dict(KEYS))
    keys = game.pressed()
    assert keys[keys.index('End') + 1 : keys.index('Return')] == edits
    assert game.world.game_name == following


def test_nothing_is_pressed_on_a_loading_screen_of_ordinary_length():
    game = Game(world(121))
    run_macro(game.run(), lambda w: dict(KEYS))
    assert game.ignored == []
    assert game.character.consume


@pytest.mark.parametrize('seconds', [3.0, 6.0, 14.0])
def test_the_prebuff_starts_within_a_second_of_the_game_coming_up(seconds):
    game = Game(world(121))
    game.loading_seconds = seconds
    first = []
    react = game.keys.on_event

    def watch(event):
        if event == ('key', 'q') and not first:
            first.append(game.clock.now - game.loaded)
        react(event)

    game.keys.on_event = watch
    run_macro(game.run(), lambda w: dict(KEYS))
    assert game.ignored == []
    assert 0 < first[0] < 1.6


def test_without_the_loading_mark_a_slow_load_only_delays_the_first_summon():
    game = Game(world(121))
    game.view_marks = False
    game.loading_seconds = 14.0
    run_macro(game.run(), lambda w: dict(KEYS))
    assert {event[1] for event in game.ignored if event[0] == 'key'} == {'q'}
    assert game.character.consume
    assert [m.txt_id for m in game.world.monsters if m.txt_id != 513] == [744]


def test_a_game_that_never_takes_input_stops_the_macro():
    game = Game(world(121))
    game.loading_seconds = 500.0
    game.view_marks = False
    with pytest.raises(Abort, match='Defiler'):
        run_macro(game.run(), lambda w: dict(KEYS))
    assert game.clock.now < 60


def test_a_load_that_never_ends_with_the_player_in_another_window_says_so():
    # 12:33 and 12:47 on 2026-10-11: the player went to another window while the game loaded
    game = Game(world(121))
    game.loading_seconds = 500.0
    react = game.keys.on_event

    def leave(event):
        react(event)
        if event == ('key', 'Return'):
            game.focused = False

    game.keys.on_event = leave
    with pytest.raises(Abort, match='the game window is not in front'):
        run_macro(game.run(), lambda w: dict(KEYS))
    assert game.pressed()[-1] == 'Return'


def test_a_game_that_is_not_created_stops_the_macro_soon():
    game = Game(world(121))
    react = game.keys.on_event
    game.keys.on_event = lambda event: None if event == ('key', 'Return') else react(event)  # an error dialog
    with pytest.raises(Abort, match='cyber33 was not created'):
        run_macro(game.run(), lambda w: dict(KEYS))
    assert game.clock.now < 25


@pytest.mark.parametrize('area', [110, 111])  # Bloody Foothills (Shenk), Frigid Highlands (Eldritch)
def test_by_the_frigid_highlands_waypoint_the_macro_leaves_and_makes_the_next_game(area):
    game = Game(world(area))
    run_macro(game.run(), lambda w: dict(KEYS))
    keys = game.pressed()
    assert keys[0] == 'Escape'
    assert keys[keys.index('Return') + 1 :] == ['q', '6', 'q', 'g', 'r']
    assert game.world.game_name == 'cyber33'


@pytest.mark.parametrize('area', [110, 111])
def test_far_from_eldritch_and_shenk_the_macro_only_prebuffs(area):
    # A terrorized Frigid Highlands, 02:45 on 2026-10-11: the request 550 units from where Eldritch
    # died left the game. The character stands at (5000, 5000).
    for seen in ([], [(5400.0, 5300.0)]):
        game = Game(world(area))
        run = game.run()
        run.supers = lambda level, seen=seen: seen if level == area else [(5000.0, 5000.0)]
        run_macro(run, lambda w: dict(KEYS))
        assert 'Escape' not in game.pressed()
        assert game.world.game_name == 'cyber32'


@pytest.mark.parametrize('area', [110, 111])
def test_near_where_the_levels_super_unique_was_seen_the_macro_leaves(area):
    game = Game(world(area))
    run = game.run()
    run.supers = lambda level: [(5400.0, 5300.0), (5060.0, 5040.0)]
    run_macro(run, lambda w: dict(KEYS))
    assert game.pressed()[0] == 'Escape'
    assert game.world.game_name == 'cyber33'


def test_the_other_weapon_set_in_hand_is_swapped_away_before_the_first_cast_and_not_back():
    game = Game(world(112))
    game.sets = [OTHER_SET, PREBUFF_SET]
    run_macro(game.run(), lambda w: dict(KEYS))
    assert game.pressed() == ['c', 'q', '6', 'q', 'g', 'r']
    assert game.sets[0] == PREBUFF_SET


def test_the_prebuff_set_in_hand_is_left_alone():
    game = Game(world(112))
    run_macro(game.run(), lambda w: dict(KEYS))
    assert 'c' not in game.pressed()


def test_weapons_the_profile_does_not_know_stop_the_macro_after_the_swaps():
    game = Game(world(112))
    game.sets = [OTHER_SET, ('wnd', 'buc')]
    with pytest.raises(Abort, match='weapons'):
        run_macro(game.run(), lambda w: dict(KEYS))
    assert game.pressed() == ['c', 'c', 'c']  # SWAP_TRIES: the game drops a swap now and then


def test_a_swap_the_game_dropped_is_pressed_again():
    # Host, 17:26 on 2026-10-10: swaps pressed just after a cast never came and were waited on for 1.2 s.
    game = Game(world(112))
    game.sets = [OTHER_SET, PREBUFF_SET]
    react, dropped = game.keys.on_event, []

    def on_event(event):
        if event == ('key', 'c') and not dropped:
            dropped.append(event)  # the first press is lost
            return
        react(event)

    game.keys.on_event = on_event
    run_macro(game.run(), lambda w: dict(KEYS))
    assert game.pressed()[:3] == ['c', 'c', 'q']
    assert game.sets[0] == PREBUFF_SET


def test_in_a_new_game_the_swap_comes_before_the_first_summon():
    game = Game(world(121))
    game.sets = [OTHER_SET, PREBUFF_SET]
    run_macro(game.run(), lambda w: dict(KEYS))
    keys = game.pressed()
    # user, 2026-10-10: the main weapons are taken before Save and Exit, so the new game starts with them.
    assert keys.index('c') < keys.index('Escape')
    assert keys[keys.index('Return') + 1 :] == ['q', '6', 'q', 'g', 'r']
    assert game.sets[0] == PREBUFF_SET


def test_a_swap_that_does_not_come_does_not_keep_the_macro_from_leaving(caplog):
    from inventory_tracking.macros.routines import leave_game

    game = Game(world(121))
    game.sets = [OTHER_SET, ('xxx',)]  # neither set is the main one: the swap changes nothing known
    with caplog.at_level('INFO'):
        leave_game(game.run())
    assert game.pressed() == ['c', 'c', 'c', 'Escape']
    assert not game.world.in_game
    assert any('the main weapons are not in hand after a swap; going on' in r.message for r in caplog.records)


def arrived(game, previous, seconds):
    run = game.run()
    run.arrival = lambda: (previous, seconds)
    return run


@pytest.mark.parametrize('previous', [102, 83, 75])  # Durance of Hate 3, Travincal, Kurast Docks
def test_in_the_fortress_just_after_act_3_the_macro_leaves_and_makes_the_next_game(previous):
    game = Game(world(103))
    run_macro(arrived(game, previous, 40.0), lambda w: dict(KEYS))
    keys = game.pressed()
    assert keys[0] == 'Escape'
    assert keys[keys.index('Return') + 1 :] == ['q', '6', 'q', 'g', 'r']
    assert game.world.game_name == 'cyber33'


@pytest.mark.parametrize(
    ('previous', 'seconds'),
    [
        (None, 5.0),  # the game started here
        (107, 5.0),  # back from the River of Flame
        (102, 600.0),  # came from Mephisto long ago
    ],
)
def test_in_the_fortress_otherwise_the_macro_only_prebuffs(previous, seconds):
    game = Game(world(103))
    run_macro(arrived(game, previous, seconds), lambda w: dict(KEYS))
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']


def test_without_a_journey_the_fortress_is_an_ordinary_place():
    game = Game(world(103))
    run_macro(game.run(), lambda w: dict(KEYS))
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']


def test_on_andariels_level_without_her_the_macro_leaves_and_makes_the_next_game():
    game = Game(world(37, monsters=(Monster(71, 58, 1, 5020.0, 5020.0, 0xFFFFFFFF),)))  # a minion is left
    run_macro(game.run(), lambda w: dict(KEYS))
    keys = game.pressed()
    assert keys[0] == 'Escape'
    assert keys[keys.index('Return') + 1 :] == ['q', '6', 'q', 'g', 'r']
    assert game.world.game_name == 'cyber33'


def test_on_a_level_whose_route_is_at_its_end_the_macro_leaves_and_makes_the_next_game():
    # Chaos Sanctuary, 23:18:38 on 2026-10-12: Diablo dead, and the macro request only cast the buffs.
    game = Game(world(108, monsters=(Monster(71, 310, 1, 5300.0, 5300.0, 0xFFFFFFFF),)))  # a Doom Knight far off
    run = game.run()
    run.ending = lambda area: area == 108
    run_macro(run, lambda w: dict(KEYS))
    keys = game.pressed()
    assert keys[0] == 'Escape'
    assert game.world.game_name == 'cyber33'


def test_on_a_level_whose_route_is_not_at_its_end_the_macro_only_prebuffs():
    game = Game(world(108))
    run = game.run()
    run.ending = lambda area: False
    run_macro(run, lambda w: dict(KEYS))
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']


def test_on_the_countess_level_without_her_the_macro_leaves_and_makes_the_next_game():
    stalker = Monster(71, 45, 1, 5020.0, 5020.0, 0xFFFFFFFF)  # a Dark Stalker of her class, not her
    game = Game(world(25, monsters=(stalker,)))
    run_macro(game.run(), lambda w: dict(KEYS))
    keys = game.pressed()
    assert keys[0] == 'Escape'
    assert game.world.game_name == 'cyber33'


def test_with_the_countess_alive_the_macro_only_prebuffs():
    countess = Monster(70, 45, 1, 5040.0, 5040.0, 0xFFFFFFFF, flags=0x0A)  # the flags her sightings carry
    game = Game(world(25, monsters=(countess,)))
    run_macro(game.run(), lambda w: dict(KEYS))
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']


@pytest.mark.parametrize('area', [37, 36])  # her level with her alive; another level without her
def test_with_andariel_alive_or_on_another_level_the_macro_only_prebuffs(area):
    andariel = (Monster(70, 156, 1, 5040.0, 5040.0, 0xFFFFFFFF),) if area == 37 else ()
    game = Game(world(area, monsters=andariel))
    run_macro(game.run(), lambda w: dict(KEYS))
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']


def test_beside_the_dead_nihlathak_the_macro_leaves_and_makes_the_next_game():
    # 11:48 on 2026-10-11: the request 11 units from where he died 13 s before only prebuffed.
    game = Game(world(124))
    run = game.run()
    run.supers = lambda level: [(5010.0, 5005.0)]
    run_macro(run, lambda w: dict(KEYS))
    assert game.pressed()[0] == 'Escape'
    assert game.world.game_name == 'cyber33'


@pytest.mark.parametrize(
    ('monsters', 'seen'),
    [
        ((Monster(70, 526, 1, 5010.0, 5005.0, 0xFFFFFFFF),), [(5010.0, 5005.0)]),  # alive beside the character
        ((), []),  # not found yet
        ((), [(5400.0, 5300.0)]),  # killed, and the character far from there
        ((), None),  # no tracker to say where he was
    ],
)
def test_in_the_halls_of_vaught_away_from_a_dead_nihlathak_the_macro_only_prebuffs(monsters, seen):
    game = Game(world(124, monsters=monsters))
    run = game.run()
    run.supers = None if seen is None else lambda level: seen
    run_macro(run, lambda w: dict(KEYS))
    assert 'Escape' not in game.pressed()
    assert game.world.game_name == 'cyber32'


def test_beside_the_dead_summoner_the_macro_leaves_and_makes_the_next_game():
    # user, 2026-10-11: "win-x at summoner's location should go save/exit -> new game -> prebuff"
    game = Game(world(74))
    run = game.run()
    run.supers = lambda level: [(5010.0, 5005.0)]
    run_macro(run, lambda w: dict(KEYS))
    assert game.pressed()[0] == 'Escape'
    assert game.world.game_name == 'cyber33'


@pytest.mark.parametrize(
    ('monsters', 'seen'),
    [
        ((Monster(70, 250, 1, 5010.0, 5005.0, 0xFFFFFFFF),), [(5010.0, 5005.0)]),  # alive beside the character
        ((), []),  # not found yet: the wrong arm, or on the way
        ((), [(5400.0, 5300.0)]),  # killed, and the character far from there
        ((), None),  # no tracker to say where he was
    ],
)
def test_in_the_arcane_sanctuary_away_from_a_dead_summoner_the_macro_only_prebuffs(monsters, seen):
    game = Game(world(74, monsters=monsters))
    run = game.run()
    run.supers = None if seen is None else lambda level: seen
    run_macro(run, lambda w: dict(KEYS))
    assert 'Escape' not in game.pressed()
    assert game.world.game_name == 'cyber32'


def quick_run(rights, quick):
    """A run whose character shows `rights` on the right button, one a look, 0.1 s apart."""
    import random
    from types import SimpleNamespace

    from inventory_tracking.macros.timing import Pace

    state = SimpleNamespace(now=0.0, looks=0)

    def look():
        right = rights[min(state.looks, len(rights) - 1)]
        state.looks += 1
        return world(player=player(right_skill=right, mode=1))

    def sleep(_seconds):
        state.now += 0.1

    run = Game(world()).run()
    run.read, run.clock, run.pace = look, lambda: state.now, Pace(random.Random(1), sleep)
    run.quick = quick
    return run, state


def test_a_skill_key_waits_for_the_one_before_to_give_the_right_button_back():
    # Tower Cellar 1, 20:00:12 on 2026-10-11: Sigil: Lethargy tapped under the held strike came onto
    # the button 0.5 s later, as Teleport's key went down, and stayed there: attack mode stopped.
    from inventory_tracking.builds.warlock.skills import ECHOING_STRIKE, SIGIL_LETHARGY
    from inventory_tracking.macros.routines import QUICK_SECONDS, quick_cast_over
    from inventory_tracking.macros.skills import TELEPORT

    strike, sigil = ECHOING_STRIKE, SIGIL_LETHARGY
    run, state = quick_run([strike, strike, strike, strike, strike, sigil, sigil, strike], (sigil, strike, 0.0, True))
    quick_cast_over(run, TELEPORT)
    assert state.looks == 8  # through the wait under the strike, the cast, and the strike back
    assert run.quick is None

    run, state = quick_run([strike], (sigil, strike, 0.0, True))  # it never shows: not for ever
    quick_cast_over(run, TELEPORT)
    assert QUICK_SECONDS <= state.now < QUICK_SECONDS + 0.2

    run, state = quick_run([strike], (sigil, strike, 0.0, False))  # nothing was held: a short wait only
    quick_cast_over(run, TELEPORT)
    assert state.now < 0.5

    run, state = quick_run([sigil], (TELEPORT, strike, 0.0, True))  # the same key again: no wait
    quick_cast_over(run, TELEPORT)
    assert state.looks == 0


def test_a_skill_seen_on_the_button_by_any_look_since_its_key_is_not_waited_for(caplog):
    # The Chaos Sanctuary, 02:21:27 and 02:23:25 on 2026-10-14: Death Mark showed on the right button 0.08 to 0.16 s
    # after its key (the take's frames, read by the fight's own looks), then the strike came back; the Sigil's key
    # 0.5 s later waited out the whole second for it with the strike let go: a volley gap of 1.63 s against 0.73.
    from inventory_tracking.builds.warlock.skills import DEATH_MARK, ECHOING_STRIKE, SIGIL_LETHARGY
    from inventory_tracking.macros.routines import quick_cast_over

    game = Game(world(player=player(right_skill=ECHOING_STRIKE, mode=10)))
    run = game.run()
    run.quick = (DEATH_MARK, ECHOING_STRIKE, run.clock(), True)  # tapped under the held strike
    game.world = replace(game.world, player=replace(game.character, right_skill=DEATH_MARK))
    run.world()  # a look of the fight's while the mark is cast
    game.world = replace(game.world, player=replace(game.character, right_skill=ECHOING_STRIKE))
    game.clock.now += 0.5
    began = run.clock()
    with caplog.at_level('INFO', logger='inventory_tracking'):
        quick_cast_over(run, SIGIL_LETHARGY)
    assert run.clock() - began < 0.05
    assert 'still on the right button' not in caplog.text
    assert run.quick is None


def test_a_key_long_after_the_one_before_says_nothing_of_a_wait_it_did_not_make(caplog):
    # Every Death Mark of 2026-10-14 followed a "Blade Warp still on the right button 1.0s after its key" though the
    # warp was seconds old and nothing was waited for (the loop's `else` ran with no look at all).
    from inventory_tracking.builds.warlock.skills import DEATH_MARK, ECHOING_STRIKE
    from inventory_tracking.macros.routines import quick_cast_over
    from inventory_tracking.macros.skills import TELEPORT

    game = Game(world(player=player(right_skill=ECHOING_STRIKE)))
    run = game.run()
    run.quick = (TELEPORT, ECHOING_STRIKE, run.clock(), False)
    game.clock.now += 7.0
    with caplog.at_level('INFO', logger='inventory_tracking'):
        quick_cast_over(run, DEATH_MARK)
    assert 'still on the right button' not in caplog.text
    assert run.quick is None


def test_an_arrivals_probe_swaps_back_without_a_settle(monkeypatch):
    # 14:35 on 2026-10-17: the swap back after the probe's swap waited the 0.2 s settle meant for after a cast, though
    # the character just arrived stands
    from inventory_tracking.macros import routines

    game = Game(world(112))
    game.sets = [PREBUFF_SET, OTHER_SET]
    settled = []
    monkeypatch.setattr(routines, 'settle', lambda *a, **k: settled.append(True))
    run = game.run()
    run.keys = dict(KEYS)
    assert routines.took_input(run, 'Lower Kurast', run.clock())
    assert game.pressed() == ['c', 'c']
    assert game.sets[0] == PREBUFF_SET
    assert not settled


def test_a_panel_that_opens_after_the_first_look_does_not_keep_the_game_from_being_left(monkeypatch):
    # 15:35:43-47 on 2026-10-17: the walk back from Halbu ended on the waypoint, its panel opened after leave_game's
    # look; Escape closed it, the quit menu never came, and the loop stopped
    from inventory_tracking.macros import routines

    game = Game(world(103))

    def opens(run):
        game.world = replace(game.world, open_panels=('waypoint',))

    monkeypatch.setattr(routines, 'take_battle_weapons', opens)
    routines.leave_game(game.run())
    assert not game.world.in_game


def test_a_level_run_turns_the_item_labels_on_first():
    # Game 40 at 18:22 on 2026-10-18: `make osd` gave up on Show Items during the load, the run went with it off
    game = Game(world(show_items=False))

    def toggle(event) -> None:
        if event[:2] == ('key', 'z'):
            game.world = replace(game.world, show_items=not game.world.show_items)

    game.keys.on_event = toggle
    show_items_on(game.run(), 'z')
    assert game.world.show_items is True
    assert game.pressed().count('z') == 1
    show_items_on(game.run(), 'z')  # on already: nothing pressed, never toggled back off
    assert game.pressed().count('z') == 1


def test_item_labels_that_stay_off_stop_the_level_run():
    game = Game(world(show_items=False))
    game.keys.on_event = lambda event: None
    with pytest.raises(Abort, match='Show Items stays off'):
        show_items_on(game.run(), 'z')
    assert game.pressed().count('z') == SHOW_ITEMS_TRIES
    with pytest.raises(Abort, match='no Show Items key'):
        show_items_on(game.run(), None)
    show_items_on(Game(world(show_items=None)).run(), 'z')  # unread: not pressed blind
