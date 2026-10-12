"""The route catalogue as it stands: complete, ending, and naming only what the levels have."""

from inventory_tracking.levels.presets import LEVEL_NAMES
from inventory_tracking.macros import skills
from inventory_tracking.routes import model
from inventory_tracking.routes.catalog import EXEMPT, ROUTES
from inventory_tracking.routes.check import main_scripts, pending, problems
from inventory_tracking.routes.links import TOWNS
from inventory_tracking.routes.model import FIGHT, LEAVE, LOOT, STAND, USE
from inventory_tracking.terror import elites
from inventory_tracking.terror.tracker import SLAIN_BOSSES


def test_the_catalogue_is_sound():
    # Complete (T2), every route ends (T3), every stage names what its level has (T4).
    assert problems(ROUTES, EXEMPT) == []


def test_every_level_has_a_script_or_a_reason_for_none():
    mains = main_scripts(ROUTES)

    assert set(mains) | set(EXEMPT) == set(LEVEL_NAMES)
    assert not set(mains) & set(EXEMPT)
    assert all(EXEMPT.values())


def test_from_every_level_the_main_scripts_lead_to_leaving_the_game():
    mains = main_scripts(ROUTES)
    for start in mains:
        area, steps = start, 0
        while mains[area].stages[-1].kind != LEAVE:
            area, steps = mains[area].way_on.to, steps + 1
            assert steps < len(mains), f'no end from level {start}'


def route(name):
    [found] = [r for r in ROUTES if r.name == name]
    return found


def test_the_countess_route_is_the_tower_to_its_end_then_the_kill_the_loot_and_the_next_game():
    countess = route('Countess')

    assert countess.starts == (6,)  # Black Marsh
    assert [script.area for script in countess.scripts] == [6, 20, 21, 22, 23, 24, 25]
    assert [(s.kind, s.boss) for s in countess.scripts[-1].stages] == [(FIGHT, 'The Countess'), (LOOT, ''), (LEAVE, '')]


def test_cold_plains_goes_to_the_cave_and_its_second_level():
    assert [script.area for script in route('Cave').scripts] == [3, 9, 13]
    assert not route('Cave').scripts[0].alternate
    assert route('Mausoleum').scripts[0].alternate  # the Burial Grounds are another route


def test_mephisto_is_the_portal_spot_the_opener_the_kill_the_loot_the_portal_and_the_next_game():
    durance_3 = route('Mephisto').scripts[-1]

    assert durance_3.area == 102
    assert [(s.kind, s.mark or s.boss) for s in durance_3.stages] == [
        (STAND, 'Red portal'),
        (FIGHT, 'Mephisto'),
        (LOOT, ''),
        (USE, 'Red portal'),
        (LEAVE, ''),
    ]
    assert durance_3.stages[0].by == skills.BLADE_WARP
    assert durance_3.stages[1].opener == (skills.DEATH_MARK, skills.SIGIL_LETHARGY)
    assert durance_3.stages[3].to in TOWNS


def test_the_seals_are_opened_west_north_east_before_diablo():
    stages = route('Diablo').scripts[-1].stages

    assert [s.mark or s.boss for s in stages if s.kind in (USE, FIGHT)] == [
        'Vizier seal 1',
        'Vizier seal 2',
        'Grand Vizier of Chaos',
        'De Seis seal',
        'Lord De Seis',
        'Infector seal 1',
        'Infector seal 2',
        'Infector of Souls',
        'Diablo',
    ]


def test_the_skills_a_stage_names_are_the_macros_own():
    assert (model.BLADE_WARP, model.DEATH_MARK, model.SIGIL_LETHARGY) == (
        skills.BLADE_WARP,
        skills.DEATH_MARK,
        skills.SIGIL_LETHARGY,
    )


def test_the_stages_that_cannot_be_acted_on_yet_are_these():
    # The list only shrinks: a pending stage whose mark exists fails `problems` above.
    assert sorted({(name, area) for name, area, _ in pending(ROUTES)}) == [
        ('Abaddon', 111),
        ('Infernal Pit', 117),
        ('Lower Kurast', 79),
        ('Pit of Acheron', 112),
    ]


def test_every_boss_a_route_fights_has_a_name_the_monster_tracker_gives_its_death():
    named = frozenset(elites.table().supers.values()) | frozenset(SLAIN_BOSSES.values())
    stages = [stage for route in ROUTES for script in route.scripts for stage in script.stages]
    fought = {stage.boss for stage in stages if stage.kind == FIGHT}
    assert fought - named == set()
