from pricing.knowledge.assessment.maintenance.guide_demand import summarize_demand


def use(build, variant='Standard', side='player', strength='preferred', **changes):
    return {
        'build': build,
        'variant': variant,
        'side': side,
        'strength': strength,
        'review_state': 'reviewed',
        'scope': 'softcore',
        **changes,
    }


def test_duplicate_variants_and_sides_add_context_not_build_votes():
    uses = [use('one'), use('one', 'Budget'), use('one', side='merc'), use('two', strength='alternative')]
    result = summarize_demand(uses, complete=False)
    assert result['distinct_builds'] == 2
    assert result['grade'] == 'Pending'
    assert result['lower_bound_grade'] == 'Med'
    assert result['preferred_builds'] == ['one']
    assert result['alternative_builds'] == ['two']
    assert result == summarize_demand(uses + uses, complete=False)


def test_unreviewed_shared_historical_and_discovery_uses_cannot_vote():
    uses = [
        use('one', review_state='pending'),
        use('shared-planner'),
        use('two', historical=True),
        use('three', strength='example'),
        use('four', scope='hardcore'),
    ]
    assert summarize_demand(uses, complete=False)['distinct_builds'] == 0
    assert summarize_demand([], complete=False)['grade'] == 'Pending'
    assert summarize_demand([], complete=True)['grade'] == 'No reviewed use'


def test_grade_boundaries_and_monotonic_breadth():
    assert [summarize_demand([use(str(i)) for i in range(n)], complete=True)['grade'] for n in (1, 2, 4, 5, 6)] == [
        'Low',
        'Med',
        'Med',
        'High',
        'High',
    ]


def test_changed_reviewed_profile_invalidates_demand_evidence():
    import pytest

    from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand

    profile = {
        'id': 'role',
        'names': ['Insight'],
        'build': 'one',
        'variant': 'Standard',
        'side': 'merc',
        'source': {'path': 'source', 'sha256': 'current'},
    }
    reviewed = {
        **use('one', side='merc'),
        'item': 'Insight',
        'profile_id': 'role',
        'source': {'path': 'source', 'sha256': 'old'},
    }
    with pytest.raises(ValueError, match='Stale'):
        compile_demand([reviewed], [profile])
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint

    reviewed['profile_fingerprint'] = fingerprint(profile)
    reviewed['source'] = profile['source']
    assert compile_demand([reviewed], [profile])['Insight']['distinct_builds'] == 1
    reviewed['presentation'] = {'progression': 'Endgame'}
    assert compile_demand([reviewed], [profile])['Insight']['role_presentation']['role'] == reviewed['presentation']
    reviewed['presentation'] = {'progression': 'Invented'}
    with pytest.raises(ValueError, match='progression'):
        compile_demand([reviewed], [profile])
    reviewed.pop('presentation')
    profile['must'] = {'op': 'changed'}
    with pytest.raises(ValueError, match='Stale'):
        compile_demand([reviewed], [profile])
