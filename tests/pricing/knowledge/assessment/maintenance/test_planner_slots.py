from pricing.knowledge.assessment.maintenance.planner_slots import audit_planner_slots


def test_planner_audit_retains_empty_containers_and_detects_missing_socket_child():
    doc = {
        'items': {'1': {'base': 'test', 'socketedItems': ['rune']}},
        'profiles': [
            {'name': 'Main', 'merc': '11', 'items': {'weapon': '1', 'offhand': None}, 'inventory': [], 'mercItems': {}}
        ],
    }
    rows = [
        {
            'id': 'parent',
            'source_id': 'source',
            'source_locator': '/profiles/0/items/weapon',
            'details': {'item_ref': '1'},
        }
    ]
    result = audit_planner_slots(doc, 'source', rows)
    slots = {r['locator']: r for r in result['slots']}
    assert slots['/profiles/0/items/weapon']['status'] == 'represented'
    assert slots['/profiles/0/items/weapon/socketedItems/0']['status'] == 'missing_occurrence'
    assert slots['/profiles/0/items/offhand']['status'] == 'empty'
    assert result['profiles'][0]['mercenary_id'] == '11'
    containers = {r['locator']: r['status'] for r in result['containers']}
    assert containers['/profiles/0/inventory'] == 'empty'
    assert containers['/profiles/0/cube'] == 'absent'
    assert result['complete'] is False


def test_conflicting_reference_and_cycle_are_visible_without_recursion_failure():
    doc = {'items': {'1': {'socketedItems': ['1']}}, 'profiles': [{'items': ['1']}]}
    rows = [
        {'id': 'wrong', 'source_id': 'source', 'source_locator': '/profiles/0/items/0', 'details': {'item_ref': '2'}}
    ]
    result = audit_planner_slots(doc, 'source', rows)
    assert [r['status'] for r in result['slots']] == ['conflict', 'cyclic_reference']
    assert result['unaccounted_occurrence_ids'] == ['wrong']
