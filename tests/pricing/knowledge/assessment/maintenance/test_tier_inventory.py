import pytest

from pricing.knowledge.assessment.maintenance.tier_inventory import compile_tier_inventory


def test_inventory_keeps_every_identity_and_separates_historical_grade_from_current_policy():
    census = [
        {'quality': 'set', 'name': 'Same', 'status': 'reviewed_policy', 'tier': 'low'},
        {'quality': 'unique', 'name': 'Same', 'status': 'missing_research', 'tier': None},
        {'quality': 'unique', 'name': 'Unmentioned', 'status': 'missing_research', 'tier': None},
    ]
    watch = [
        {'name': 'Same', 'rarity': 'unique', 'details': {'guide_tier': 'High', 'guide_conditions': 'perfect only'}}
    ]
    facts = [{'name': 'Same', 'quality': 'set', 'item_id': 'set:1', 'set_name': 'Family'}]
    recommendations = [{'id': 'r1', 'name': 'Same', 'item_id': 'set:1', 'classes': ['amazon']}]
    result = compile_tier_inventory(census, watch, recommendations, facts)
    assert len(result['rows']) == 3
    indexed = {(r['quality'], r['name']): r for r in result['rows']}
    assert indexed['set', 'Same']['tier'] == 'low'
    assert indexed['set', 'Same']['leveling_recommendations'] == ['r1']
    assert indexed['set', 'Same']['set_name'] == 'Family'
    assert indexed['unique', 'Same']['tier'] is None
    assert indexed['unique', 'Same']['historical_guide_tier'] == 'High'
    assert indexed['unique', 'Same']['leveling_recommendations'] == []
    assert indexed['unique', 'Unmentioned']['tier'] is None
    assert result['complete'] is False
    assert result['counts']['identities'] == 3
    assert result['counts']['pending'] == 2


def test_inventory_rejects_duplicate_catalog_identity_instead_of_hiding_it():
    row = {'quality': 'unique', 'name': 'One', 'status': 'missing_research', 'tier': None}
    with pytest.raises(ValueError, match='Duplicate'):
        compile_tier_inventory([row, row], [], [], [])


def test_explicit_dispositions_do_not_turn_quest_or_placeholder_records_into_trash():
    census = [{'quality': 'unique', 'name': 'Quest', 'status': 'missing_research', 'tier': None}]
    disposition = {'quality': 'unique', 'name': 'Quest', 'kind': 'quest_item', 'reason': 'Quest progression item'}
    result = compile_tier_inventory(census, [], [], [], dispositions=[disposition])
    assert result['complete'] is True
    assert result['counts']['reviewed'] == 0
    assert result['counts']['dispositions'] == 1
    assert result['counts']['pending'] == 0
    assert result['rows'][0]['tier'] is None
    assert result['rows'][0]['disposition']['kind'] == 'quest_item'
    with pytest.raises(ValueError, match='Unknown'):
        compile_tier_inventory([], [], [], [], dispositions=[disposition])
