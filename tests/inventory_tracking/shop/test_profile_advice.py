"""Profile advice stays distinct from unresolved shop setup requirements."""

from inventory_tracking.shop.build_catalog import profile_target


def test_shop_profile_can_have_advice_without_missing_conditions():
    profile = {
        'id': 'skiller',
        'types': ['lcha'],
        'build': 'example',
        'variant': 'Main',
        'role': 'skiller',
        'must': {'op': 'stat_at_least', 'key': '188:9', 'value': 1},
        'source': {'path': 'guide'},
        'advisory_conditions': ['Keep in inventory.'],
    }
    target = profile_target(profile)
    assert target['conditions'] == []
    assert target['advisory_conditions'] == ['Keep in inventory.']
    assert target['must'] == profile['must']
    profile['conditions'] = ['Verify companion.']
    assert profile_target(profile)['conditions'] == ['Verify companion.']
