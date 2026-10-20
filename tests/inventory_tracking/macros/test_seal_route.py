"""The Chaos Sanctuary's seals and their bosses, game 2 of 20261020T211911Z-0a4e743b (00:45:48-00:45:59 on 2026-10-21):
De Seis seal took its click late and was found open at the next look ("At De Seis seal"); no wait for what it brings,
De Seis came by the seal behind the Teleports, and with nothing known the level run ended: De Seis and his pack, the
Infector seals and Diablo were left."""

from dataclasses import replace

import pytest

from inventory_tracking.game.records import Thing
from inventory_tracking.levels.model import SEALS, Target
from inventory_tracking.macros import goals, route
from inventory_tracking.macros.goals import Goal, fight_goal, summoner
from inventory_tracking.macros.hunting import choice, moves
from inventory_tracking.macros.hunting.base import Bearings
from inventory_tracking.macros.teleport import SEAL_BRINGS
from inventory_tracking.macros.travel import PRESSED
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.model import FIGHT, LOOT, USE, fight, use
from inventory_tracking.routes.progress import Progress
from tests.inventory_tracking.macros.test_hunt import ROOMS, foe, game, hunter, me


SANCTUARY = 108
DE_SEIS_SEAL = 394  # DiabloSeal3 (levels/model.py SEALS)
SEAL_PLACE = (7815.0, 5155.0)  # world units, as logged at 00:45:48
SEAL_ORDER = ('Vizier seal 1', 'Vizier seal 2', 'De Seis seal', 'Infector seal 1', 'Infector seal 2')
BOSSES = ('Grand Vizier of Chaos', 'Lord De Seis', 'Infector of Souls', 'Diablo')


def sanctuary_script():
    script = next(script for r in ROUTES for script in r.scripts if script.area == SANCTUARY)
    return script


def test_each_markless_seal_fight_is_called_by_its_arms_last_seal():
    stages = sanctuary_script().stages
    called = {stage.boss: summoner(stages, stage) for stage in stages if stage.kind == FIGHT}
    assert called['Grand Vizier of Chaos'] == use('Vizier seal 2')
    assert called['Lord De Seis'] == use('De Seis seal')
    assert called['Infector of Souls'] == use('Infector seal 2')
    assert called['Diablo'] is None  # a fight with a mark of its own
    assert summoner(stages, use('De Seis seal')) is None


def de_seis_goal(here, *, foes=(), elsewhere=None, appears=(SEAL_PLACE, 'De Seis seal')):
    return fight_goal(
        fight('Lord De Seis'), 'Diablo', None, here, foes, (), (), frozenset(), elsewhere, 8.0, PRESSED, appears
    )


def test_a_seal_boss_nothing_is_known_of_is_looked_for_by_his_seal_not_given_up(monkeypatch):
    monkeypatch.setattr(goals, 'SEAL_BOSS_BY_SEAL', True)
    # 00:45:59: "the level run ends: nothing is left to go to on this level: no route stage, no boss known"
    here = (7941.5, 5318.5)
    found = de_seis_goal(here)
    assert found is not None
    assert (found.do, found.place, found.known, found.stage) == (FIGHT, SEAL_PLACE, False, fight('Lord De Seis'))
    assert found.route == 'Diablo'


def test_a_seal_boss_is_fought_when_seen_and_a_known_hostile_is_looked_at_before_the_seal(monkeypatch):
    monkeypatch.setattr(goals, 'SEAL_BOSS_BY_SEAL', True)
    here = (7811.4, 5156.6)
    de_seis = foe(7, 7777.5, 5174.5, flags=0x0A, txt_id=312)  # unit 1734551400 of the take: super unique
    seen = de_seis_goal(here, foes=[de_seis])
    assert seen is not None
    assert (seen.unit, seen.place) == (7, (7777.5, 5174.5))
    looked = de_seis_goal(here, elsewhere=lambda: ((7864.0, 5298.0), 'the remembered monster'))
    assert looked is not None
    assert looked.place == (7864.0, 5298.0)


def test_with_the_seal_switch_off_or_no_seal_nothing_known_is_no_goal(monkeypatch):
    here = (7941.5, 5318.5)
    assert de_seis_goal(here, appears=None) is None
    monkeypatch.setattr(goals, 'SEAL_BOSS_BY_SEAL', False)
    assert de_seis_goal(here) is None


def test_the_hunts_goal_names_the_seal_from_the_cards_marks():
    progress = Progress(ROUTES, route.PERFORMED, dead=lambda: frozenset(('Grand Vizier of Chaos',)))
    progress.note('cyberr99', SANCTUARY)
    for label in ('Vizier seal 1', 'Vizier seal 2', 'De Seis seal'):
        progress.used(SANCTUARY, label, (0.0, 0.0), [(0.0, 0.0)])
    places = {'De Seis seal': ((SEAL_PLACE[0] / TILE_UNITS, SEAL_PLACE[1] / TILE_UNITS),)}
    bearings = Bearings(progress, marks=lambda label: places.get(label, ()))
    step = progress.step(SANCTUARY)
    assert step is not None
    assert step.stage == fight('Lord De Seis')
    assert choice.seal_of(bearings, SANCTUARY, (7941.5, 5318.5), step.stage) == (SEAL_PLACE, 'De Seis seal')
    assert choice.seal_of(bearings, SANCTUARY, (7941.5, 5318.5), use('Infector seal 1')) is None
    assert choice.seal_of(Bearings(progress), SANCTUARY, (7941.5, 5318.5), step.stage) is None


