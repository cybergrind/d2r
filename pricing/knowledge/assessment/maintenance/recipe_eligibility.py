"""Native recipe membership cross-check; not a mode, desirability or price policy."""

import re

from pricing.knowledge.utility import type_closure


def audit_recipe_membership(base, types, recipes, edges):
    if recipes is None:
        return {'state': 'pending', 'reason': 'Native recipe catalog not supplied.', 'native_recipe_ids': []}
    if not any(recipe.get('complete') == 1 for recipe in recipes.values()):
        return {'state': 'blocked', 'reason': 'No completed native recipes supplied.', 'native_recipe_ids': []}
    cap = base.get('gemsockets', 0)
    ancestry = type_closure(
        base.get('type'),
        {code: {'equiv1': entry.get('Equiv1'), 'equiv2': entry.get('Equiv2')} for code, entry in types.items()},
    )
    if type(cap) is not int or not 0 <= cap <= 6 or (cap and (not ancestry or ancestry - types.keys())):
        return {'state': 'blocked', 'reason': 'Native capacity or type ancestry incomplete.', 'native_recipe_ids': []}
    expected = set()
    for name, recipe in recipes.items():
        if recipe.get('complete') != 1:
            continue
        runes = tuple(recipe[f'Rune{i}'] for i in range(1, 7) if recipe.get(f'Rune{i}'))
        allowed = {v for k, v in recipe.items() if re.fullmatch(r'itype\d+', k) and v}
        excluded = {v for k, v in recipe.items() if re.fullmatch(r'etype\d+', k) and v}
        if not runes or not allowed:
            return {'state': 'blocked', 'reason': f'Incomplete native recipe: {name}', 'native_recipe_ids': []}
        if cap >= len(runes) and ancestry & allowed and not ancestry & excluded:
            expected.add((name, runes, len(runes)))
    observed = {
        (r['details'].get('recipe_id'), tuple(r['details'].get('rune_codes', ())), r.get('sockets')) for r in edges
    }
    missing, extra = expected - observed, observed - expected
    return {
        'state': 'blocked' if missing or extra else 'reviewed' if expected else 'excluded',
        'reason': (
            'Cached/native recipe membership differs.'
            if missing or extra
            else 'Native type/capacity/rune order agree; mode availability and preparation remain separate.'
            if expected
            else 'No completed native recipe fits this type and capacity; not a value judgment.'
        ),
        'native_recipe_ids': sorted({name for name, _, _ in expected}),
        'missing_edges': sorted(missing, key=repr),
        'unexpected_edges': sorted(extra, key=repr),
    }
