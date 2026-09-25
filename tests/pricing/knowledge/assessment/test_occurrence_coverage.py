from pricing.knowledge.assessment.maintenance.inventory import audit_occurrences


def occurrence(key, **changes):
    return {
        'id': key,
        'name': 'Component',
        'build': 'build',
        'variant': 'Standard',
        'side': 'player',
        'slot': 'Helmet',
        'source_id': 'source.json',
        'source_locator': '/variants/0/player/Helmet/0',
        'details': {'recommended': True, 'resolution_status': 'resolved'},
        **changes,
    }


def test_audit_keeps_each_source_occurrence_and_does_not_equate_related_rule_to_coverage():
    profile = {
        'id': 'rule',
        'build': 'build',
        'variant': 'Standard',
        'side': 'player',
        'slot': 'Helmet',
        'names': ['Component'],
        'source': {'path': 'source.json', 'locator': '/variants/0'},
    }
    rows = [
        occurrence('main'),
        occurrence('merc', side='merc'),
        occurrence('swap', slot='Weapon-Swap'),
        occurrence('other', variant='Budget'),
        occurrence('duplicate-identity', source_id='another.json'),
    ]
    result = audit_occurrences(rows, [profile])
    assert result['counts']['occurrences'] == 5
    by_id = {r['id']: r for r in result['rows']}
    assert by_id['main']['source_rule_ids'] == ['rule']
    assert by_id['duplicate-identity']['related_rule_ids'] == ['rule']
    assert by_id['duplicate-identity']['source_rule_ids'] == []
    for key in ('merc', 'swap', 'other'):
        assert by_id[key]['related_rule_ids'] == []
    assert result['complete'] is False
    assert audit_occurrences(reversed(rows), [profile]) == result


def test_discovery_and_unresolved_rows_are_retained_without_becoming_executed_rules():
    rows = [
        occurrence('discovery', details={'recommended': False, 'resolution_status': 'resolved'}),
        occurrence('unknown', details={'recommended': True, 'resolution_status': 'pattern_or_unresolved'}),
        occurrence('pending', details={}),
    ]
    result = audit_occurrences(rows, [])
    assert {r['id']: r['status'] for r in result['rows']} == {
        'discovery': 'discovery_only',
        'unknown': 'identity_review',
        'pending': 'endorsement_review',
    }


def test_standalone_variants_preserve_swaps_mercenary_and_literal_source_paths():
    from pricing.knowledge.assessment.maintenance.inventory import variant_occurrences

    document = {
        'slug': 'build',
        'variants': [
            {
                'name': 'Budget',
                'player': {'Weapon-Swap': ['Named item'], 'Prebuff/Other': ['Unresolved skill text']},
                'merc': {'type': 'Act 2', 'Weapon': ['Named item']},
            }
        ],
    }
    catalog = {'named': {'name': 'Named item', 'category': 'unique'}}
    rows = variant_occurrences(document, 'variant.json', catalog)
    assert len(rows) == 3
    assert len({r['id'] for r in rows}) == 3
    assert rows[0]['slot'] == 'Weapon-Swap'
    assert rows[1]['source_locator'] == '/variants/0/player/Prebuff~1Other/0'
    assert rows[1]['details']['resolution_status'] == 'pattern_or_unresolved'
    assert rows[2]['side'] == 'merc'
