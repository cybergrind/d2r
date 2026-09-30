from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.completion import compile_completion
from pricing.knowledge.assessment.maintenance.coverage_matrix import DIMENSIONS


def inputs():
    matrix = {
        'rows': [
            {
                'id': 'identity:a',
                'dimensions': {
                    key: {
                        'state': 'reviewed',
                        'reason': 'Verified',
                        'sources': [{'artifact': 'inventory', 'locator': '/identities/0'}],
                    }
                    for key in DIMENSIONS
                },
            }
        ]
    }
    inventory = {
        'identities': [{'id': 'a'}],
        'occurrences': [{'id': 'o', 'identity_id': 'a', 'review_state': 'discovery_only'}],
        'source_conflicts': [],
        'planner_source_gaps': [],
    }
    return matrix, inventory


def test_reviewed_dimensions_do_not_hide_unreviewed_occurrences_or_delivery():
    matrix, inventory = inputs()
    result = compile_completion(matrix, inventory, {'complete': True})
    assert not result['complete']
    assert any(row['id'] == 'occurrence:o' for row in result['queue'])
    assert any(row['id'] == 'final:verification' for row in result['queue'])


@pytest.mark.parametrize('dimension', DIMENSIONS)
def test_missing_dimension_is_work_not_implicit_completion(dimension):
    matrix, inventory = inputs()
    del matrix['rows'][0]['dimensions'][dimension]
    result = compile_completion(matrix, inventory, {'complete': True})
    assert any(row['id'] == f'identity:a/{dimension}' for row in result['queue'])


def test_removed_identity_and_source_conflicts_remain_blockers():
    matrix, inventory = inputs()
    matrix['rows'].clear()
    inventory['source_conflicts'] = [{'id': 'conflict'}]
    result = compile_completion(matrix, inventory, {'complete': True})
    assert {'identity:a', 'source_conflict:0'} <= {r['id'] for r in result['queue']}


def test_planner_notes_and_nested_equipment_remain_completion_work():
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint

    matrix, inventory = inputs()
    audit = {
        'schema_version': 1,
        'inventory_fingerprint': fingerprint(inventory),
        'source_hashes': {},
        'planner_reports': {'planner.json': {'issues': [{'kind': 'notes_require_review'}]}},
        'source_issues': [],
        'guide_issues': [],
        'unsupported_sources': [],
        'missing_planners': [],
    }
    result = compile_completion(matrix, inventory, {'complete': True}, planner_audit=audit)
    assert any(row['id'] == 'planner_audit:planner.json:0' for row in result['queue'])
    inventory['changed'] = True
    with pytest.raises(ValueError, match='Stale planner reachability'):
        compile_completion(matrix, inventory, {'complete': True}, planner_audit=audit)


def test_real_planner_sources_require_reachability_audit():
    matrix, inventory = inputs()
    inventory['sources'] = [{'path': 'pricing/raw/mr/planners/example.json'}]
    result = compile_completion(matrix, inventory, {'complete': True})
    assert any(row['id'] == 'planner_audit:missing' for row in result['queue'])


def test_audit_cannot_omit_a_scoped_planner():
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint

    matrix, inventory = inputs()
    inventory['sources'] = [{'path': 'pricing/raw/mr/planners/example.json'}]
    audit = {
        'schema_version': 1,
        'inventory_fingerprint': fingerprint(inventory),
        'source_hashes': {},
        'planner_reports': {},
        'source_issues': [],
        'guide_issues': [],
        'unsupported_sources': [],
        'missing_planners': [],
    }
    result = compile_completion(matrix, inventory, {'complete': True}, planner_audit=audit)
    assert any(row['id'] == 'planner_audit:omitted:pricing/raw/mr/planners/example.json' for row in result['queue'])


def test_reviews_without_evidence_and_unknown_states_fail_closed():
    matrix, inventory = inputs()
    for value in matrix['rows'][0]['dimensions'].values():
        value['sources'] = []
    result = compile_completion(matrix, inventory, {'complete': True})
    assert len([r for r in result['queue'] if r['id'].startswith('identity:a/')]) == len(DIMENSIONS)
    broken = deepcopy(matrix)
    broken['rows'][0]['dimensions']['market']['state'] = 'priced-ish'
    with pytest.raises(ValueError, match='state'):
        compile_completion(broken, inventory, {'complete': True})


def test_empty_or_duplicate_scope_cannot_pass():
    matrix, inventory = inputs()
    with pytest.raises(ValueError, match='Empty scope'):
        compile_completion({'rows': []}, {'identities': [], 'occurrences': []}, {'complete': True})
    matrix['rows'].append(deepcopy(matrix['rows'][0]))
    with pytest.raises(ValueError, match='Duplicate'):
        compile_completion(matrix, inventory, {'complete': True})


