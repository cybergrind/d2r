import json
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.base_use import assess_runeword_base, recipe_catalog
from pricing.knowledge.assessment.mechanics.preparation import prepare_sockets
from tests.pricing.knowledge.assessment.test_base_use import capture, word


@pytest.mark.parametrize(
    ('base', 'word_name', 'recipe_id'),
    [
        ('Monarch', 'Spirit', '126'),
        ('Archon Plate', 'Fortitude', '123'),
        ('Phase Blade', 'Grief', '124'),
        ('Helm', 'Lore', '125'),
    ],
)
def test_socket_costs_match_pinned_cube_recipe(base, word_name, recipe_id):
    game = Path('third-parties/d2data/json')
    recipe = json.loads((game / 'cubemain.json').read_text())[recipe_id]
    misc = json.loads((game / 'misc.json').read_text())
    edge = next(
        r for r in recipe_catalog() if r.get('name') == base and r.get('details', {}).get('runeword') == word_name
    )
    facts = normalize(capture(base, sockets=0, quality='normal', ethereal=False))
    options = {o.action: o for o in prepare_sockets(facts, edge).options}
    cube = options['cube_socket'].to_dict()
    assert cube['resources'] == [{'name': misc[recipe[f'input {i}']]['name'], 'quantity': 1} for i in (2, 3, 4)]
    assert cube['source'] == f'third-parties/d2data/json/cubemain.json#{recipe_id}'
    assert 'horadric_cube' in cube['preconditions']
    assert 'ingredients_available' in cube['preconditions']
    assert options['larzuk'].to_dict()['resources'] == [{'name': 'Larzuk socket reward', 'quantity': 1}]
    assert 'unused_socket_reward' in options['larzuk'].preconditions


def test_removal_cost_is_not_a_runeword_or_item_price():
    game = Path('third-parties/d2data/json')
    recipe = json.loads((game / 'cubemain.json').read_text())['141']
    misc = json.loads((game / 'misc.json').read_text())
    facts = normalize(capture(contents='filled'))
    use = word(assess_runeword_base(facts), 'Infinity')
    option = use['preparation'][0]
    assert option['resources'] == [
        {'name': 'Hel Rune', 'quantity': 1},
        {'name': 'Scroll of Town Portal', 'quantity': 1},
    ]
    assert option['source'].endswith('cubemain.json#141')
    assert option['resources'] == [{'name': misc[recipe[f'input {i}']]['name'], 'quantity': 1} for i in (2, 3)]
    assert recipe['output'] == '"useitem,uns"'
    assert option['destroys_contents'] is True
    assert 'price' not in option
    assert facts.socket_contents == 'filled'


@pytest.mark.parametrize('caps', [[], [0, 4, 6], [None, 4, 6]])
@pytest.mark.parametrize('quality', ['normal', 'low_quality'])
def test_missing_socket_mechanics_do_not_create_preparation_requests(caps, quality):
    facts = normalize(capture('Crystal Sword', sockets=0, quality=quality, ethereal=False))
    recipe = {'sockets': 4, 'details': {'runeword': 'Spirit', 'socket_options': {'maximum_by_ilvl_bracket': caps}}}
    result = prepare_sockets(facts, recipe)
    assert result.status == 'unverified'
    assert result.options == ()
    assert any('socket limits' in message for message in result.messages)
