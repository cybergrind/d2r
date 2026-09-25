"""Reviewed socket recipes from pinned d2data cubemain.json (fc469993502d).

These are consumed resources, never Ist estimates or proof of resource ownership.
Runtime uses reviewed data here, without reading the reference checkout.
"""

from dataclasses import replace

from pricing.knowledge.assessment.registry import classify


CUBE_RECIPES = {
    'armor': ('123', ('Tal Rune', 'Thul Rune', 'Perfect Topaz')),
    'weapon': ('124', ('Ral Rune', 'Amn Rune', 'Perfect Amethyst')),
    'helm': ('125', ('Ral Rune', 'Thul Rune', 'Perfect Sapphire')),
    'shield': ('126', ('Tal Rune', 'Amn Rune', 'Perfect Ruby')),
}
CLEAR_RECIPE = ('141', ('Hel Rune', 'Scroll of Town Portal'))


def with_costs(option, facts):
    if option.action == 'larzuk':
        resources = ('Larzuk socket reward',)
        prerequisites = ('unused_socket_reward',)
        source = None
    else:
        recipe = CLEAR_RECIPE if option.action == 'clear_sockets' else CUBE_RECIPES.get(classify(facts)[0])
        if recipe is None:
            raise ValueError('No reviewed socket recipe for this item family')
        row_id, resources = recipe
        prerequisites = ('horadric_cube', 'ingredients_available')
        source = f'third-parties/d2data/json/cubemain.json#{row_id}'
    return replace(
        option,
        resources=tuple({'name': name, 'quantity': 1} for name in resources),
        preconditions=tuple(dict.fromkeys((*option.preconditions, *prerequisites))),
        source=source,
    )
