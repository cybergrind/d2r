"""The strike put back on the right mouse button in keyboard mode, in the game's skill selection (macros/skillpanel.py;
rca/2026-10-14/run-1904-findings.md §3.7, the player's ruling of 2026-10-14): after a controller stint the right
button held Summon Defiler (the pad's B), and attack mode by the keys stopped three times in 19.4 s."""

import logging
import math
from dataclasses import replace

import pytest

from inventory_tracking.builds.characters import ICONS
from inventory_tracking.builds.warlock.skills import BLADE_WARP, ECHOING_STRIKE, SUMMON_DEFILER
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.skillpanel import PANEL, RIGHT_BUTTON, select_right, window_point
from tests.inventory_tracking.macros.fakes import SLOTS, WINDOW, Game
from tests.inventory_tracking.macros.test_hunt import foe, game, hunter, keys


ICON = ICONS['CybergrindAA'][ECHOING_STRIKE]
NEAR = 0.01  # window fractions: a click this near a place is on it


class Selection:
    """The skill selection over a fakes' game: a click on the right skill's button opens it (or closes it), a click
    on an icon while it is open puts that icon's skill on the right button and closes it; any other click while
    it is open closes it. Clicks elsewhere are the game's (`Game.react`). `icons`: window fraction -> skill."""

    def __init__(self, play: Game, icons: dict[tuple[float, float], int]) -> None:
        self.play = play
        self.icons = icons
        self.button = window_point(RIGHT_BUTTON, WINDOW)
        play.keys.on_event = self.on

    def on(self, event) -> None:
        play, w = self.play, self.play.world
        if event[0] != 'click':
            play.react(event)
            return
        at = event[1]
        opened = PANEL in w.open_panels
        if math.dist(at, self.button) <= NEAR:
            play.world = replace(w, open_panels=() if opened else (PANEL,))
            return
        if not opened:
            play.react(event)
            return
        skill = next((s for place, s in self.icons.items() if math.dist(at, place) <= NEAR), None)
        player = w.player if skill is None else replace(w.player, right_skill=skill)
        play.world = replace(w, open_panels=(), player=player)


def after_a_stint(*monsters) -> Game:
    """The CS at 22:09:20 on 2026-10-14: back in keyboard mode with Blade Warp on the left button and Summon Defiler
    on the right, Echoing Strike on no key."""
    play = game(*monsters, slots=SLOTS)
    p = play.world.player
    play.world = replace(play.world, player=replace(p, left_skill=BLADE_WARP, right_skill=SUMMON_DEFILER))
    return play


def test_the_places_are_the_players_own_selection_in_a_window_of_its_size() -> None:
    # The take's pointer: the panel opened at (0.536, 0.978), Echoing Strike was clicked at (0.669, 0.696)
    assert window_point(RIGHT_BUTTON, WINDOW) == pytest.approx((0.536, 0.978), abs=0.001)
    assert window_point(ICON, WINDOW) == pytest.approx((0.669, 0.696), abs=0.001)


def test_the_strike_is_selected_on_the_right_button_by_its_icon(caplog) -> None:
    play = after_a_stint()
    Selection(play, {window_point(ICON, WINDOW): ECHOING_STRIKE})
    run = play.run()
    with caplog.at_level(logging.INFO):
        select_right(run, ECHOING_STRIKE, ICON)
    assert play.world.player.right_skill == ECHOING_STRIKE
    assert PANEL not in play.world.open_panels
    assert 'Macro: skill panel: Echoing Strike put on the right button (it held Summon Defiler)' in caplog.text
    clicks = [event[1] for event in play.keys.events if event[0] == 'click']
    assert len(clicks) == 2
    assert not play.walks  # no click went to the ground


def test_an_icon_that_is_not_there_leaves_the_panel_closed_and_says_so() -> None:
    play = after_a_stint()
    selection = Selection(play, {})
    run = play.run()
    with pytest.raises(Abort, match=r'did not put Echoing Strike on the right button \(it holds Summon Defiler'):
        select_right(run, ECHOING_STRIKE, ICON)
    assert PANEL not in play.world.open_panels
    selection.icons = {window_point(ICON, WINDOW): 377}  # another skill's icon there: closed with it on the button
    with pytest.raises(Abort, match='did not put Echoing Strike'):
        select_right(run, ECHOING_STRIKE, ICON)
    assert not play.walks


def test_nothing_is_clicked_over_another_panel_or_when_the_selection_does_not_open() -> None:
    play = after_a_stint()
    run = play.run()
    play.world = replace(play.world, open_panels=('inventory',))
    with pytest.raises(Abort, match='inventory open'):
        select_right(run, ECHOING_STRIKE, ICON)
    assert not play.keys.events
    play.world = replace(play.world, open_panels=())
    play.keys.on_event = lambda event: None  # the click on the button opens nothing
    with pytest.raises(Abort, match='did not open'):
        select_right(run, ECHOING_STRIKE, ICON)
    assert len([event for event in play.keys.events if event[0] == 'click']) == 1  # the icon is not clicked


def test_attack_mode_by_the_keys_puts_the_strike_back_and_fights(caplog) -> None:
    """The fight stopped 15 times on "Echoing Strike is on no skill key and on neither mouse button (left Blade Warp,
    right Summon Defiler)" until the player selected it by hand (22:09:51.68). Now the mode selects it itself once
    the wrong skill has stayed INPUT_SECONDS, and strikes."""
    play = after_a_stint(foe(10, 5008.0, 5000.0))
    Selection(play, {window_point(ICON, WINDOW): ECHOING_STRIKE})
    run = play.run()
    play.arrivals.append((6.0, run.cancelled.set))
    with caplog.at_level(logging.INFO), pytest.raises(Abort, match='cancelled'):
        hunter(play).attack_mode(run, keys)
    assert 'Macro: skill panel: Echoing Strike is on no skill key and on neither mouse button (left Blade Warp, ' in (
        caplog.text
    )
    assert 'Macro: skill panel: Echoing Strike put on the right button (it held Summon Defiler)' in caplog.text
    assert 'the fight stopped' not in caplog.text
    assert 10 in play.world.dead


def test_a_character_whose_icon_is_not_known_is_not_clicked_for(caplog) -> None:
    play = after_a_stint(foe(10, 5008.0, 5000.0))
    hunt = hunter(play)
    hunt.build = replace(hunt.build, skill_icons={})
    run = play.run()
    with caplog.at_level(logging.INFO), pytest.raises(Abort, match='fights stopped in a row'):
        hunt.attack_mode(run, keys)
    assert not [event for event in play.keys.events if event[0] == 'click']
