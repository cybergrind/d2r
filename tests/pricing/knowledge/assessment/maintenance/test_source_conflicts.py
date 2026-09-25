from pricing.knowledge.assessment.maintenance.source_conflicts import source_conflicts


def test_repeated_missing_set_references_share_blocker_without_losing_item_or_guide_context():
    rows = [
        {
            'source_id': 'guide',
            'planner_source_id': 'planner',
            'status': 'missing_set',
            'reference': {'set_id': 'missing', 'item_id': item, 'section_locator': '/sections/1'},
        }
        for item in ('1', '2')
    ]
    planners = {'planner': {'profiles': [{'uid': 'present', 'name': 'Standard'}]}}
    groups = source_conflicts(rows, planners)
    assert len(groups) == 1
    assert groups[0]['requested_set_id'] == 'missing'
    assert groups[0]['available_sets'] == [{'uid': 'present', 'name': 'Standard'}]
    assert [r['reference']['item_id'] for r in groups[0]['affected_references']] == ['1', '2']
    assert groups[0]['disposition'] == 'blocked_source'
    assert groups == source_conflicts(list(reversed(rows)), planners)


def test_missing_items_have_separate_blockers_and_definition_only_is_not_source_failure():
    rows = [
        {
            'source_id': 'guide',
            'planner_source_id': 'planner',
            'status': status,
            'reference': {'set_id': 'set', 'item_id': item},
        }
        for status, item in [('missing_item', '1'), ('missing_item', '2'), ('definition_only', '3')]
    ]
    assert len(source_conflicts(rows, {})) == 2
