from pricing.knowledge.assessment.maintenance.base_matrix import audit_bases


def test_base_membership_uses_runtime_selectors_and_prunes_only_proven_false_guards():
    bases = {'a': {'name': 'A', 'type': 'sword', 'gemsockets': 0}, 'b': {'name': 'B', 'type': 'sword', 'gemsockets': 0}}
    types = {'sword': {'Equiv1': 'weapon'}}
    profiles = [
        {'id': 'ancestor', 'types': ['weapon'], 'qualities': ['normal']},
        {
            'id': 'only-a',
            'types': ['sword'],
            'qualities': ['normal'],
            'must': {
                'all': [
                    {'op': 'fact_eq', 'field': 'base_code', 'value': 'a'},
                    {'op': 'fact_eq', 'field': 'ethereal', 'value': True},
                ]
            },
        },
        {
            'id': 'rolled',
            'types': ['sword'],
            'qualities': ['normal'],
            'must': {'op': 'stat_at_least', 'key': '17:0', 'value': 10, 'absent_is_zero': True},
        },
    ]
    result = audit_bases(bases, types, [], profiles, {})
    a = next(r for r in result['rows'] if r['id'] == 'a:normal')
    b = next(r for r in result['rows'] if r['id'] == 'b:normal')
    assert a['candidate_profile_ids'] == ['only-a', 'rolled']
    assert b['candidate_profile_ids'] == ['rolled']
    assert {r['profile_id']: r['guard_truth'] for r in b['policy_assignments']} == {
        'only-a': 'false',
        'rolled': 'unknown',
    }
    assert all(r['profile_fingerprint'] for r in a['policy_assignments'])
    assert a['dimensions']['policy_routing']['state'] == 'reviewed'
    assert a['dimensions']['desirability']['state'] == 'pending'
    assert a['dimensions']['market']['state'] == 'pending'
    assert not next(r for r in result['rows'] if r['id'] == 'a:superior')['candidate_profile_ids']
