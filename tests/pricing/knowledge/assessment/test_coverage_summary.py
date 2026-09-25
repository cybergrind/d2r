from pricing.knowledge.assessment.coverage import coverage


def test_named_tier_completeness_is_reported_separately_from_dispatch_and_profiles():
    result = coverage()
    named = result['named_tiers']
    assert named['identities'] >= named['reviewed_policies'] > 0
    assert named['pending'] == named['identities'] - named['reviewed_policies']
    assert named['invalid_sources'] == 0
    assert named['complete'] is (named['pending'] == 0)
    assert result['profile_count'] > 0
    assert result['price_policy_gaps']