def test_exact_pattern_review_closes_only_its_occurrence():
    from pricing.knowledge.assessment.maintenance.guide_inventory import compile_inventory
    from tests.pricing.knowledge.assessment.maintenance.test_inline_source_links import inline_review
    from tests.pricing.knowledge.assessment.maintenance.test_review_dossiers import reviewed

    role, occurrence = inline_review()
    neighbour = {**occurrence, 'id': 'neighbour', 'source_locator': '/item-spans/163'}
    inventory = compile_inventory([occurrence, neighbour], [role], {})
    use = reviewed(role, pattern=role['id'], pattern_label='Rare Ring')
    del use['item']
    matrix = {'rows': []}
    result = compile_completion(matrix, inventory, {'complete': True}, profiles=[role], uses=[use])
    ids = {row['id'] for row in result['queue']}
    assert 'occurrence:' + occurrence['id'] not in ids
    assert 'occurrence:neighbour' in ids
    assert result['counts']['reviewed_occurrences'] == 1
    assert not result['complete']


@pytest.mark.parametrize(
    ('category', 'quality'),
    [
        ('unique', 'unique'),
        ('set', 'set'),
        ('runeword', 'normal'),
        ('runeword', 'superior'),
        ('runeword', 'low_quality'),
    ],
)
def test_exact_named_review_does_not_close_other_variant_or_socket_component(category, quality):
    from pricing.knowledge.assessment.maintenance.guide_inventory import compile_inventory
    from tests.pricing.knowledge.assessment.maintenance.test_inline_source_links import inline_review
    from tests.pricing.knowledge.assessment.maintenance.test_review_dossiers import reviewed

    role, occurrence = inline_review()
    role.update(names=['Test Unique'], qualities=[quality])
    if category == 'runeword':
        role['must'] = {'op': 'fact_eq', 'field': 'runeword', 'value': 'Test Unique'}
    occurrence.update(
        name='Test Unique',
        original_label='Test Unique',
        category=category,
        details={'recommended': True, 'resolution_status': 'resolved'},
    )
    other = {**occurrence, 'id': 'other', 'variant': 'Different setup'}
    catalog = {'unique1': {'category': category, 'name': 'Test Unique'}}
    inventory = compile_inventory([occurrence, other], [role], catalog)
    use = reviewed(role, item='Test Unique')
    result = compile_completion({'rows': []}, inventory, {'complete': True}, profiles=[role], uses=[use])
    ids = {row['id'] for row in result['queue']}
    assert 'occurrence:' + occurrence['id'] not in ids
    assert 'occurrence:other' in ids


def test_completion_rejects_stale_artifact_inputs(tmp_path):
    import hashlib

    from pricing.knowledge.assessment.maintenance.completion import verify_artifact_inputs

    source = tmp_path / 'source.json'
    source.write_text('original')
    pinned = hashlib.sha256(source.read_bytes()).hexdigest()
    docs = {'matrix': {'sources': {'profiles': {'path': 'source.json', 'sha256': pinned}}}}
    verify_artifact_inputs(docs, tmp_path)
    source.write_text('changed')
    with pytest.raises(ValueError, match='Stale'):
        verify_artifact_inputs(docs, tmp_path)


def test_final_checks_must_match_scope_and_selected_generation():
    from pricing.knowledge.assessment.maintenance.completion import scope_fingerprint

    matrix, inventory = inputs()
    inventory['occurrences'] = []
    gate = {'complete': True}
    bank = {'case_coverage_complete': True, 'missing': {}, 'orphaned_case_targets': []}
    scope = scope_fingerprint(matrix, inventory, gate, None, (), bank_coverage=bank)
    checks = {
        key: {
            'status': 'passed',
            'scope': scope,
            'generation': 'generation-a',
            'evidence': [{'path': 'verified.json', 'sha256': 'pinned'}],
        }
        for key in ('verification', 'delivery', 'item_bank')
    }
    result = compile_completion(
        matrix, inventory, gate, bank_coverage=bank, final_checks=checks, generation='generation-a'
    )
    assert result['complete']
    assert result['queue'] == []
    assert not compile_completion(
        matrix, inventory, gate, bank_coverage=bank, final_checks=checks, generation='generation-b'
    )['complete']
    matrix['rows'][0]['dimensions']['market']['reason'] = 'Changed assessment'
    assert not compile_completion(
        matrix, inventory, gate, bank_coverage=bank, final_checks=checks, generation='generation-a'
    )['complete']


def test_removed_base_quality_or_role_quality_row_cannot_disappear_from_scope():
    from pricing.knowledge.assessment.maintenance.guide_inventory import configurations
    from tests.pricing.knowledge.assessment.maintenance.test_guide_inventory import profile

    matrix, inventory = inputs()
    inventory['occurrences'] = []
    role = profile()
    inventory['configurations'] = configurations([role])
    inventory['identities'][0].update(name='Test', category='unique', catalog_ids=['unique1'], occurrence_ids=[])
    bases = {'rows': [{'id': 'base-normal'}]}
    result = compile_completion(matrix, inventory, {'complete': True}, profiles=[role], bases=bases)
    ids = {row['id'] for row in result['queue']}
    assert 'base:base-normal' in ids
    assert {f'use:{role["id"]}:{quality}' for quality in role['qualities']} <= ids


