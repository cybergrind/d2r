"""Compile recipe proc possibilities per concrete base for offline comparisons."""

from pricing.knowledge.crafting_bases import crafting_recipe_bases
from pricing.knowledge.named_triggers import EVENTS, fixed_triggers


def crafting_triggers(recipes, bases, properties, stat_ids, skill_ids, matches):
    result = {}
    for key, row, codes in crafting_recipe_bases(recipes, bases, matches):
        effects = []
        for slot in range(1, 6):
            code = row.get(f'mod {slot}')
            if code not in EVENTS:
                if properties.get(code, {}).get('func1') == 11:
                    raise ValueError('Unreviewed crafted trigger property')
                continue
            record = {
                'prop1': code,
                **{
                    f'{target}1': row.get(f'mod {slot} {suffix}')
                    for target, suffix in [('par', 'param'), ('min', 'min'), ('max', 'max')]
                },
            }
            compiled = fixed_triggers(record, properties, stat_ids, skill_ids)
            if len(compiled) != 1:
                raise ValueError('Unverified crafted trigger parameters')
            effects.append({**compiled[0], 'recipe_key': key})
        for code in codes:
            result.setdefault(code, []).extend(effects)
    return result
