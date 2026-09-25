"""Prove absence of recipe contributions before applying random-affix mechanics."""

from pricing.knowledge.crafting_bases import crafting_recipe_bases


def no_effect(prop, excluded_stats):
    functions = [(prop.get(f'func{i}'), prop.get(f'stat{i}')) for i in range(1, 8) if prop.get(f'func{i}')]
    if not functions:
        return False
    for function, stat in functions:
        if function in (1, 2, 8, 11):
            if not stat or stat in excluded_stats:
                return False
        elif function != 7:  # PropertyFunc7 modifies physical enhanced damage only.
            return False
    return True


def affix_only_bases(recipes, bases, properties, matches, excluded_stats):
    eligible, blocked = set(), set()
    for _, row, codes in crafting_recipe_bases(recipes, bases, matches):
        eligible.update(codes)
        for slot in range(1, 6):
            code = row.get(f'mod {slot}')
            if code and not no_effect(properties.get(code, {}), excluded_stats):
                blocked.update(codes)
    return sorted(eligible - blocked)
