from dataclasses import replace

import pytest

from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.routines import prebuff, run_macro, screen_fraction
from inventory_tracking.macros.world import Monster
from tests.inventory_tracking.macros.fakes import KEYS, OTHER_SET, PREBUFF_SET, Game, player, world


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
    assert game.pressed() == ['q'] * 5  # once per summon spot


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


def test_a_key_the_osd_presses_does_not_stop_the_macro():
    # Host, 13:11 on 2026-10-07: the OSD's Show Items `z` was down at the first summon of a new game.
    game = Game(world())
    game.keys.held = ('z',)
    run = game.run()
    with pytest.raises(Abort, match='key'):
        run.actuator.tap('q')
    run.actuator.allow('z')
    prebuff(run)
    assert game.world.player.consume
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


def test_weapons_the_profile_does_not_know_stop_the_macro_after_one_swap():
    game = Game(world(112))
    game.sets = [OTHER_SET, ('wnd', 'buc')]
    with pytest.raises(Abort, match='weapons'):
        run_macro(game.run(), lambda w: dict(KEYS))
    assert game.pressed() == ['c']


def test_in_a_new_game_the_swap_comes_before_the_first_summon():
    game = Game(world(121))
    game.sets = [OTHER_SET, PREBUFF_SET]
    run_macro(game.run(), lambda w: dict(KEYS))
    keys = game.pressed()
    assert keys[keys.index('Return') + 1 :] == ['c', 'q', '6', 'q', 'g', 'r']


def follow(game, times=99):
    """The bound demon walks onto every new Defiler, `times` times."""
    react, left = game.keys.on_event, [times]

    def on_event(event):
        react(event)
        if event == ('key', 'q') and left[0]:
            left[0] -= 1
            defiler = next(m for m in game.world.monsters if m.txt_id == 744)
            moved = tuple(
                replace(m, x=defiler.x + 1, y=defiler.y + 1) if m.txt_id == 700 else m for m in game.world.monsters
            )
            game.world = replace(game.world, monsters=moved)

    game.keys.on_event = on_event


def test_consume_is_not_pressed_while_the_bound_demon_stands_by_the_defiler():
    game = Game(world(monsters=(BOUND_DEMON,)))
    follow(game)
    with pytest.raises(Abort, match='too close'):
        prebuff(game.run())
    assert '6' not in game.pressed()
    assert 700 in [m.txt_id for m in game.world.monsters]


def test_a_defiler_the_demon_walked_up_to_is_replaced_by_one_in_the_open():
    game = Game(world(monsters=(BOUND_DEMON,)))
    follow(game, times=1)
    prebuff(game.run())
    assert game.pressed() == ['q', 'q', '6', 'q', 'g', 'r']
    assert game.world.player.consume
    assert sorted(m.txt_id for m in game.world.monsters) == [700, 744]


def test_a_crowded_defiler_is_replaced_at_another_spot_each_time():
    game = Game(world(monsters=(BOUND_DEMON,)))
    follow(game, times=2)
    react, summons = game.keys.on_event, []

    def on_event(event):
        if event == ('key', 'q'):
            summons.append(game.keys.fraction())
        react(event)

    game.keys.on_event = on_event
    prebuff(game.run())
    assert len({(round(x, 1), round(y, 1)) for x, y in summons[:3]}) == 3
    assert game.world.player.consume


def test_a_tall_demon_drawn_below_the_defiler_is_not_consumed_in_its_place():
    # Host, 01:46 on 2026-10-07: 8 world units apart, the demon below the Defiler on the screen.
    defiler = Monster(60, 744, 1, 4997.0, 4995.0, 0xFFFFFFFF)
    demon = replace(BOUND_DEMON, x=5001.0, y=5002.0)
    game = Game(world(monsters=(demon, defiler)))
    prebuff(game.run())
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']  # another Defiler, in the open
    assert sorted(m.txt_id for m in game.world.monsters) == [700, 744]


def test_a_defiler_is_not_summoned_next_to_the_demon():
    demon_on_the_right = replace(BOUND_DEMON, x=5004.0, y=4993.0)  # where the first summon spot is
    game = Game(world(monsters=(demon_on_the_right,)))
    prebuff(game.run())
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']
    assert sorted(m.txt_id for m in game.world.monsters) == [700, 744]


