import copy
import json
from pathlib import Path

from pricing.knowledge.crafting_bases import crafting_bases


ROOT = Path(__file__).parents[3]


def test_cube_recipe_chains_require_mutual_normal_exceptional_elite_identity():
    recipes = json.loads((ROOT / 'third-parties/d2data/json/cubemain.json').read_text())
    bases = json.loads((ROOT / 'pricing/raw/d2data/armor.json').read_text())
    result = crafting_bases(recipes, bases)
    assert len(result) == 24
    assert result['Blood Gloves']['tiers']['Elite']['name'] == 'Vampirebone Gloves'
    assert not any(name.endswith('Weapon') for name in result)
    changed = copy.deepcopy(bases)
    code = result['Blood Gloves']['tiers']['Elite']['code']
    changed[code]['normcode'] = 'invalid'
    assert 'Blood Gloves' not in crafting_bases(recipes, changed)


def test_nonethereal_recipes_require_unambiguous_exact_output():
    from pricing.knowledge.crafting_bases import nonethereal_crafting_recipes

    recipes = json.loads((ROOT / 'third-parties/d2data/json/cubemain.json').read_text())
    result = nonethereal_crafting_recipes(recipes)
    assert len(result) == 36
    key = result['Blood Gloves']['record_key']
    for output in ('usetype,crf,eth', 'useitem,crf', 'usetype,crf,unknown'):
        changed = copy.deepcopy(recipes)
        changed[key]['output'] = output
        assert 'Blood Gloves' not in nonethereal_crafting_recipes(changed)
    changed = copy.deepcopy(recipes)
    changed[key]['enabled'] = 0
    assert 'Blood Gloves' not in nonethereal_crafting_recipes(changed)
    changed = copy.deepcopy(recipes)
    changed['ambiguous'] = {**changed[key], 'output': 'usetype,crf,eth'}
    assert 'Blood Gloves' not in nonethereal_crafting_recipes(changed)
