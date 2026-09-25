from pricing.knowledge.assessment.maintenance.recipe_eligibility import audit_recipe_membership


def test_native_recipe_membership_checks_parent_exclusions_capacity_and_order():
    types = {'blade': {'Equiv1': 'weapon'}, 'weapon': {}, 'excluded': {'Equiv1': 'blade'}}
    recipes = {
        'Example': {'complete': 1, 'itype1': 'weapon', 'etype1': 'excluded', 'Rune1': 'first', 'Rune2': 'second'},
        'Disabled': {'complete': 0, 'itype1': 'weapon', 'Rune1': 'first'},
    }
    edge = {'sockets': 2, 'details': {'recipe_id': 'Example', 'rune_codes': ['first', 'second']}}
    base = {'type': 'blade', 'gemsockets': 2}
    result = audit_recipe_membership(base, types, recipes, [edge, edge])
    assert result['state'] == 'reviewed'
    assert result['native_recipe_ids'] == ['Example']
    assert audit_recipe_membership(base, types, recipes, [])['state'] == 'blocked'
    reversed_edge = {**edge, 'details': {**edge['details'], 'rune_codes': ['second', 'first']}}
    assert audit_recipe_membership(base, types, recipes, [reversed_edge])['state'] == 'blocked'
    for impossible in ({'type': 'excluded', 'gemsockets': 2}, {'type': 'blade', 'gemsockets': 1}):
        assert audit_recipe_membership(impossible, types, recipes, [])['state'] == 'excluded'
    assert audit_recipe_membership(base, types, None, [])['state'] == 'pending'
    assert audit_recipe_membership({'type': 'missing', 'gemsockets': 2}, types, recipes, [])['state'] == 'blocked'
    assert audit_recipe_membership({'type': 'missing', 'gemsockets': 0}, types, recipes, [])['state'] == 'excluded'


def test_empty_native_catalog_cannot_prove_no_recipe_exists():
    result = audit_recipe_membership({'type': 'weapon', 'gemsockets': 2}, {'weapon': {}}, {}, [])
    assert result['state'] == 'blocked'
