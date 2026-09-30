"""Short source labels do not erase configuration-specific pattern endorsements."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.source_context_reviews import compile_source_context_reviews
from tests.pricing.knowledge.assessment.maintenance.test_player_source_context import setup
from tests.pricing.knowledge.assessment.maintenance.test_review_dossiers import reviewed


def pattern_setup(root):
    role, occurrence, doc = setup(root)
    role.pop('names')
    role.update(types=['helm'], qualities=['magic'])
    occurrence.update(category=None, identity_status='unresolved')
    row = doc['rows'][0]
    row['kind'] = 'player_pattern'
    row['expected_occurrence']['category'] = None
    branch = row['branches'][0]
    branch.update(profile_fingerprint=fingerprint(role), pattern_label=row['evidence']['quote'], qualities=['magic'])
    use = reviewed(role, pattern=role['id'], pattern_label=row['evidence']['quote'])
    use.pop('item', None)
    return role, occurrence, doc, use


def run(root, role, occurrence, doc, use):
    return compile_source_context_reviews(doc, [occurrence], [role], [use], root)


def test_pattern_binding_preserves_original_label_and_pending_work(tmp_path):
    args = pattern_setup(tmp_path)
    original = deepcopy(args[1])
    assert run(tmp_path, *args)[0]['state'] == 'reviewed'
    assert args[1] == original
    args[2]['rows'][0]['remaining_branches'] = ['Filled configuration not reviewed yet.']
    assert run(tmp_path, *args)[0]['state'] == 'pending'


@pytest.mark.parametrize(
    'change', ['name-only', 'other-pattern', 'other-quality', 'named-role', 'other-class', 'unknown-kind']
)
def test_pattern_binding_rejects_incompatible_configuration(tmp_path, change):
    role, occurrence, doc, use = pattern_setup(tmp_path)
    row = doc['rows'][0]
    if change == 'name-only':
        row['branches'][0]['pattern_label'] = occurrence['name']
    elif change == 'other-pattern':
        use['pattern_label'] = 'Other filler combination'
    elif change == 'other-quality':
        row['branches'][0]['qualities'] = ['rare']
    elif change == 'named-role':
        role['names'] = ['Test Unique']
        use.pop('pattern')
        use.pop('pattern_label')
        use['item'] = 'Test Unique'
    elif change == 'other-class':
        role['must']['value'] = 'Sorceress'
    else:
        row['kind'] = 'unknown'
    row['branches'][0]['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match='source-context'):
        run(tmp_path, role, occurrence, doc, use)


@pytest.mark.parametrize(('prefix', 'contents'), [('Empty preparation base for ', 'empty'), ('Completed ', 'filled')])
def test_preparation_label_requires_corresponding_socket_state(tmp_path, prefix, contents):
    role, occurrence, doc, use = pattern_setup(tmp_path)
    branch = doc['rows'][0]['branches'][0]
    branch['pattern_label'] = use['pattern_label'] = prefix + doc['rows'][0]['evidence']['quote']
    with pytest.raises(ValueError, match='source-context'):
        run(tmp_path, role, occurrence, doc, use)
    role['must'] = {'all': [role['must'], {'op': 'fact_eq', 'field': 'socket_contents', 'value': contents}]}
    branch['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    assert run(tmp_path, role, occurrence, doc, use)[0]['state'] == 'reviewed'