def test_item_bank_inventory_is_required_for_final_completion():
    matrix, inventory = inputs()
    result = compile_completion(matrix, inventory, {'complete': True})
    assert 'final:item_bank' in {row['id'] for row in result['queue']}


@pytest.mark.parametrize(
    'source',
    [
        {'artifact': 'missing', 'locator': '/identities/0'},
        {'artifact': 'inventory', 'locator': '/identities/99'},
        {'artifact': 'inventory', 'locator': '/identities/-1'},
        {'artifact': 'inventory'},
    ],
)
def test_reviewed_dimension_requires_resolvable_source_reference(source):
    matrix, inventory = inputs()
    matrix['rows'][0]['dimensions']['market']['sources'] = [source]
    result = compile_completion(matrix, inventory, {'complete': True})
    assert any(row['id'] == 'identity:a/market' and row['state'] == 'blocked' for row in result['queue'])


def test_completion_policy_change_invalidates_scope_attestation(monkeypatch):
    from pricing.knowledge.assessment.maintenance import completion

    matrix, inventory = inputs()
    old = completion.scope_fingerprint(matrix, inventory, {}, None, ())
    monkeypatch.setattr(completion, 'policy_fingerprint', lambda: 'changed-review-policy', raising=False)
    assert completion.scope_fingerprint(matrix, inventory, {}, None, ()) != old


@pytest.mark.parametrize(
    ('predicate', 'quality', 'expected'),
    [
        ({}, 'normal', False),
        ({'op': 'fact_eq', 'field': 'runeword', 'value': None}, 'normal', False),
        ({'op': 'fact_eq', 'field': 'runeword', 'value': 'Other'}, 'normal', False),
        ({'op': 'fact_eq', 'field': 'runeword', 'value': 'Word'}, 'unique', False),
        (
            {
                'any': [
                    {'op': 'fact_eq', 'field': 'runeword', 'value': 'Word'},
                    {'op': 'fact_eq', 'field': 'sockets', 'value': 3},
                ]
            },
            'normal',
            False,
        ),
        (
            {
                'all': [
                    {'op': 'fact_eq', 'field': 'runeword', 'value': 'Word'},
                    {'op': 'fact_eq', 'field': 'sockets', 'value': 3},
                ]
            },
            'normal',
            True,
        ),
    ],
)
def test_completed_word_review_requires_recipe_identity_on_every_successful_path(predicate, quality, expected):
    from pricing.knowledge.assessment.maintenance.completion import _occurrence_quality_matches

    assert (
        _occurrence_quality_matches(
            {'category': 'runeword', 'name': 'Word'}, {'qualities': [quality], 'must': predicate}
        )
        is expected
    )


@pytest.mark.parametrize('status', ['linked', 'definition_only'])
@pytest.mark.parametrize('claimed_state', ['pending', 'reviewed'])
def test_embedded_guide_use_requires_semantic_review_even_when_item_is_resolved(status, claimed_state):
    matrix, inventory = inputs()
    inventory['embedded_item_links'] = [
        {
            'source_id': 'guide.html',
            'planner_source_id': 'planner.json',
            'reference': {
                'profile_id': 'p',
                'set_id': 's',
                'item_id': '143',
                'position': [3, 7],
                'section_locator': '/sections/1',
            },
            'status': status,
            'review_state': claimed_state,
            'occurrence_ids': ['o'] if status == 'linked' else [],
        }
    ]
    result = compile_completion(matrix, inventory, {'complete': True})
    rows = [r for r in result['queue'] if r['id'].startswith('embedded_reference:')]
    assert len(rows) == 1
    assert rows[0]['dimension'] == 'source_review'
    assert rows[0]['state'] == 'pending'
    assert not result['complete']


@pytest.mark.parametrize(
    'module',
    [
        'planner_endorsement.py',
        'planner_runeword_endorsement.py',
        'planner_tab_endorsement.py',
        'planner_set_endorsement.py',
        'planner_jewel_endorsement.py',
        'planner_socket_endorsement.py',
    ],
)
def test_planner_validation_changes_invalidate_completion_policy(monkeypatch, module):
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.completion import policy_fingerprint

    before = policy_fingerprint()
    original = Path.read_bytes

    def changed(path):
        raw = original(path)
        return raw + b'\n# changed validation policy\n' if path.name == module else raw

    monkeypatch.setattr(Path, 'read_bytes', changed)
    assert policy_fingerprint() != before
