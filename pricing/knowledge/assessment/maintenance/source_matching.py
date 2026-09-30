"""Structural requirements used to validate source-review claims."""


def requires_predicate(predicate, expected):
    """Conservative implication for exact predicates and all/any composition."""
    if predicate == expected:
        return True
    if 'all' in expected:
        return bool(expected['all']) and all(requires_predicate(predicate, child) for child in expected['all'])
    if 'all' in predicate:
        return any(requires_predicate(child, expected) for child in predicate['all'])
    if 'any' in predicate:
        return bool(predicate['any']) and all(requires_predicate(child, expected) for child in predicate['any'])
    return False


def role_requires(role, expected):
    return requires_predicate(
        {'all': [role.get('must', {}), *(d['when'] for d in role.get('depends_on', []) if d.get('required', True))]},
        expected,
    )


def requires(node, expected):
    if node == expected:
        return True
    if isinstance(node, dict) and isinstance(node.get('all'), list):
        return any(requires(child, expected) for child in node['all'])
    if isinstance(node, dict) and isinstance(node.get('any'), list) and node['any']:
        return all(requires(child, expected) for child in node['any'])
    return False


def requires_eq(predicate, op, field, value):
    if 'all' in predicate:
        return any(requires_eq(child, op, field, value) for child in predicate['all'])
    if 'any' in predicate:
        return bool(predicate['any']) and all(requires_eq(child, op, field, value) for child in predicate['any'])
    return predicate == {'op': op, 'field': field, 'value': value}


# Only reviewed native Hustle variants with explicit guide equipment slots.
HUSTLE_VARIANTS = {
    'Hustle (armor)': ({'Body Armor', 'Body Armors'}, {'tors'}),
    'Hustle (weapon)': ({'Weapon', 'Weapon-Swap'}, {'abow', 'bow', 'pole', 'spea', 'swor'}),
}


def occurrence_name_matches(row, role, name):
    if row.get('name') == name:
        return True
    if row.get('name') != 'Hustle' or row.get('category') != 'runeword' or name not in HUSTLE_VARIANTS:
        return False
    slots, types = HUSTLE_VARIANTS[name]
    return (
        row.get('slot') in slots
        and role.get('slot') == row.get('slot')
        and role.get('names') == [name]
        and bool(role.get('types'))
        and set(role['types']) <= types
        and requires_eq(role.get('must', {}), 'fact_eq', 'runeword', name)
    )


def occurrence_quality_matches(row, role):
    if row.get('category') != 'runeword':
        return row.get('category') in role.get('qualities', [])
    recipe_required = requires_eq(role.get('must', {}), 'fact_eq', 'runeword', row.get('name')) or any(
        occurrence_name_matches(row, role, name) and requires_eq(role.get('must', {}), 'fact_eq', 'runeword', name)
        for name in role.get('names', [])
    )
    return bool({'normal', 'superior', 'low_quality'}.intersection(role.get('qualities', []))) and recipe_required
