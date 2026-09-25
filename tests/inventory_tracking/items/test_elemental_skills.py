from inventory_tracking.items.metadata import decode_stats


def test_hellplague_fire_skills_and_unknown_element_stay_distinct():
    rows, _, unresolved = decode_stats([{'id': 126, 'layer': 1, 'raw': 2}])
    assert not unresolved
    assert rows[0]['text'] == '+2 to Fire Skills'
    for layer, raw in [(0, 2), (7, 2), (1, 0), (1, -1)]:
        _, _, unresolved = decode_stats([{'id': 126, 'layer': layer, 'raw': raw}])
        assert unresolved


def test_all_catalog_skills_and_masteries_decode_as_skill_bonuses():
    from inventory_tracking.items.metadata import metadata

    for skill_id, skill in metadata()['skills'].items():
        for stat_id in (97, 107, 151) if skill.get('class') else (97, 151):
            rows, _, unresolved = decode_stats([{'id': stat_id, 'layer': int(skill_id), 'raw': 2}])
            assert not unresolved, (stat_id, skill_id, skill)
            assert skill['name'] in rows[0]['text']


def test_all_classes_trees_elements_and_passive_mastery_stats():
    from inventory_tracking.items.stat_constants import CLASS_NAMES, SKILL_ELEMENTS, SKILL_TABS

    for class_id, class_name in enumerate(CLASS_NAMES):
        rows, _, unresolved = decode_stats([{'id': 83, 'layer': class_id, 'raw': 2}])
        assert not unresolved
        assert class_name in rows[0]['text']
        for tree, name in enumerate(SKILL_TABS[class_id]):
            rows, _, unresolved = decode_stats([{'id': 188, 'layer': class_id * 8 + tree, 'raw': 2}])
            assert not unresolved
            assert name in rows[0]['text']
    for layer, element in SKILL_ELEMENTS.items():
        rows, _, unresolved = decode_stats([{'id': 126, 'layer': layer, 'raw': 2}])
        assert not unresolved
        assert rows[0]['text'] == f'+2 to {element} Skills'
    for stat_id in (127, 329, 330, 331, 332, 357):
        _, _, unresolved = decode_stats([{'id': stat_id, 'layer': 0, 'raw': 2}])
        assert not unresolved, stat_id
