"""Angelic Non-Ladder bonuses must not inherit the Season 15 Ladder changes."""

from pathlib import Path

import pytest

from pricing.knowledge.definitions import build_definitions


@pytest.fixture(scope='module')
def compiled():
    return build_definitions(Path(__file__).resolve().parents[3])


@pytest.mark.parametrize('name', ['Angelic Halo', 'Angelic Wings', 'Angelic Mantle', 'Angelic Sickle'])
def test_ordinary_angelic_set_is_the_non_ladder_default(compiled, name):
    row = next(r for r in compiled['rows'] if r['name'] == name)
    assert row['set_definition'].get('FCode5') is None  # No additional full-set +1 skill.
    assert row['game_definition'].get('aprop2b') is None  # No Ladder three-piece addition.
    assert row['game_definition'].get('firstLadderSeason') is None
    assert row['source']['path'] == 'third-parties/d2data/json/base/setitems.json'
    archived = row['ladder_definition']
    assert archived['table_id'] == row['table_id']
    assert archived['set_definition']['FCode5'] == 'allskills'
    assert row['mode_review']['scope'] == 'softcore_non_ladder'
    for path in row['mode_review']['sources']:
        assert path in compiled['inputs']


def test_ordinary_angelic_partial_bonuses_are_preserved(compiled):
    rows = {r['name']: r for r in compiled['rows'] if r['rarity'] == 'set'}
    assert rows['Angelic Halo']['game_definition']['aprop1a'] == 'att/lvl'
    assert rows['Angelic Wings']['game_definition']['aprop2a'] == 'allskills'
    assert rows['Angelic Sickle']['ladder_definition']['game_definition']['aprop2b'] == 'dmg'
    assert rows['Angelic Mantle']['ladder_definition']['game_definition']['aprop2b'] == 'dmg-undead'


def test_portable_item_facts_do_not_reintroduce_ladder_set_bonuses():
    from pricing.knowledge.facts import build_item_facts

    document = build_item_facts(Path(__file__).resolve().parents[3])
    for name in ('Angelic Mantle', 'Angelic Sickle'):
        row = next(r for r in document['rows'] if r['name'] == name)
        assert row['source'] == 'third-parties/d2data/json/base/setitems.json'
        assert not any(r['property'] in ('dmg', 'dmg-undead') for r in row['conditional_effects'])
