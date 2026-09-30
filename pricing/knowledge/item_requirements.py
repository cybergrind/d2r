"""Original-base requirements from fixed native properties.

D2MOO source/D2Common/src/Items/Items.cpp (ITEMS_CheckRequirements): add the
percentage adjustment truncated toward zero, then subtract ten for ethereal.
This does not model upgrades, socket additions, or the wearer's own attributes.
"""


def single_skill_level(level, properties, skills):
    """Native class-skill bonuses impose the skill's own required level.

    D2MOO ITEMS_GetRequiredLevel inspects STAT_ITEM_SINGLESKILL after the base,
    quality and socket requirements. Unknown or optional bonuses need review.
    Proc, aura and charge parameters are not single-skill bonuses.
    """
    if type(level) is not int:
        return None
    by_name = {row['skill'].casefold(): row for row in skills.values() if isinstance(row.get('skill'), str)}
    for prop in properties:
        if prop['property'] != 'skill':
            continue
        low, high = prop.get('min'), prop.get('max')
        if type(low) is not int or type(high) is not int or low > high or low < 0:
            return None
        if high == 0:
            continue
        if low == 0:
            return None
        param = prop.get('param')
        skill = (
            skills.get(str(param))
            if type(param) is int
            else by_name.get(param.casefold())
            if isinstance(param, str)
            else None
        )
        required = skill.get('reqlevel') if skill else None
        if type(required) is not int or required < 0:
            return None
        level = max(level, required)
    return level


def fixed_requirements(base, level, modifiers):
    result = {**base, 'level': level}
    percent = 0
    ethereal = False
    for modifier in modifiers:
        low, high = modifier.get('min'), modifier.get('max')
        if type(low) is not int or type(high) is not int or low != high:
            return {**result, 'strength': None, 'dexterity': None}
        if modifier['property'] == 'ease':
            percent += low
        elif modifier['property'] == 'ethereal':
            if low not in (0, 1):
                return {**result, 'strength': None, 'dexterity': None}
            ethereal |= bool(low)
    for attribute in ('strength', 'dexterity'):
        value = base.get(attribute)
        if value is None:
            continue
        product = value * percent
        adjustment = (abs(product) // 100) * (-1 if product < 0 else 1)
        result[attribute] = max(0, value + adjustment - (10 if ethereal else 0))
    return result
