from dataclasses import replace

import pytest

from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.routines import prebuff, run_macro, screen_fraction
from inventory_tracking.macros.world import Monster
from tests.inventory_tracking.macros.fakes import KEYS, Game, player, world


BOUND_DEMON = Monster(50, 700, 1, 4995.0, 5003.0, 0xFFFFFFFF)  # summons carry no owner (host, 2026-10-06)


def test_prebuff_consumes_its_own_defiler_and_keeps_the_bound_demon():
    game = Game(world(monsters=(BOUND_DEMON,)))
    prebuff(game.run())
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']
    assert game.world.player.consume
    assert [m.txt_id for m in game.world.monsters] == [700, 744]


DEFILER = Monster(60, 744, 1, 5006.0, 4996.0, 0xFFFFFFFF)


@pytest.mark.parametrize(
    ('consume', 'monsters', 'keys'),
    [
        (True, (DEFILER,), ['g', 'r']),  # both there: only the casts
        (True, (), ['q', 'g', 'r']),  # buff without a Defiler: one summon
        (False, (DEFILER,), ['6', 'q', 'g', 'r']),  # a Defiler without the buff: consume it, summon one
        (False, (), ['q', '6', 'q', 'g', 'r']),
    ],
)
def test_prebuff_presses_only_what_is_missing_and_ends_buffed_with_one_defiler(consume, monsters, keys):
    game = Game(world(player=player(consume=consume), monsters=monsters))
    prebuff(game.run())
    assert game.pressed() == keys
    assert game.world.player.consume
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
    assert game.pressed() == ['q', 'q', 'q']


def test_a_spot_that_takes_no_summon_is_followed_by_another():
    game = Game(world())
    game.blocked = lambda x, y: x > 0.6  # nothing can stand on the right of the view
    prebuff(game.run())
    assert game.pressed() == ['q', 'q', '6', 'q', 'q', 'g', 'r']
    assert game.world.player.consume


def test_a_held_key_stops_the_macro_before_anything_is_sent():
    game = Game(world())
    game.keys.held = True
    with pytest.raises(Abort, match='key'):
        prebuff(game.run())
    assert game.keys.events == []


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
        ('cyber99', ['BackSpace', 'BackSpace', '1', '0', '0'], 'cyber100'),
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
    assert game.world.player.consume


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
    assert game.world.player.consume
    assert [m.txt_id for m in game.world.monsters if m.txt_id != 513] == [744]


def test_a_game_that_never_takes_input_stops_the_macro():
    game = Game(world(121))
    game.loading_seconds = 500.0
    game.view_marks = False
    with pytest.raises(Abort, match='Defiler'):
        run_macro(game.run(), lambda w: dict(KEYS))
    assert game.clock.now < 60


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
