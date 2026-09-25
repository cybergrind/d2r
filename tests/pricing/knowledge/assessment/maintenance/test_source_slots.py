from pricing.knowledge.assessment.maintenance.source_slots import audit_variant_slots


def test_empty_context_and_missing_labels_are_accounted_for_without_inheritance():
    document = {
        'slug': 'build',
        'variants': [
            {
                'name': 'Budget',
                'delta_only': True,
                'player': {'Weapon': ['Insight', 'Spirit'], 'Off-Hand': []},
                'merc': {'type': 'Act 2 Prayer', 'Weapon': ['Insight']},
            }
        ],
    }
    rows = [
        {
            'id': 'one',
            'source_id': 'source',
            'source_locator': '/variants/0/player/Weapon/0',
            'original_label': 'Insight',
        }
    ]
    audit = audit_variant_slots(document, 'source', rows)
    slots = {r['locator']: r for r in audit['slots']}
    weapon = slots['/variants/0/player/Weapon']
    assert weapon['status'] == 'missing_occurrences'
    assert weapon['occurrence_ids'] == ['one']
    assert weapon['missing_locators'] == ['/variants/0/player/Weapon/1']
    assert weapon['variant_context']['delta_only'] is True
    assert slots['/variants/0/player/Off-Hand']['status'] == 'empty'
    assert slots['/variants/0/merc/type']['status'] == 'context'
    assert slots['/variants/0/merc/type']['value'] == 'Act 2 Prayer'
    assert audit['complete'] is False


def test_locator_match_requires_matching_label_and_preserves_escaped_slot():
    document = {'slug': 'build', 'variants': [{'name': 'Main', 'player': {'Swap/Utility': ['Spirit']}}]}
    row = {
        'id': 'wrong',
        'source_id': 'source',
        'source_locator': '/variants/0/player/Swap~1Utility/0',
        'original_label': 'Insight',
    }
    audit = audit_variant_slots(document, 'source', [row])
    slot = audit['slots'][0]
    assert slot['status'] == 'conflict'
    assert slot['conflicting_occurrence_ids'] == ['wrong']
    assert audit['sides'][1]['status'] == 'absent'
    row['original_label'] = 'Spirit'
    audit = audit_variant_slots(document, 'source', [row])
    assert audit['slots'][0]['status'] == 'represented'
    assert audit['complete'] is False  # absent side is not an audited inheritance decision


def test_consolidated_tables_keep_stage_context_and_legacy_locators():
    from pricing.knowledge.assessment.maintenance.source_slots import audit_build_slots

    documents = {
        'build': {
            'slots': {'Swap/Utility': ['Spirit']},
            'merc': {'Weapon': {'early': ['Insight'], 'end': []}},
            'prose_only_items': ['Teleport staff'],
            'variants': [{'name': 'Main', 'player': {}, 'merc': {'type': 'Act 2 Prayer'}}],
        }
    }
    rows = [
        {
            'id': 'swap',
            'source_id': 'source',
            'source_locator': '/build/slots/Swap/Utility/0',
            'original_label': 'Spirit',
        }
    ]
    audit = audit_build_slots(documents, 'source', rows)
    slots = {r['locator']: r for r in audit['slots']}
    assert slots['/build/slots/Swap/Utility']['occurrence_ids'] == ['swap']
    assert slots['/build/merc/Weapon/early']['variant'] == 'early'
    assert slots['/build/merc/Weapon/early']['status'] == 'missing_occurrences'
    assert slots['/build/merc/Weapon/end']['status'] == 'empty'
    assert slots['/build/prose_only_items']['value'] == ['Teleport staff']
    assert slots['/build/variants/0/merc/type']['status'] == 'context'
    assert audit['complete'] is False


def test_prose_mercenary_metadata_is_context_but_unknown_shapes_need_review():
    from pricing.knowledge.assessment.maintenance.source_slots import audit_build_slots

    audit = audit_build_slots(
        {'build': {'merc': {'_text_only': True, '_source': 'guide prose', 'Unexpected': 42}}}, 'source', []
    )
    slots = {r['slot']: r for r in audit['slots']}
    assert slots['_text_only']['status'] == 'context'
    assert slots['_source']['status'] == 'context'
    assert slots['Unexpected']['status'] == 'unsupported_shape'
