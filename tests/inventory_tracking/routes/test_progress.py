"""What is done in this game, and the stage a level is at (levels/routes.md, T6)."""

from pathlib import Path

import pytest

from inventory_tracking.levels.exits import guide_level
from inventory_tracking.levels.guide import lead_first
from inventory_tracking.levels.model import Lead
from inventory_tracking.levels.registry import handler_for
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.model import ENTER, FIGHT, USE, Route, enter, fight, leave, level, loot, stand, use
from inventory_tracking.routes.progress import Facts, Progress, Step, current, done
from tests.inventory_tracking.levels.fixtures import replay


def step_at(progress: Progress, area: int) -> Step:
    """The stage the level is at, which the test knows it has."""
    step = progress.step(area)
    assert step is not None, area
    return step


CAVE = Route(
    'Cave',
    (3,),
    (
        level(3, enter('Cave', 9)),
        level(9, fight('Coldcrow', 'Coldcrow'), loot(), enter('Next level', 13)),
        level(13, use('Super chest'), loot(), leave()),
    ),
)
MAUSOLEUM = Route('Mausoleum', (3,), (level(3, enter('Burial Grounds', 17), alternate=True),))
DOORS = Route('Doors', (3,), (level(50, enter('First', 51), enter('Second', 52)), level(51, use('Portal', 53))))


@pytest.mark.parametrize(
    ('stage', 'entered', 'expected'),
    [
        (enter('Cave', 9), (), False),
        (enter('Cave', 9), (9,), True),
        (enter('Cave', 9), (3, 13), False),
        (use('Portal', 53), (), False),  # a portal is done as a door is: the level behind it was entered
        (use('Portal', 53), (53,), True),
        (use('Super chest'), (13,), False),  # until the step has seen it opened
        (fight('Coldcrow'), (9,), None),  # not judged without word on the dead
        (loot(), (9,), False),  # until a press found the ground clean
        (leave(), (9,), None),
    ],
)
def test_a_way_on_is_done_when_its_level_was_entered_and_the_rest_is_not_judged_yet(stage, entered, expected):
    assert done(13, stage, Facts(frozenset(entered))) is expected


@pytest.mark.parametrize(
    ('entered', 'expected'),
    [
        ((), 'First'),
        ((51,), 'Second'),
        ((52,), 'First'),  # done out of order: the second stays done, the first is still to do
        ((51, 52), None),
    ],
)
def test_the_current_stage_is_the_first_that_is_not_done(entered, expected):
    stage = current(DOORS.scripts[0], Facts(frozenset(entered)))
    assert (stage.mark if stage else None) == expected


def test_a_level_is_at_the_stage_of_its_main_script():
    progress = Progress([MAUSOLEUM, CAVE])

    step = step_at(progress, 3)

    assert (step.route, step.stage) == ('Cave', enter('Cave', 9))
    assert step.script.area == 3
    assert step_at(progress, 13).stage == use('Super chest')
    assert progress.step(1) is None  # no script: a town


def test_entering_the_level_behind_the_door_finishes_the_script():
    progress = Progress([CAVE])
    progress.note('cyber32', 3)
    progress.note('cyber32', 9)

    assert progress.step(3) is None
    assert step_at(progress, 9).stage.kind == FIGHT


def test_a_new_game_forgets():
    progress = Progress([CAVE])
    progress.note('cyber32', 3)
    progress.note('cyber32', 9)

    progress.note('cyber33', 3)

    assert step_at(progress, 3).stage == enter('Cave', 9)


def test_the_menu_and_an_unread_level_change_nothing_within_a_game():
    progress = Progress([CAVE])
    progress.note('cyber32', 9)
    progress.note('cyber32', None)
    assert progress.step(3) is None

    progress.note(None, None)  # the menu: the game is over
    progress.note('cyber32', 3)  # the same name again is another game
    assert progress.step(3) is not None


def test_the_card_leads_with_the_mark_of_a_stage_that_is_performed():
    progress = Progress([CAVE], performed=frozenset((ENTER,)))

    assert progress.lead(3) == Lead('Cave', 9)
    assert progress.lead(9) is None  # the fight is not performed yet: the card keeps its own order
    assert progress.lead(13) is None
    assert progress.lead(1) is None


def test_every_level_of_the_catalogue_with_a_door_first_leads_with_it():
    progress = Progress(ROUTES)

    assert progress.lead(6) == Lead('Forgotten Tower', 20)  # Black Marsh
    assert progress.lead(115) == Lead('Drifter Cavern', 116)  # Glacial Trail
    assert progress.lead(27) == Lead('Monastery Gate', 26)  # Outer Cloister: the Pit, not the Barracks
    assert progress.lead(25) is None  # the Countess: nothing leads on


