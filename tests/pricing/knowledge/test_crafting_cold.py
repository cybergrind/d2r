import json
from pathlib import Path

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.crafting_cold import crafting_affix_only_cold
from pricing.knowledge.crafting_poison import crafting_affix_only_poison


@pytest.mark.parametrize(
    ('compile_element', 'stat'),
    [
        (crafting_affix_only_cold, 'coldlength'),
        (crafting_affix_only_poison, 'poisonlength'),
        (crafting_affix_only_poison, 'poison_count'),
    ],
)
def test_any_recipe_element_contribution_or_unknown_function_blocks_that_base(compile_element, stat):
    root = Path(__file__).parents[3]
    recipes = json.loads((root / 'third-parties/d2data/json/cubemain.json').read_text())
    row = next(r for r in recipes.values() if r.get('description', '').endswith(' -> Hit Power Ring'))
    properties = json.loads((root / 'third-parties/d2data/json/properties.json').read_text())
    bases = {b['code']: b for b in metadata()['bases'].values()}
    ring = next(b['code'] for b in bases.values() if b['name'] == 'Ring')

    def compile_rows(rows, props=properties):
        return compile_element(rows, bases, props, lambda kind, allowed: kind in allowed)

    assert compile_rows({'safe': row}) == [ring]
    changed = {**row, 'mod 5': 'test-effect'}
    for effect in ({'func1': 1, 'stat1': stat}, {'func1': 999, 'stat1': 'maxhp'}, {}):
        props = {**properties, 'test-effect': effect}
        assert compile_rows({'safe': row, 'unsafe': changed}, props) == []
    assert compile_rows({'safe': row, 'disabled': {**changed, 'enabled': 0}}) == [ring]
