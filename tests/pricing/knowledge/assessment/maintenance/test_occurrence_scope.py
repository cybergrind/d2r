from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.completion import compile_completion


def inventory():
    return {
        'identities': [{'id': 'item'}],
        'occurrences': [
            {
                'id': 'hc',
                'identity_id': 'item',
                'source_id': 'guide.json',
                'source_locator': '/variants/1/player/Helmet/0',
                'source_status': 'verified',
                'build': 'build',
                'variant': 'Hardcore',
            }
        ],
        'variant_contexts': [
            {
                'source_id': 'guide.json',
                'locator': '/variants/1',
                'build': 'build',
                'variant': 'Hardcore',
                'demand_eligibility': 'excluded_hardcore',
                'evidence': {'name': 'Hardcore'},
            }
        ],
    }


def test_explicit_hardcore_occurrence_is_closed_but_item_obligations_remain():
    doc = inventory()
    result = compile_completion({'rows': []}, doc, {'complete': True})
    assert 'occurrence:hc' not in {row['id'] for row in result['queue']}
    assert 'identity:item' in {row['id'] for row in result['queue']}
    assert result['counts']['excluded_occurrences'] == 1
    assert result['counts']['reviewed_occurrences'] == 0
    assert result['occurrence_dispositions'][0]['state'] == 'excluded'
    assert not result['complete']


@pytest.mark.parametrize(
    'patch',
    [
        {'source_id': 'other.json'},
        {'source_locator': '/variants/10/player/Helmet/0'},
        {'source_status': 'changed'},
        {'variant': 'Softcore'},
        {'build': 'other'},
    ],
)
def test_scope_exclusion_cannot_cross_source_variant_or_build(patch):
    doc = inventory()
    doc['occurrences'][0].update(patch)
    result = compile_completion({'rows': []}, doc, {'complete': True})
    assert 'occurrence:hc' in {row['id'] for row in result['queue']}


def test_scope_label_alone_or_duplicate_context_is_not_review_evidence():
    for change in ('label', 'duplicate'):
        doc = inventory()
        if change == 'label':
            doc['variant_contexts'][0]['evidence']['name'] = 'Standard with Hardcore alternatives'
        else:
            doc['variant_contexts'].append(deepcopy(doc['variant_contexts'][0]))
        result = compile_completion({'rows': []}, doc, {'complete': True})
        assert 'occurrence:hc' in {row['id'] for row in result['queue']}


def test_hardcore_planner_profile_exclusion_preserves_neighbouring_softcore_profile():
    doc = inventory()
    doc['variant_contexts'] = []
    doc['occurrences'][0].update(
        source_id='planner.json', source_locator='/profiles/2/items/head', build='shared-planner'
    )
    doc['occurrences'].append(
        {**doc['occurrences'][0], 'id': 'standard', 'variant': 'Standard', 'source_locator': '/profiles/3/items/head'}
    )
    doc['planner_slot_audits'] = [
        {
            'source_id': 'planner.json',
            'profiles': [
                {'locator': '/profiles/2', 'name': 'Hardcore'},
                {'locator': '/profiles/3', 'name': 'Standard'},
            ],
        }
    ]
    result = compile_completion({'rows': []}, doc, {'complete': True})
    assert 'occurrence:hc' not in {row['id'] for row in result['queue']}
    assert 'occurrence:standard' in {row['id'] for row in result['queue']}
    assert result['occurrence_dispositions'][0]['source']['locator'] == '/planner_slot_audits/0/profiles/0'
