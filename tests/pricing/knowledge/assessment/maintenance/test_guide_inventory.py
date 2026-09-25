from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import compile_inventory


def occurrence(identity='one', **changes):
    return {
        'id': identity,
        'name': 'Insight',
        'category': 'runeword',
        'build': 'build-a',
        'variant': 'Starter',
        'side': 'merc',
        'slot': 'Weapon',
        'source_id': 'guide.json',
        'source_locator': '/items/0',
        'details': {'recommended': True, 'resolution_status': 'resolved', 'companions': ['Cure']},
        **changes,
    }


def profile(identity='rule-a', **changes):
    return {
        'id': identity,
        'build': 'build-a',
        'variant': 'Starter',
        'side': 'merc',
        'slot': 'Weapon',
        'names': ['Insight'],
        'qualities': ['normal'],
        'must': {'op': 'fact_eq', 'field': 'sockets', 'value': 4},
        'source': {'path': 'guide.json', 'locator': '/items/0', 'sha256': 'source'},
        **changes,
    }


CATALOG = {
    'word': {'name': 'Insight', 'category': 'runeword'},
    'unused': {'name': 'Unused Unique', 'category': 'unique'},
}


def test_inventory_keeps_unmentioned_identities_and_original_evidence_without_demand_votes():
    rows = [
        occurrence(),
        occurrence('two', build='shared-planner', details={'recommended': False, 'resolution_status': 'resolved'}),
    ]
    saved = deepcopy(rows)
    result = compile_inventory(rows, [profile()], CATALOG)
    assert rows == saved
    assert result['counts']['occurrences'] == 2
    assert len(result['identities']) == 2
    entry = next(r for r in result['identities'] if r['name'] == 'Insight')
    assert len(entry['occurrence_ids']) == 2
    assert entry['review_state'] == 'pending'
    assert 'grade' not in entry
    original = next(r for r in result['occurrences'] if r['id'] == 'one')
    assert original['details']['companions'] == ['Cure']
    assert original['source_rule_ids'] == ['rule-a']
    assert not next(r for r in result['identities'] if r['name'] == 'Unused Unique')['occurrence_ids']


def test_semantic_configurations_reuse_provenance_but_not_different_requirements():
    first = profile()
    duplicate = profile(
        'rule-b', build='build-b', source={'path': 'other.json', 'locator': '/items/1', 'sha256': 'other'}
    )
    different = profile('rule-c', must={'op': 'fact_eq', 'field': 'sockets', 'value': 3})
    result = compile_inventory([occurrence()], [first, duplicate, different], CATALOG)
    assert sorted(len(r['profile_ids']) for r in result['configurations']) == [1, 2]
    assert result == compile_inventory([occurrence()], [different, duplicate, first], CATALOG)


def test_ambiguous_or_unresolved_names_do_not_merge_into_a_named_identity():
    catalog = {**CATALOG, 'other': {'name': 'Insight', 'category': 'unique'}}
    rows = [
        occurrence(category=None),
        occurrence('two', details={'recommended': True, 'resolution_status': 'unresolved'}),
    ]
    result = compile_inventory(rows, [], catalog)
    assert all(r['identity_status'] == 'unresolved' for r in result['occurrences'])
    assert all(not r['occurrence_ids'] for r in result['identities'] if r['category'] in ('unique', 'runeword'))
    with pytest.raises(ValueError, match='Duplicate source occurrence'):
        compile_inventory([rows[0], rows[0]], [], catalog)


def test_source_audit_detects_drift_and_never_verifies_a_missing_hash(tmp_path):
    import hashlib

    from pricing.knowledge.assessment.maintenance.guide_inventory import inspect_source

    path = tmp_path / 'source.json'
    path.write_bytes(b'original')
    source = {'path': 'source.json', 'sha256': hashlib.sha256(b'original').hexdigest()}
    assert inspect_source(tmp_path, source)['status'] == 'verified'
    path.write_bytes(b'changed')
    assert inspect_source(tmp_path, source)['status'] == 'changed_or_missing'
    assert inspect_source(tmp_path, {'path': 'missing.json', 'sha256': None})['status'] == 'changed_or_missing'


def test_canonical_planner_base_id_resolves_affixed_label_without_losing_quality():
    catalog = {'base-id': {'name': 'Orb', 'category': 'weapon', 'aliases': ['Old Orb']}}
    row = occurrence(
        name='Rare Orb',
        category='weapon',
        rarity='rare',
        details={
            'canonical_id': 'base-id',
            'quality': 4,
            'resolution_status': 'resolved',
            'recommended': False,
            'stats': {'skill': 2},
        },
    )
    result = compile_inventory([row], [], catalog)
    entry = result['occurrences'][0]
    assert entry['identity_status'] == 'resolved'
    assert entry['identity_basis'] == 'canonical_id'
    assert entry['rarity'] == 'rare'
    assert entry['name'] == 'Rare Orb'
    assert entry['details']['stats'] == {'skill': 2}
    assert result['identities'][0]['name'] == 'Orb'


@pytest.mark.parametrize(
    'changes',
    [
        {'category': 'unique'},
        {'name': 'Different Orb'},
        {'details': {'canonical_id': 'missing', 'resolution_status': 'resolved'}},
    ],
)
def test_conflicting_canonical_id_never_falls_back_to_matching_name(changes):
    row = occurrence(details={'canonical_id': 'word', 'resolution_status': 'resolved'})
    row.update(changes)
    result = compile_inventory([row], [], CATALOG)
    assert result['occurrences'][0]['identity_status'] == 'unresolved'
    assert result['occurrences'][0]['identity_basis'] == 'canonical_id_conflict'


def test_catalog_alias_requires_consistent_canonical_id_and_quality_prefix():
    catalog = {'base-id': {'name': 'Orb', 'category': 'weapon', 'aliases': ['Old Orb']}}
    row = occurrence(
        name='Magic Old Orb',
        category='weapon',
        details={'canonical_id': 'base-id', 'quality': 3, 'resolution_status': 'resolved'},
    )
    assert compile_inventory([row], [], catalog)['occurrences'][0]['identity_status'] == 'resolved'
    row['details']['quality'] = 4
    assert compile_inventory([row], [], catalog)['occurrences'][0]['identity_status'] == 'unresolved'
