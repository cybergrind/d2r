from pricing.knowledge.per_level_effects import fixed_per_level_effects


def test_fixed_per_level_compiler_keeps_valshift_and_rejects_random_coefficients():
    record = {'prop1': 'hp/lvl', 'par1': 12}
    props = {'hp/lvl': {'func1': 17, 'stat1': 'item_hp_perlevel'}}
    stats = {
        'item_hp_perlevel': {'*ID': 216, 'op': 2, 'op base': 'level', 'op param': 3, 'ValShift': 8, 'descfunc': 19}
    }
    assert fixed_per_level_effects(record, props, stats) == [
        {'stat_id': 216, 'coefficient_raw': 3072, 'denominator': 2048}
    ]
    assert fixed_per_level_effects({'prop1': 'hp/lvl', 'min1': 8, 'max1': 12}, props, stats) == []
    assert (
        fixed_per_level_effects(record, props, {'item_hp_perlevel': {**stats['item_hp_perlevel'], 'op base': 'time'}})
        == []
    )


def test_recipe_fixed_fallback_and_variable_life_coefficients_stay_separate():
    from pricing.knowledge.definition_store import catalog

    leaf = catalog().runewords['Leaf']
    assert leaf['fixed_per_level_effects'] == ({'stat_id': 214, 'coefficient_raw': 16, 'denominator': 8},)
    fortitude = catalog().runewords['Fortitude']
    assert not fortitude['fixed_per_level_effects']
    assert fortitude['variable_per_level_effects'] == (
        {'stat_id': 216, 'minimum_raw': 2048, 'maximum_raw': 3072, 'step_raw': 256, 'denominator': 2048},
    )