# --- the seal found open at its operate ---


DE_SEIS_USE = use('De Seis seal')


def seal_at_hand(mode: int, stage=DE_SEIS_USE):
    play = game(area=SANCTUARY)
    hunt = hunter(play)
    run = play.run()
    player = me(play.world)
    place = (player.x + 3.0, player.y)
    seal = Thing(1577890155, DE_SEIS_SEAL, mode, *place)
    run.things = lambda: (seal,)
    mark = Target(SANCTUARY, ROOMS, (place[0] / TILE_UNITS, place[1] / TILE_UNITS), 'De Seis seal', 'target',
                  use=DE_SEIS_SEAL)  # fmt: skip
    goal = Goal('De Seis seal', place, USE, 25.0, PRESSED, mark=mark, route='Diablo' if stage else '', stage=stage)
    return play, hunt, run, goal


def test_a_seal_found_open_by_a_late_click_still_waits_for_its_boss(monkeypatch):
    # 00:45:48.95 "did not take the click", 00:45:49.80 "At De Seis seal", the seek 0.1 s later; De Seis came at the
    # seal 0.9 s after it opened (take 20261020T214324Z-108, frames 3582 and 3604)
    monkeypatch.setattr(moves, 'SETTLE_FOUND_USED', True)
    play, hunt, run, goal = seal_at_hand(mode=1)
    before = hunt.settled_at
    hunt.operate(run, play.world, goal, None)
    assert hunt.settled_at > before
    assert hunt.settled_at == pytest.approx(run.clock() + SEAL_BRINGS, abs=0.5)


def test_with_the_switch_off_or_off_the_route_an_object_found_used_brings_nothing(monkeypatch):
    monkeypatch.setattr(moves, 'SETTLE_FOUND_USED', False)
    play, hunt, run, goal = seal_at_hand(mode=1)
    before = hunt.settled_at
    hunt.operate(run, play.world, goal, None)
    assert hunt.settled_at == before
    monkeypatch.setattr(moves, 'SETTLE_FOUND_USED', True)
    play, hunt, run, goal = seal_at_hand(mode=1, stage=None)  # an agenda's chest: no renewal at an opened one
    hunt.operate(run, play.world, replace(goal, stage=None), None)
    assert hunt.settled_at == before


# --- progress: a click that did not take, and a new game ---


def test_a_seal_still_closed_after_its_click_is_not_done():
    play = game(area=SANCTUARY)
    progress = Progress(ROUTES, route.PERFORMED, dead=frozenset)
    progress.note(play.world.game_name, SANCTUARY)
    player = me(play.world)
    place = (player.x + 3.0, player.y)
    seal = Target(SANCTUARY, ROOMS, (place[0] / TILE_UNITS, place[1] / TILE_UNITS), 'Vizier seal 1', 'target',
                  use=SEALS[4])  # fmt: skip
    play.thing = Thing(9, SEALS[4], 0, *place)  # mode 0: the click did not take
    route.note_used(play.run(), seal, progress, None)
    step = progress.step(SANCTUARY)
    assert step is not None
    assert step.stage == use('Vizier seal 1')
    play.thing = Thing(9, SEALS[4], 1, *place)
    route.note_used(play.run(), seal, progress, None)
    step = progress.step(SANCTUARY)
    assert step is not None
    assert step.stage == use('Vizier seal 2')


def walk_the_sanctuary(progress: Progress, dead: set[str]) -> list[str]:
    """Every stage of the Sanctuary's script as a run makes it, in order: (kind, mark or boss)."""
    made = []
    for _ in range(20):
        step = progress.step(SANCTUARY)
        if step is None or step.stage.kind == LOOT:
            break
        stage = step.stage
        if stage.kind == USE:
            made.append(stage.mark)
            progress.used(SANCTUARY, stage.mark, (1.0, 1.0), [(1.0, 1.0)])
        else:
            made.append(stage.boss)
            dead.add(stage.boss)
    return made


def test_a_second_game_in_the_same_service_opens_every_seal_and_fights_every_boss_again():
    dead: set[str] = set()
    progress = Progress(ROUTES, route.PERFORMED, dead=lambda: frozenset(dead))
    whole = [*SEAL_ORDER[:2], BOSSES[0], SEAL_ORDER[2], BOSSES[1], *SEAL_ORDER[3:], BOSSES[2], BOSSES[3]]
    progress.note('cyberr98', 107)
    progress.note('cyberr98', SANCTUARY)
    assert walk_the_sanctuary(progress, dead) == whole
    dead.clear()  # terror/tracker.py: the kills of a game are forgotten with it
    progress.note('cyberr99', 107)
    progress.note('cyberr99', SANCTUARY)
    assert progress.facts.used == frozenset()
    assert walk_the_sanctuary(progress, dead) == whole
