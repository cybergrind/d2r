"""The reviver table (table.py, revivers.json): what it says, and that it is what the game's tables say."""

import pytest

from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.policy import REACH

from .scenarios import SCENARIOS
from .table import EXCEL, derive, table


def test_the_table_is_what_the_dumped_game_tables_give():
    if not (EXCEL / 'monstats.txt').exists():
        pytest.skip('the excel dump (pricing/raw/game-excel) is not on this machine')
    assert derive() == table()


def test_every_row_names_the_monster_the_bundled_combat_tables_have_under_that_txt_id():
    bundled = tables()['monsters']
    listed = [*table()['revivers'], *table()['self_revivers'], *table()['spawners']]
    listed += [entry for found in table()['raised'].values() for entry in found]
    known = [entry for entry in listed if str(entry['txt']) in bundled]
    assert len(known) > 100
    assert all(bundled[str(entry['txt'])]['Id'] == entry['id'] for entry in known)


def test_the_revivers_are_the_three_families_with_a_raise_skill():
    by_ai: dict[str, set[str]] = {}
    for entry in table()['revivers']:
        by_ai.setdefault(entry['ai'], set()).add(entry['skill'])
    assert by_ai == {
        'FallenShaman': {'Resurrect'},
        'GreaterMummy': {'Resurrect2'},
        'FetishShaman': {'Resurrect2'},
    }
    assert all(entry['raise_chance'] and entry['raise_frames'] for entry in table()['revivers'])


def test_every_reviver_raises_from_further_than_the_blades_fly():
    # What makes a reviver a problem of its own: it can stand where no cast reaches it (REACH 22.1
    # units) and still raise what is killed in front of the character. Only the fetish shamans come
    # to the corpse (`raise_close`).
    assert min(entry['raise_range'] for entry in table()['revivers']) > REACH
    close = {entry['ai'] for entry in table()['revivers'] if 'raise_close' in entry}
    assert close == {'FetishShaman'}


def test_a_shaman_raises_other_shamans_and_an_unraveler_does_not_raise_unravelers():
    raised = {ai: {entry['id'] for entry in found} for ai, found in table()['raised'].items()}
    shamans = {entry['id'] for entry in table()['revivers'] if entry['ai'] == 'FallenShaman'}
    mummies = {entry['id'] for entry in table()['revivers'] if entry['ai'] == 'GreaterMummy'}
    assert shamans <= raised['FallenShaman']
    assert not mummies & raised['GreaterMummy']  # they are hUndead; the rule asks for lUndead


def test_the_self_revivers_and_spawners_are_listed_apart():
    assert {entry['ai'] for entry in table()['self_revivers']} == {'ReanimatedHorde'}
    assert all(entry['spawns_txt'] is not None for entry in table()['spawners'])


@pytest.mark.parametrize('scenario', SCENARIOS, ids=lambda s: s.name)
def test_a_scenario_is_set_in_an_area_that_spawns_its_reviver_and_can_be_terrorized(scenario):
    rows = {entry['txt']: entry for entry in table()['revivers']}
    for raiser in scenario.raisers:
        txt = next(b.txt for b in scenario.bodies if b.unit == raiser.unit)
        area = next(a for a in rows[txt]['areas'] if a['area'] == scenario.area)
        assert area['zone'] is not None
        assert rows[txt]['herald']