def test_townsfolk_by_the_defiler_do_not_stop_consume():
    # Host, 19:43 on 2026-10-07 (Rogue Encampment): Kashya (class 150) 8 and 12 units from the
    # Defiler was "too close" three summons in a row, and Consume was never pressed.
    game = Game(world())
    react = game.keys.on_event

    def on_event(event):  # she stands that far from every Defiler, wherever it lands
        react(event)
        if event == ('key', 'q'):
            defiler = next(m for m in game.world.monsters if m.txt_id == 744)
            kashya = Monster(8, 150, 1, defiler.x + 8, defiler.y + 12, 0xFFFFFFFF)
            others = tuple(m for m in game.world.monsters if m.txt_id != 150)
            game.world = replace(game.world, monsters=(*others, kashya))

    game.keys.on_event = on_event
    prebuff(game.run())
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']


def test_consume_is_aimed_where_the_defiler_stands_after_it_walked():
    # User, 2026-10-07: the summoned Defiler moves, and Consume pressed where it was misses.
    game = Game(world())
    react, walked = game.keys.on_event, []

    def on_event(event):
        react(event)
        if event == ('key', 'q') and not walked:  # it walks off as soon as it has landed
            walked.append(True)
            moved = tuple(replace(m, x=m.x - 9, y=m.y + 2) if m.txt_id == 744 else m for m in game.world.monsters)
            game.world = replace(game.world, monsters=moved)

    game.keys.on_event = on_event
    steps, move = [], game.keys.move_pointer

    def move_pointer(x, y):  # and takes two more steps while the pointer is on its way to it
        steps.append((x, y))
        if len(walked) < 3 and len(steps) % 3 == 0 and '6' not in game.pressed() and game.pressed() == ['q']:
            walked.append(True)
            moved = tuple(replace(m, x=m.x + 3) if m.txt_id == 744 else m for m in game.world.monsters)
            game.world = replace(game.world, monsters=moved)
        return move(x, y)

    game.keys.move_pointer = move_pointer
    prebuff(game.run())
    assert len(walked) == 3
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']
    assert game.world.player.consume


def test_consume_is_not_pressed_at_a_defiler_that_never_stands_still():
    # The pointer would be where the Defiler was, and the bound demon may stand there (user,
    # 2026-10-07: the demon must never be consumed by accident).
    game = Game(world(monsters=(BOUND_DEMON,)))
    run = game.run()
    move, steps = run.actuator.move, [3.0, -3.0]

    def restless(x, y, **scatter):  # three units to and fro, once per pointer move
        move(x, y, **scatter)
        steps.reverse()
        walked = tuple(replace(m, x=m.x + steps[0]) if m.txt_id == 744 else m for m in game.world.monsters)
        game.world = replace(game.world, monsters=walked)

    run.actuator.move = restless
    with pytest.raises(Abort, match='keeps walking'):
        prebuff(run)
    assert '6' not in game.pressed()
    assert 700 in [m.txt_id for m in game.world.monsters]


def deaf_to_consume(game, times):
    """The game does nothing on the first `times` Consume keys."""
    react, left = game.keys.on_event, [times]

    def on_event(event):
        if event == ('key', '6') and left[0]:
            left[0] -= 1
            return
        react(event)

    game.keys.on_event = on_event


def test_a_consume_that_changed_nothing_is_pressed_again():
    # Host, 20:04 on 2026-10-07: the key went down on a still Defiler, which stood on with no buff.
    game = Game(world(monsters=(BOUND_DEMON,)))
    deaf_to_consume(game, 1)
    prebuff(game.run())
    assert game.pressed() == ['q', '6', '6', 'q', 'g', 'r']
    assert game.world.player.consume
    assert sorted(m.txt_id for m in game.world.monsters) == [700, 744]


def test_consume_gives_up_after_three_presses_that_changed_nothing():
    game = Game(world())
    deaf_to_consume(game, 99)
    with pytest.raises(Abort, match='Consume: not seen'):
        prebuff(game.run())
    assert game.pressed() == ['q', '6', '6', '6']


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


@pytest.mark.parametrize('area', [37, 36])  # her level with her alive; another level without her
def test_with_andariel_alive_or_on_another_level_the_macro_only_prebuffs(area):
    andariel = (Monster(70, 156, 1, 5040.0, 5040.0, 0xFFFFFFFF),) if area == 37 else ()
    game = Game(world(area, monsters=andariel))
    run_macro(game.run(), lambda w: dict(KEYS))
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']
