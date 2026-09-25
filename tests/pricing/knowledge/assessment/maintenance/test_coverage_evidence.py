import pytest

from pricing.knowledge.assessment.maintenance.coverage_matrix import build_matrix
from tests.pricing.knowledge.assessment.maintenance.test_coverage_matrix import inputs


@pytest.mark.parametrize('strength', ['reviewed_inference', 'explicit'])
def test_evidence_union_preserves_conditions_and_never_invents_identity_or_price(strength):
    data = inputs()
    recs = {
        'rows': [
            {
                'id': 'r',
                'item_id': 'd2data:uniqueitems:Unmentioned',
                'name': 'Unmentioned',
                'purpose': 'leveling',
                'conditions': ['Only with companion'],
                'source_date': '2025-04-24',
                'evidence_strength': strength,
                'review': 'Applicability reviewed',
            },
        ],
        'patterns': [{'name': 'early boots', 'status': 'conditional'}],
    }
    watch = {
        'rows': [
            {'name': 'Unmentioned', 'rarity': 'unique', 'details': {'local_conditions': 'Ethereal only'}},
            {'name': 'Missing item', 'rarity': 'set', 'details': {'guide_tier': 'high'}},
        ]
    }
    result = build_matrix(*data, recommendations=recs, valuable=watch)
    evidence = [r for r in result['rows'] if r['kind'] == 'evidence']
    assert len(evidence) == 4
    leveling = next(r for r in evidence if r['evidence_kind'] == 'leveling')
    assert leveling['identity_ids'] == ['identity:u']
    assert leveling['evidence']['conditions'] == ['Only with companion']
    assert leveling['evidence']['source_date'] == '2025-04-24'
    assert leveling['dimensions']['leveling']['state'] == 'reviewed'
    missing = next(r for r in evidence if r['name'] == 'Missing item')
    assert missing['identity_ids'] == []
    assert missing['dimensions']['discovery']['state'] == 'blocked'
    assert all(r['dimensions']['market']['state'] == 'pending' for r in evidence)
    assert all(r['dimensions']['named_tiers']['state'] == 'pending' for r in evidence)
    named = next(r for r in result['rows'] if r['id'] == 'identity:u')
    assert named['dimensions']['leveling']['state'] == 'pending'  # a conditional use is not exhaustive review
    assert len(named['evidence_ids']) == 2
    assert result['counts']['unlinked_evidence'] == 2


def test_ambiguous_names_do_not_merge_distinct_catalog_identities():
    data = inputs()
    data[0]['identities'].append(
        {'id': 'other', 'name': 'Unmentioned', 'category': 'unique', 'catalog_ids': ['unique2'], 'occurrence_ids': []}
    )
    watch = {'rows': [{'name': 'Unmentioned', 'rarity': 'unique'}]}
    result = build_matrix(*data, valuable=watch)
    evidence = next(r for r in result['rows'] if r['kind'] == 'evidence')
    assert evidence['identity_ids'] == []
    assert evidence['candidate_identity_ids'] == ['identity:other', 'identity:u']
    assert evidence['dimensions']['discovery']['state'] == 'blocked'