FIXTURES = sorted(path.stem for path in (Path(__file__).parents[1] / 'fixtures' / 'levels').glob('*.json'))


def led(name: str) -> tuple[Lead | None, list[str]]:
    """The lead of the fixture's level in a new game, and its card's labels with the lead applied."""
    snapshot = replay(name)
    area = snapshot.location.area_id
    lead = Progress(ROUTES).lead(area)
    pois = guide_level(handler_for(area), snapshot).pois
    return lead, [poi.label for poi in lead_first(pois, lead)]


@pytest.mark.parametrize('name', FIXTURES)
def test_on_every_level_dumped_from_the_game_the_card_holds_the_mark_its_stage_leads_with(name):
    lead, labels = led(name)
    if lead is not None:
        assert labels[0] == lead.label


def test_the_levels_dumped_from_the_game_lead_with_their_routes_doors():
    first = {name: labels[0] for name in FIXTURES for lead, labels in [led(name)] if lead is not None}
    assert first['cold_plains_all_known'] == first['cold_plains_entry'] == 'Cave'  # Stony Field without a route
    assert first['black_marsh'] == 'Forgotten Tower'
    assert first['dark_wood'] == 'Underground Passage'  # Black Marsh without a route
    assert first['jail_3'] == 'Inner Cloister'
    assert {first[f'tower_cellar_{n}'] for n in (1, 2, 3, 4)} == {'Next level'}


SEALS = Route(
    'Diablo',
    (107,),
    (level(108, use('Seal 1'), fight('Infector of Souls'), use('Seal 2'), fight('Diablo'), loot(), leave()),),
)
MEPHISTO = Route(
    'Mephisto',
    (101,),
    (level(102, stand('Red portal'), fight('Mephisto'), loot(), use('Red portal', 103), leave()),),
)
PITS = Route('Pit', (111,), (level(125, use('Super chest'), loot(), leave()),))
BOTH = frozenset((ENTER, USE))


def test_an_object_is_used_once_the_step_saw_it_operated_and_a_new_game_forgets():
    progress = Progress([CAVE], performed=BOTH)
    progress.note('cyber32', 13)
    assert progress.lead(13) == Lead('Super chest')

    progress.used(13, 'Super chest', (1022.4, 2004.4), [(1022.4, 2004.4)])

    assert step_at(progress, 13).stage == loot()
    assert progress.lead(13) is None
    progress.note('cyber33', 13)
    assert progress.lead(13) == Lead('Super chest')


def test_a_label_on_several_objects_is_done_when_each_was_used_and_leads_past_those_that_were():
    progress = Progress([PITS], performed=BOTH)
    chests = [(10.0, 10.0), (40.0, 10.0)]

    progress.used(125, 'Super chest', chests[0], chests)

    assert progress.lead(125) == Lead('Super chest', None, frozenset({chests[0]}))
    progress.used(125, 'Super chest', chests[1], chests)
    assert progress.lead(125) is None


def test_a_stage_not_performed_yet_is_passed_for_an_object_of_the_level_but_not_for_a_way_out():
    progress = Progress([SEALS, MEPHISTO, CAVE], performed=BOTH)

    progress.used(108, 'Seal 1', (1.0, 1.0), [(1.0, 1.0)])
    assert progress.lead(108) == Lead('Seal 2')  # past the seal boss: the key goes on, the fight is the player's
    progress.used(108, 'Seal 2', (2.0, 2.0), [(2.0, 2.0)])
    assert step_at(progress, 108).stage == fight('Infector of Souls')
    assert progress.lead(108) is None

    assert progress.lead(102) is None  # not to the red portal with Mephisto alive
    assert progress.lead(9) is None  # nor out of Cave 1 past Coldcrow: the card's own order stands


def test_a_pending_stage_is_not_led_with():
    route = Route('Abaddon', (111,), (level(111, use('Abaddon', 125, pending='the portal is not read')),))
    progress = Progress([route], performed=BOTH)

    assert step_at(progress, 111).stage.pending
    assert progress.lead(111) is None


# --- fights, loot, standing, leaving (Phase 5) ---

COUNTESS = Route('Countess', (6,), (level(25, fight('The Countess', 'Countess'), loot(), leave()),))
ALL = frozenset((ENTER, USE, 'stand', FIGHT, 'loot', 'leave'))


