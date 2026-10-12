"""The catalogue check on catalogues made wrong on purpose: one fault each."""

from inventory_tracking.levels.presets import LEVEL_NAMES
from inventory_tracking.routes.check import problems, unmet
from inventory_tracking.routes.model import Route, clear, enter, fight, leave, level, loot, stand, use


# Every level but the ones a test scripts is exempt, so only the fault under test is reported.
def check(*routes, also_exempt=()):
    scripted = {script.area for route in routes for script in route.scripts if not script.alternate}
    exempt = {area: 'not under test' for area in LEVEL_NAMES if area not in scripted or area in also_exempt}
    return problems(routes, exempt)


PIT = Route(
    'Pit',
    (27,),
    (
        level(27, enter('Monastery Gate', 26)),
        level(26, enter('Tamoe Highland', 7)),
        level(7, enter('Pit', 12)),
        level(12, enter('Next level', 16)),
        level(16, use('Super chest'), loot(), leave()),
    ),
)


def test_a_sound_route_has_no_problems():
    assert check(PIT) == []


def test_a_level_with_no_script_and_no_exemption_is_reported():
    exempt = {area: 'not under test' for area in LEVEL_NAMES if area not in (7, 12, 16, 26, 27, 39)}

    assert problems((PIT,), exempt) == ['Moo Moo Farm (39) has no script and no exemption']


def test_a_level_cannot_be_exempt_and_scripted_or_have_two_main_scripts():
    again = Route('Pit again', (1,), (level(16, clear(), leave()),))

    assert check(PIT, also_exempt=(16,)) == ['Pit 2 is exempt and has a script']
    assert check(PIT, again) == ['Pit 2 has 2 main scripts: Pit, Pit again']


def test_a_script_must_end_by_leaving_the_level_or_the_game():
    stuck = Route('Pit', (27,), (*PIT.scripts[:-1], level(16, use('Super chest'), loot())))
    late = Route('Pit', (27,), (*PIT.scripts[:-1], level(16, leave(), loot(), leave())))
    after = Route('Pit', (27,), (*PIT.scripts[:3], level(12, enter('Next level', 16), loot()), PIT.scripts[4]))

    assert check(stuck) == ['Pit, Pit 2: ends without leaving the level or the game']
    assert check(late) == ['Pit, Pit 2: stages after leave']
    assert check(after) == ['Pit, Pit 1: stages after the way on']


def test_a_route_is_a_chain_and_its_levels_are_joined_in_the_game():
    gap = Route('Pit', (27,), (PIT.scripts[0], *PIT.scripts[2:]))
    wrong = Route('Pit', (27,), (*PIT.scripts[:2], level(7, enter('Pit', 16)), PIT.scripts[4]))

    assert check(gap) == [
        'Pit, Outer Cloister: does not lead to Tamoe Highland, the next level of the route',
        'Outer Cloister: the route stops at Monastery Gate, which has no script',
    ]
    assert check(wrong) == ['Pit, Tamoe Highland: enter Pit: Pit 2 is not joined to this level']


def test_a_route_starts_at_a_waypoint_on_it_or_in_a_town():
    assert check(Route('Pit', (7,), PIT.scripts)) == ['Pit: start Tamoe Highland has no waypoint']
    assert check(Route('Pit', (3,), PIT.scripts)) == ['Pit: start Cold Plains is not on the route']
    assert check(Route('Pit', (), PIT.scripts)) == ['Pit: no start']
    assert check(Route('Pit', (1,), PIT.scripts)) == []  # from town


def test_a_route_that_circles_or_runs_into_a_level_without_a_script_never_ends():
    circle = Route('Jail', (29,), (level(29, enter('Next level', 30)), level(30, enter('Jail 1', 29))))
    stops = Route('Jail', (29,), (level(29, enter('Next level', 30)),))

    assert check(circle) == [
        'Jail 1: the route never ends: Jail 1 -> Jail 2 -> Jail 1',
        'Jail 2: the route never ends: Jail 2 -> Jail 1 -> Jail 2',
    ]
    assert check(stops) == ['Jail 1: the route stops at Jail 2, which has no script']


def test_a_stage_names_a_mark_the_level_has():
    typo = Route('Pit', (27,), (*PIT.scripts[:2], level(7, enter('Pitt', 12)), *PIT.scripts[3:]))
    room = Route('Pit', (27,), (*PIT.scripts[:4], level(16, use('Pit 1'), loot(), leave())))
    no_object = Route('Kurast', (79,), (level(79, use('Super chests'), leave()),))
    nowhere = Route('Kurast', (79,), (level(79, stand('Bonfire'), fight('Stormtree', 'Bonfire'), leave()),))

    assert check(typo) == ["Pit, Tamoe Highland: enter Pitt: no mark 'Pitt'"]
    assert check(room) == ["Pit, Pit 2: use Pit 1: no mark 'Pit 1'"]
    assert check(no_object) == ["Kurast, Lower Kurast: use Super chests: the mark 'Super chests' is not on an object"]
    assert check(nowhere) == [
        "Kurast, Lower Kurast: stand at Bonfire: no mark 'Bonfire'",
        "Kurast, Lower Kurast: fight Stormtree: no mark 'Bonfire'",
    ]


def test_a_fight_names_a_boss_of_the_game():
    route = Route('Cellar', (1,), (level(25, fight('Countess', 'Countess'), leave()),))

    assert check(route) == ['Cellar, Tower Cellar 5: fight Countess: the game has no boss of that name']


def test_a_pending_stage_is_let_through_until_its_mark_exists():
    waiting = Route('Kurast', (79,), (level(79, use('Super chests', pending='the camp, not the chests'), leave()),))
    stale = Route('Pit', (27,), (*PIT.scripts[:4], level(16, use('Super chest', pending='no mark'), loot(), leave())))

    assert check(waiting) == []
    assert check(stale) == ['Pit, Pit 2: use Super chest (pending): is pending, but the level has what it needs']


def test_every_level_has_its_own_way_out_to_a_level_it_is_joined_to():
    # No handler names the Tower Cellar from the Forgotten Tower: the generic way out does (levels/exits.py).
    assert unmet(20, enter('Tower Cellar 1', 21)) is None
    assert unmet(20, enter('The cellar', 21)) == "no mark 'The cellar'"
    assert unmet(4, use('Tristram', 38)) is None  # the portal object the Stony Field mark names
    assert unmet(25, fight('The Countess')) is None  # a fight where the character stands needs no mark
