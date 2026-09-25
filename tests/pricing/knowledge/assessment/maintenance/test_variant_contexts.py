from pricing.knowledge.assessment.maintenance.variant_contexts import variant_contexts


def test_hardcore_variants_retained_but_excluded_from_softcore_votes():
    doc = {
        'slug': 'build',
        'variants': [
            {'name': 'Hardcore (prose)', 'delta_only': True, 'purpose': 'Gear changes', 'player': {}},
            {'name': 'Standard', 'purpose': 'Also usable in Hardcore', 'player': {'Weapon': ['Insight']}},
        ],
    }
    rows = variant_contexts(doc, 'source')
    assert rows[0]['demand_eligibility'] == 'excluded_hardcore'
    assert rows[0]['inheritance_status'] == 'unresolved_delta'
    assert rows[0]['parent_variant'] is None
    assert rows[1]['demand_eligibility'] == 'requires_review'
    assert rows[1]['inheritance_status'] == 'not_declared'
    assert rows[0]['locator'] == '/variants/0'


def test_planner_only_context_is_not_guide_endorsement_and_flags_are_preserved():
    doc = {
        'slug': 'build',
        'variants': [
            {
                'name': 'Budget',
                'planner_only': True,
                'delta_only': False,
                'planner_profile': 'profile',
                'notes': 'example',
            }
        ],
    }
    row = variant_contexts(doc, 'source')[0]
    assert row['demand_eligibility'] == 'planner_endorsement_review'
    assert row['evidence']['planner_profile'] == 'profile'
    assert row['evidence']['notes'] == 'example'
    assert row['parent_variant'] is None