def test_a_fight_is_done_when_the_boss_is_dead_then_the_loot_then_leaving():
    dead: set[str] = set()
    progress = Progress([COUNTESS], ALL, dead=lambda: frozenset(dead))
    progress.note('cyber32', 25)
    assert progress.lead(25) == Lead('Countess')
    assert not progress.ending(25)  # the boss alive

    dead.add('The Countess')
    assert step_at(progress, 25).stage == loot()
    assert progress.lead(25) is None

    assert progress.ending(25)  # the boss dead: what is left is the loot and the way out

    progress.looted(25)
    assert step_at(progress, 25).stage == leave()
    assert progress.ending(25)
    assert not progress.ending(26)  # a level without a script
    progress.note('cyber33', 25)
    dead.clear()
    assert step_at(progress, 25).stage.kind == FIGHT


def test_without_word_on_the_dead_a_fight_holds_its_script_and_is_not_led_with():
    progress = Progress([COUNTESS, CAVE], ALL)

    assert step_at(progress, 25).stage.kind == FIGHT
    assert progress.lead(25) is None
    assert progress.lead(9) is None  # Cave 1: not out past Coldcrow, and not to him for ever


def test_a_stand_is_done_once_the_character_stood_there():
    progress = Progress([MEPHISTO], ALL, dead=frozenset)
    assert progress.lead(102) == Lead('Red portal')

    progress.stood(102, 'Red portal')

    assert step_at(progress, 102).stage == fight('Mephisto')
    assert progress.lead(102) is None  # the fight names no mark: the card's own (Mephisto) leads


def test_the_way_out_is_led_with_once_the_boss_is_dead_and_the_ground_clean():
    progress = Progress([MEPHISTO], ALL, dead=lambda: frozenset({'Mephisto'}))
    progress.stood(102, 'Red portal')
    assert progress.lead(102) is None  # the loot first
    progress.looted(102)
    assert progress.lead(102) == Lead('Red portal', 103)


def test_a_pending_fight_is_still_judged_by_the_dead():
    route = Route('Andariel', (35,), (level(37, fight('Andariel', 'Andariel', pending='no mark'), loot(), leave()),))
    progress = Progress([route], ALL, dead=lambda: frozenset({'Andariel'}))
    assert step_at(progress, 37).stage == loot()


# --- alternates: the route whose levels are terrorized (Phase 6) ---

PIT = Route('Pit', (27,), (level(27, enter('Monastery Gate', 26)), level(26, enter('Tamoe Highland', 7))))
ANDARIEL = Route(
    'Andariel',
    (27,),
    (level(27, enter('Barracks', 28), alternate=True), level(28, enter('Next level', 29)), level(29, leave())),
)
JAIL = Route('Jail', (27,), (level(27, enter('Barracks', 28), alternate=True), level(28, leave(), alternate=True)))


@pytest.mark.parametrize(
    ('terrorized', 'route', 'mark'),
    [
        ((), 'Pit', 'Monastery Gate'),  # nothing terrorized: the main script
        ((28, 29), 'Andariel', 'Barracks'),  # the Barracks and the Jail: the route through them
        ((26, 7, 28), 'Pit', 'Monastery Gate'),  # both: the main script stands
        ((27,), 'Pit', 'Monastery Gate'),  # the level itself says nothing about where to go from it
    ],
)
def test_a_level_follows_the_alternate_whose_levels_ahead_are_terrorized(terrorized, route, mark):
    progress = Progress([PIT, ANDARIEL, JAIL], wanted=lambda area: area in terrorized)

    step = step_at(progress, 27)

    assert (step.route, step.stage.mark) == (route, mark)
    lead = progress.lead(27)
    assert lead is not None
    assert lead.label == mark


def test_without_word_on_the_terror_zones_the_main_script_stands():
    progress = Progress([PIT, ANDARIEL], wanted=lambda area: None)
    assert step_at(progress, 27).route == 'Pit'
    assert step_at(Progress([PIT, ANDARIEL]), 27).route == 'Pit'


def test_the_catalogues_outer_cloister_leads_to_the_barracks_when_the_jail_is_terrorized():
    progress = Progress(ROUTES, wanted=lambda area: area in (28, 29, 30, 31))
    assert progress.lead(27) == Lead('Barracks', 28)
    assert Progress(ROUTES, wanted=lambda area: area in (17, 18, 19)).lead(3) == Lead('Burial Grounds', 17)
    assert Progress(ROUTES, wanted=lambda area: area in (11, 15)).lead(6) == Lead('Hole 1', 11)
