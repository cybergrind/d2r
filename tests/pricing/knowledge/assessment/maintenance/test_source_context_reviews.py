"""Explicit narrative bindings preserve source context and all required branches."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_inline_source_links import inline_review
from tests.pricing.knowledge.assessment.maintenance.test_review_dossiers import reviewed


def setup(root):
    role, occurrence = inline_review()
    role.update(
        names=['Test Unique'],
        qualities=['unique'],
        side='merc',
        variant='Starter',
        slot='Helmet',
        must={'op': 'context_eq', 'field': 'mercenary_type', 'value': 'Act 5 Bash'},
    )
    path = root / role['source']['path']
    path.parent.mkdir(parents=True)
    span = {'label': 'Test Unique', 'side': 'merc', 'slot': 'unspecified'}
    payload = {
        'sources': {
            occurrence['source_id']: {
                'item_spans': [span] * 163,
                'sections': [{'text': 'Starter Act 5 Bash uses Test Unique as its helmet.'}],
            }
        }
    }
    path.write_text(json.dumps(payload))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    role['source']['sha256'] = digest
    occurrence.update(
        name='Test Unique',
        original_label='Test Unique',
        category='unique',
        identity_status='resolved',
        side='merc',
        slot='unspecified',
        variant='Guide mention',
        source_rule_ids=[],
        details={'recommended': True, 'resolution_status': 'resolved'},
    )
    keys = ('name', 'original_label', 'category', 'build', 'variant', 'side', 'slot', 'source_id', 'source_locator')
    row = {
        'id': 'starter-head',
        'review_date': '2026-09-27',
        'reason': 'Explicit starter helmet and mercenary branch.',
        'occurrence_id': occurrence['id'],
        'expected_occurrence': {k: occurrence[k] for k in keys},
        'source': {**role['source'], 'expected': span},
        'evidence': {
            **role['source'],
            'locator': role['source']['locator'].replace('/item_spans/162', '/sections/0/text'),
            'quote': 'Starter Act 5 Bash uses Test Unique as its helmet.',
        },
        'branches': [
            {
                'profile_id': role['id'],
                'profile_fingerprint': fingerprint(role),
                'variant': 'Starter',
                'slot': 'Helmet',
                'mercenary_type': 'Act 5 Bash',
            }
        ],
        'remaining_branches': [],
    }
    return role, occurrence, {'schema_version': 1, 'rows': [row]}


def compile_review(root, role, occurrence, reviews):
    from pricing.knowledge.assessment.maintenance.source_context_reviews import compile_source_context_reviews

    return compile_source_context_reviews(reviews, [occurrence], [role], [reviewed(role, item='Test Unique')], root)


def test_explicit_source_binding_closes_only_exact_occurrence_without_rewriting_it(tmp_path):
    role, occurrence, reviews = setup(tmp_path)
    original = deepcopy(occurrence)
    result = compile_review(tmp_path, role, occurrence, reviews)
    assert result[0]['state'] == 'reviewed'
    assert result[0]['occurrence_id'] == occurrence['id']
    assert occurrence == original
    assert result[0]['profile_ids'] == [role['id']]


@pytest.mark.parametrize(
    'patch',
    [
        {'variant': 'Other'},
        {'slot': 'Rings'},
        {'side': 'player'},
        {'source_locator': '/item-spans/161'},
        {'category': 'set'},
        {'name': 'Other'},
        {'source_status': 'unverified'},
    ],
)
def test_neighbour_variant_wearer_slot_identity_and_unverified_source_cannot_inherit_review(tmp_path, patch):
    role, occurrence, reviews = setup(tmp_path)
    occurrence.update(patch)
    with pytest.raises(ValueError, match=r'source-context|Stale guide-use'):
        compile_review(tmp_path, role, occurrence, reviews)


def test_remaining_branch_is_partial_even_when_other_branch_is_implemented(tmp_path):
    role, occurrence, reviews = setup(tmp_path)
    reviews['rows'][0]['remaining_branches'] = ['Act 2 Might starter helmet needs separate role review.']
    assert compile_review(tmp_path, role, occurrence, reviews)[0]['state'] == 'pending'


@pytest.mark.parametrize('change', ['profile', 'source', 'quote', 'context', 'unreviewed', 'duplicate'])
def test_stale_missing_or_duplicate_proof_is_rejected(tmp_path, change):
    role, occurrence, reviews = setup(tmp_path)
    row = reviews['rows'][0]
    if change == 'profile':
        role['conditions'] = ['Changed rule']
    elif change == 'source':
        (tmp_path / role['source']['path']).write_text('{}')
    elif change == 'quote':
        row['evidence']['quote'] = 'Unsupported setup'
    elif change == 'context':
        row['branches'][0]['mercenary_type'] = 'Act 2 Might'
    elif change == 'unreviewed':
        row['reason'] = ''
    else:
        reviews['rows'].append(deepcopy(row))
    with pytest.raises(ValueError, match=r'source-context|Stale guide-use'):
        compile_review(tmp_path, role, occurrence, reviews)


@pytest.mark.parametrize('partial', [False, True])
def test_completion_consumes_only_complete_review_and_binds_final_scope(tmp_path, partial):
    from pricing.knowledge.assessment.maintenance.completion import compile_completion
    from pricing.knowledge.assessment.maintenance.guide_inventory import compile_inventory

    role, occurrence, reviews = setup(tmp_path)
    if partial:
        reviews['rows'][0]['remaining_branches'] = ['Another mercenary branch needs review.']
    neighbour = {**occurrence, 'id': 'neighbour', 'source_locator': '/item-spans/161'}
    inventory = compile_inventory(
        [occurrence, neighbour], [role], {'unique1': {'name': 'Test Unique', 'category': 'unique'}}
    )
    kwargs = {'profiles': [role], 'uses': [reviewed(role, item='Test Unique')], 'source_root': tmp_path}
    result = compile_completion({'rows': []}, inventory, {}, source_context_reviews=reviews, **kwargs)
    ids = {row['id'] for row in result['queue']}
    assert ('occurrence:one' in ids) is partial
    assert 'occurrence:neighbour' in ids
    assert result['source_context_dispositions'][0]['state'] == ('pending' if partial else 'reviewed')
    changed = deepcopy(reviews)
    changed['rows'][0]['reason'] += ' Additional reviewed explanation.'
    assert (
        compile_completion({'rows': []}, inventory, {}, source_context_reviews=changed, **kwargs)['scope']
        != result['scope']
    )


def test_explicit_remaining_branch_overrides_older_generic_source_credit(tmp_path):
    from pricing.knowledge.assessment.maintenance.completion import compile_completion
    from pricing.knowledge.assessment.maintenance.guide_inventory import compile_inventory

    role, occurrence, reviews = setup(tmp_path)
    older = {**role, 'id': 'older', 'variant': 'Guide mention', 'slot': 'unspecified'}
    profiles = [role, older]
    uses = [reviewed(r, item='Test Unique') for r in profiles]
    inventory = compile_inventory([occurrence], profiles, {'unique1': {'name': 'Test Unique', 'category': 'unique'}})
    original = compile_completion({'rows': []}, inventory, {}, profiles=profiles, uses=uses)
    assert original['counts']['reviewed_occurrences'] == 1
    reviews['rows'][0]['remaining_branches'] = ['Act 2 Might needs review.']
    updated = compile_completion(
        {'rows': []}, inventory, {}, profiles=profiles, uses=uses, source_context_reviews=reviews, source_root=tmp_path
    )
    assert updated['counts']['reviewed_occurrences'] == 0
    task = next(row for row in updated['queue'] if row['id'] == 'occurrence:one')
    assert 'Act 2 Might' in task['reason']
