from pricing.knowledge.assessment.maintenance.base_matrix import audit_bases


def test_all_bases_remain_in_scope_and_links_do_not_prove_desirability_or_price():
    bases = {
        'example': {'name': 'Example Sword', 'type': 'sword', 'gemsockets': 4},
        'unused': {'name': 'Unmentioned Sword', 'type': 'sword', 'gemsockets': 0},
    }
    types = {'sword': {'MaxSockets1': 3, 'MaxSockets2': 4, 'MaxSockets3': 4}}
    edge = {
        'base_code': 'example',
        'source_locator': 'recipe/example',
        'details': {
            'legality': 'verified_type_and_capacity',
            'runeword': 'Example Word',
            'socket_options': {'maximum_by_ilvl_bracket': [3, 4, 4]},
        },
    }
    profiles = [
        {
            'id': 'candidate',
            'types': ['sword'],
            'qualities': ['normal'],
            'must': {'op': 'stat_at_least', 'key': '17:0', 'value': 10},
            'source': {'path': 'guide'},
        }
    ]
    market = {'bases': [{'code': 'example', 'scoped_base_observations': 100}]}
    result = audit_bases(bases, types, [edge, edge], profiles, market)
    assert len(result['rows']) == 6
    assert result['complete'] is False
    normal = next(r for r in result['rows'] if r['id'] == 'example:normal')
    assert len(normal['recipe_links']) == 1
    assert normal['candidate_profile_ids'] == ['candidate']
    assert normal['dimensions']['desirability']['state'] == 'pending'
    assert normal['dimensions']['market']['state'] == 'pending'
    assert normal['base_market_evidence']['scoped_base_observations'] == 100
    assert all(r['dimensions']['named_tiers']['state'] == 'excluded' for r in result['rows'])
    assert all(not r['recipe_links'] for r in result['rows'] if r['base_code'] == 'unused')
    superior = next(r for r in result['rows'] if r['id'] == 'example:superior')
    assert superior['candidate_profile_ids'] == []
    assert result == audit_bases(bases, types, [edge], profiles, market)


def test_socket_evidence_conflict_and_missing_native_limits_are_visible():
    bases = {'example': {'name': 'Example', 'type': 'sword', 'gemsockets': 4}}
    types = {'sword': {'MaxSockets1': 3, 'MaxSockets2': 4, 'MaxSockets3': 4}}
    edge = {
        'base_code': 'example',
        'source_locator': 'recipe/example',
        'details': {
            'legality': 'verified_type_and_capacity',
            'runeword': 'Example Word',
            'socket_options': {'maximum_by_ilvl_bracket': [4, 4, 4]},
        },
    }
    result = audit_bases(bases, types, [edge], [], {})
    assert all(r['dimensions']['socket_mechanics']['state'] == 'blocked' for r in result['rows'])
    result = audit_bases(bases, {}, [], [], {})
    assert all(r['dimensions']['socket_mechanics']['state'] == 'blocked' for r in result['rows'])


def test_native_membership_is_separate_from_mode_preparation_and_desirability():
    bases = {
        'base': {'name': 'Base', 'type': 'weapon', 'gemsockets': 2},
        'no-sockets': {'name': 'No sockets', 'type': 'weapon', 'gemsockets': 0},
    }
    types = {'weapon': {'MaxSockets1': 2, 'MaxSockets2': 2, 'MaxSockets3': 2}}
    recipes = {'Word': {'complete': 1, 'itype1': 'weapon', 'Rune1': 'first', 'Rune2': 'second'}}
    edges = [
        {
            'base_code': 'base',
            'sockets': 2,
            'details': {
                'legality': 'verified_type_and_capacity',
                'runeword': 'Word',
                'recipe_id': 'Word',
                'rune_codes': ['first', 'second'],
                'socket_options': {'maximum_by_ilvl_bracket': [2, 2, 2]},
            },
        }
    ]
    result = audit_bases(bases, types, edges, [], {}, recipes=recipes)
    assert result['counts']['dimensions']['type_capacity_eligibility'] == {'excluded': 3, 'reviewed': 3}
    for row in result['rows']:
        assert row['dimensions']['recipe_eligibility']['state'] == 'pending'
        assert row['dimensions']['desirability']['state'] == 'pending'
        assert row['dimensions']['market']['state'] == 'pending'
