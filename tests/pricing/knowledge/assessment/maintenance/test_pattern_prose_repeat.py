"""Alternate prose labels must identify the same endorsed planner configuration."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.source_context_reviews import compile_source_context_reviews
from tests.pricing.knowledge.assessment.maintenance.test_player_prose_repeat import setup as prose_setup
from tests.pricing.knowledge.assessment.maintenance.test_review_dossiers import reviewed


def setup(root):
    role, occurrence, doc = prose_setup(root)
    role.pop('names')
    role.update(types=['staf'], qualities=['magic', 'rare'])
    occurrence.update(category=None, identity_status='unresolved')
    row = doc['rows'][0]
    row['kind'] = 'player_pattern_prose_repeat'
    row['expected_occurrence']['category'] = None
    branch = row['branches'][0]
    branch.update(
        profile_fingerprint=fingerprint(role),
        qualities=role['qualities'],
        pattern_label='Reviewed staff configuration',
        source_label=occurrence['original_label'],
    )
    use = reviewed(role, pattern=role['id'], pattern_label=branch['pattern_label'])
    use.pop('item', None)
    return role, occurrence, doc, use


def run(root, role, occurrence, doc, use):
    return compile_source_context_reviews(doc, [occurrence], [role], [use], root)


def test_alias_links_exact_planner_pattern_without_rewriting_source(tmp_path):
    args = setup(tmp_path)
    before = deepcopy(args[1])
    result = run(tmp_path, *args)
    assert result[0]['state'] == 'reviewed'
    assert args[1] == before


@pytest.mark.parametrize('change', ['source-label', 'endorsement', 'qualities', 'named-role', 'other-class'])
def test_pattern_alias_requires_explicit_source_and_endorsement(tmp_path, change):
    role, occurrence, doc, use = setup(tmp_path)
    branch = doc['rows'][0]['branches'][0]
    if change == 'source-label':
        branch['source_label'] = 'Another item'
    elif change == 'endorsement':
        branch['pattern_label'] = 'Unreviewed alternative'
    elif change == 'qualities':
        branch['qualities'] = ['crafted']
    elif change == 'named-role':
        role['names'] = ['Test Unique']
        use.pop('pattern')
        use.pop('pattern_label')
        use['item'] = 'Test Unique'
    else:
        role['must']['value'] = 'Sorceress'
    branch['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match='source-context'):
        run(tmp_path, role, occurrence, doc, use)
