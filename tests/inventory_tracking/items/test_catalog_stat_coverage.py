"""Exercise every encoded endpoint in the bundled item/affix definitions.

This checks decoder coverage, not completeness of the roll-range extraction or
every possible combination of socket, set and item effects.
"""

from inventory_tracking.items.metadata import decode_stats, metadata


def definitions():
    for family in ('identities', 'affixes'):
        for table in metadata()[family].values():
            yield from table.values()


def test_catalog_roll_endpoints_decode_without_losing_native_values():
    catalog = metadata()
    checked = set()
    for item in definitions():
        for key, limits in item.get('roll_ranges', {}).items():
            stat_id, _, layer = key.partition(':')
            for bound in ('min', 'max'):
                raw = limits[bound] * (1 << catalog['stats'][stat_id]['shift'])
                if not raw:  # A zero roll is omitted from the native stat list.
                    continue
                assert int(raw) == raw
                stat = {'id': int(stat_id), 'layer': int(layer or 0), 'raw': int(raw)}
                signature = tuple(stat.values())
                if signature in checked:
                    continue
                rows, _, unresolved = decode_stats([stat], viewer_level=91)
                assert not unresolved, (item['name'], key, bound, stat)
                assert rows[0]['memory_stat'] == stat
                assert rows[0]['text']
                checked.add(signature)
    assert len(checked) >= 1800


def test_catalog_trigger_and_level_formula_payloads_decode():
    triggers, formulas = [], []
    for item in definitions():
        triggers.extend(item.get('fixed_triggers', []))
        for effect in item.get('fixed_per_level_effects', []):
            formulas.append((effect['stat_id'], effect['coefficient_raw'], effect['denominator']))
        for effect in item.get('variable_per_level_effects', []):
            for raw in range(effect['minimum_raw'], effect['maximum_raw'] + 1, effect['step_raw']):
                formulas.append((effect['stat_id'], raw, effect['denominator']))
    for effects in metadata()['crafting_triggers'].values():
        triggers.extend(effects)
    assert triggers
    assert formulas
    for effect in triggers:
        stat = {'id': effect['stat_id'], 'layer': effect['skill_id'] * 64 + effect['level'], 'raw': effect['chance']}
        rows, facets, unresolved = decode_stats([stat])
        assert not unresolved, effect
        assert not facets
        assert metadata()['skills'][str(effect['skill_id'])]['name'] in rows[0]['text']
    for stat_id, raw, denominator in formulas:
        stat = {'id': stat_id, 'layer': 0, 'raw': raw}
        for level in (1, 91, 99):
            rows, facets, unresolved = decode_stats([stat], viewer_level=level)
            assert not unresolved, (stat, level)
            assert not facets
            assert rows[0]['value'] == raw * level // denominator


def test_all_native_class_skills_and_skill_trees_decode():
    for skill_id, skill in metadata()['skills'].items():
        if not skill.get('class'):
            continue
        stat = {'id': 107, 'layer': int(skill_id), 'raw': 3}
        rows, _, unresolved = decode_stats([stat])
        assert not unresolved, skill
        assert skill['name'] in rows[0]['text']
    for class_id in range(8):
        assert not decode_stats([{'id': 83, 'layer': class_id, 'raw': 2}])[2]
        for tree in range(3):
            assert not decode_stats([{'id': 188, 'layer': class_id * 8 + tree, 'raw': 3}])[2]


def test_raw_set_bonus_elemental_level_formulas_decode():
    # Pinned d2data sets.json: Arctic FParam1=16, Vidala FParam1=12,
    # Heaven's Brethren PParam3b=24, Milabrega PParam2b=16.
    for stat_id, coefficient in ((226, 16), (226, 12), (227, 24), (228, 16)):
        stat = {'id': stat_id, 'layer': 0, 'raw': coefficient}
        for level in (1, 91, 99):
            rows, facets, unresolved = decode_stats([stat], viewer_level=level)
            assert not unresolved
            assert not facets
            assert rows[0]['value'] == coefficient * level // 8
            assert 'Maximum' in rows[0]['text']
