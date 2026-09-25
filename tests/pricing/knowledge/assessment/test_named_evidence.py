from pricing.knowledge.assessment.maintenance.coverage import audit_named


def test_named_coverage_links_build_and_leveling_evidence_without_inventing_tiers(tmp_path):
    definitions = {('set', 'Known'): {'base_codes': []}, ('unique', 'Other'): {'base_codes': []}}
    demand = [
        {
            'id': 'merc',
            'name': 'Known',
            'category': 'set',
            'build': 'build',
            'variant': 'Uber',
            'side': 'merc',
            'slot': 'Helmet',
            'source_id': 'guide',
            'source_locator': '/merc',
            'details': {'recommended': True, 'resolution_status': 'resolved'},
        },
        {'id': 'discovery', 'name': 'Known', 'category': 'set', 'details': {'recommended': False}},
        {'id': 'wrong-quality', 'name': 'Known', 'category': 'unique', 'details': {'recommended': True}},
    ]
    recommendations = [
        {
            'id': 'level',
            'item_id': 'set:1',
            'name': 'Known',
            'purpose': 'leveling',
            'source_id': 'transcript',
            'source_locator': '02:02',
        },
        {'id': 'unverified', 'item_id': 'missing', 'name': 'Other', 'purpose': 'leveling'},
    ]
    item_facts = [{'item_id': 'set:1', 'quality': 'set', 'name': 'Known'}]
    result = audit_named(
        definitions, {}, {}, tmp_path, demand=demand, recommendations=recommendations, item_facts=item_facts
    )
    rows = {r['name']: r for r in result['rows']}
    evidence = rows['Known']['evidence']
    assert evidence['recommended_build_occurrences'] == 1
    assert evidence['discovery_occurrences'] == 1
    assert evidence['build_roles'][0]['side'] == 'merc'
    assert evidence['build_roles'][0]['variant'] == 'Uber'
    assert evidence['leveling_recommendations'][0]['id'] == 'level'
    assert not rows['Other']['evidence']['leveling_recommendations']
    assert all(r['tier'] is None and r['status'] == 'missing_research' for r in result['rows'])
    assert result['evidence_counts']['unreviewed_with_build_or_leveling_evidence'] == 1
