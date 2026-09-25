from pricing.knowledge.assessment.maintenance.embedded_items import resolve_embedded_item


def test_embedded_item_links_exact_set_occurrences_without_copying_rolls_as_requirements():
    planner = {
        'items': {'7': {'base': 'base', 'stats': {'damage': 99}}},
        'profiles': [{'uid': 'set-a', 'name': 'Budget'}, {'uid': 'set-b', 'name': 'Endgame'}],
    }
    rows = [
        {'id': 'correct', 'source_locator': '/profiles/0/items/rarm', 'details': {'item_ref': '7'}},
        {'id': 'other', 'source_locator': '/profiles/1/items/rarm', 'details': {'item_ref': '7'}},
    ]
    result = resolve_embedded_item({'set_id': 'set-a', 'item_id': '7'}, planner, rows)
    assert result['status'] == 'linked'
    assert result['occurrence_ids'] == ['correct']
    assert result['item_definition']['stats']['damage'] == 99
    assert result['review_state'] == 'pending'
    assert 'requirements' not in result


def test_missing_or_ambiguous_sets_never_fall_back_to_another_profile():
    reference = {'set_id': 'set-a', 'item_id': '7'}
    planner = {'items': {'7': {'base': 'base'}}, 'profiles': []}
    missing = resolve_embedded_item(reference, planner, [])
    assert missing['status'] == 'missing_set'
    assert missing['item_definition'] == {'base': 'base'}
    planner['profiles'] = [{'uid': 'set-a'}, {'uid': 'set-a'}]
    assert resolve_embedded_item(reference, planner, [])['status'] == 'ambiguous_set'
    planner['profiles'] = [{'uid': 'set-a'}]
    assert resolve_embedded_item(reference, planner, [])['status'] == 'definition_only'
    reference['item_id'] = '8'
    assert resolve_embedded_item(reference, planner, [])['status'] == 'missing_item'
