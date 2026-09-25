from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers.definitions import named_definitions
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_normal_unique_upgrade_is_two_ordered_recipes_with_separate_costs():
    from pricing.knowledge.assessment.mechanics.upgrades import upgrade_paths

    item = facts('Heavy Belt', 'unique', 'Goldwrap')
    before = item.to_dict()
    routes = upgrade_paths(item)
    assert [r.target_name for r in routes] == ['Battle Belt', 'Troll Belt']
    elite = routes[1].to_dict()
    assert [step['level_requirement_penalty'] for step in elite['steps']] == [5, 7]
    assert elite['steps'][0]['resources'] == ['Tal Rune', 'Shael Rune', 'Perfect Diamond']
    assert elite['steps'][1]['resources'] == ['Ko Rune', 'Lem Rune', 'Perfect Diamond']
    assert elite['steps'][0]['target_code'] == elite['steps'][1]['source_code']
    assert 'wearer_requirements' in elite['preconditions']
    assert item.to_dict() == before
    with pytest.raises(TypeError):
        routes[1].steps[0]['target_code'] = 'invalid'


def test_set_upgrades_use_nonladder_recipe_and_elite_items_have_no_route():
    from pricing.knowledge.assessment.mechanics.upgrades import upgrade_paths

    item = facts('Plated Belt', 'set', "Sigon's Wrap")
    assert [r.target_name for r in upgrade_paths(item)] == ['War Belt', 'Colossus Girdle']
    assert upgrade_paths(item)[0].steps[0]['source'].endswith('#152')
    assert upgrade_paths(facts('Shako', 'unique', 'Harlequin Crest')) == ()
    assert upgrade_paths(facts('Heavy Belt', 'magic')) == ()


def test_captured_upgrade_needs_identity_and_only_offers_remaining_step():
    from pricing.knowledge.assessment.mechanics.upgrades import upgrade_paths

    item = facts('Battle Belt', 'unique', 'Goldwrap')
    assert upgrade_paths(item) == ()
    item = replace(
        item,
        provenance={
            'capture': {
                'item_identity': {
                    'table': 'unique',
                    'table_id': named_definitions()['unique', 'Goldwrap']['table_id'],
                }
            }
        },
    )
    paths = upgrade_paths(item)
    assert len(paths) == 1
    assert len(paths[0].steps) == 1
    assert paths[0].target_name == 'Troll Belt'
    assert upgrade_paths(replace(item, identified=False)) == ()


def test_engine_exposes_upgrade_routes_without_inventing_prices_from_incomplete_stats():
    from pricing.knowledge.assessment.engine import assess
    from tests.pricing.knowledge.assessment.test_base_use import capture

    extraction = capture('Heavy Belt', quality='unique', sockets=0, ethereal=False, ed=0, ar=0)
    extraction['item']['name'] = 'Goldwrap'
    result = assess(extraction, profiles=[])
    assert [row['target_name'] for row in result['upgrade_paths']] == ['Battle Belt', 'Troll Belt']
    assert result['facts']['base_name'] == 'Heavy Belt'
    assert result['comparison_requests'] == []


def test_rare_weapon_and_armor_use_their_own_upgrade_recipes():
    from pricing.knowledge.assessment.mechanics.upgrades import upgrade_paths

    weapon = upgrade_paths(facts('Cinquedeas', 'rare', 'Dread Edge'))
    assert len(weapon) == 1
    assert weapon[0].target_name == 'Fanged Knife'
    assert weapon[0].steps[0]['resources'] == ('Fal Rune', 'Um Rune', 'Perfect Sapphire')
    assert weapon[0].steps[0]['source'].endswith('#135')
    armor = upgrade_paths(facts('Heavy Belt', 'rare'))
    assert armor[0].steps[0]['resources'] == ('Ral Rune', 'Thul Rune', 'Perfect Amethyst')
    assert armor[1].steps[-1]['resources'] == ('Ko Rune', 'Pul Rune', 'Perfect Amethyst')
    assert upgrade_paths(facts('Heavy Belt', 'crafted')) == ()
