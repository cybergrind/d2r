import copy
import json
from pathlib import Path

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.crafting_triggers import crafting_triggers


ROOT = Path(__file__).parents[3]


def test_recipe_trigger_compiler_preserves_base_and_rejects_unknown_semantics():
    data = metadata()
    bases = {b['code']: b for b in data['bases'].values()}
    recipes = json.loads((ROOT / 'third-parties/d2data/json/cubemain.json').read_text())
    key, row = next((k, r) for k, r in recipes.items() if r.get('description', '').endswith(' -> Hit Power Ring'))
    properties = json.loads((ROOT / 'third-parties/d2data/json/properties.json').read_text())
    stat_ids = {r['name']: int(k) for k, r in data['stats'].items()}
    skill_ids = {r['name']: int(k) for k, r in data['skills'].items()}

    def compile_row(recipe):
        return crafting_triggers(
            {key: recipe}, bases, properties, stat_ids, skill_ids, lambda item_type, allowed: item_type in allowed
        )

    result = compile_row(row)
    ring = next(b['code'] for b in bases.values() if b['name'] == 'Ring')
    assert result == {ring: [{'stat_id': 201, 'skill_id': 44, 'level': 4, 'chance': 5, 'recipe_key': key}]}
    for update in ({'mod 1 max': 0}, {'output': 'useitem,crf'}, {'input 1': 'unreviewed,mag'}):
        with pytest.raises(ValueError, match=r'[Cc]rafted'):
            compile_row({**row, **update})
    assert compile_row({**row, 'enabled': 0}) == {}
    changed = copy.deepcopy(properties)
    changed['gethit-skill']['func1'] = 99
    with pytest.raises(ValueError, match=r'[Cc]rafted'):
        crafting_triggers(
            {key: row}, bases, changed, stat_ids, skill_ids, lambda item_type, allowed: item_type in allowed
        )
